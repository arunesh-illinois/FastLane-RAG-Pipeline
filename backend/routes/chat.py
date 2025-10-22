import time, re
from fastapi import APIRouter
from backend.services.appointments import schedule_appointment, reschedule_appointment
from backend.models.chat_input import ChatInput
from backend.services.utils import detect_intent_regex, compose_answer, get_cached_docs

router = APIRouter()

@router.post("/chat")
def chat(payload: ChatInput):
    start_time = time.time()

    session_id = payload.session_id
    message = payload.message

    plan_steps = []
    tool_calls = []
    citations = []
    reply = ""
    scheduled = False

    # --- Step 1: Intent Detection ---
    intent_start = time.time()
    intent = detect_intent_regex(message, session_id)  # can use regex or LLM
    plan_steps.append({
        "step": 1,
        "intent": "intent_detection",
        "latency_ms": round((time.time() - intent_start) * 1000, 2),
        "confidence": intent.get("confidence", 0.0)
    })

    entities = intent.get("entities", {}) or {}
    has_patient = bool(entities.get("patient"))
    has_slot = bool(entities.get("preferred_slot_iso"))
    has_location = bool(entities.get("location"))

    # Helper: detect compound or info-seeking messages
    def is_compound_message(msg: str) -> bool:
        q = msg.lower()
        question_words = ["what", "where", "when", "how", "why", "policy", "late", "parking", "park"]
        if '?' in q:
            return True
        for w in question_words:
            if w in q and re.search(r"\b(schedule|book|appointment|reserve|make it|change|reschedule)\b", q):
                return True
        return False

    # --- Step 2: Direct scheduling shortcut ---
    if intent.get("is_scheduling") and has_patient and has_slot and has_location and not is_compound_message(message):
        tool_start = time.time()
        tool_result = schedule_appointment(entities, session_id)
        scheduled = True

        tool_calls.append({
            "name": "schedule_appointment",
            "args": entities,
            "result": tool_result
        })

        if tool_result.get("status") == "already_booked":
            reply = f"This appointment was already booked ({tool_result['appt_id']})."
        else:
            patient = entities.get("patient", "Patient")
            location = entities.get("location", "clinic")
            reply = f"Booked {patient} at {location} ({tool_result['appt_id']})."

        plan_steps.append({
            "step": len(plan_steps) + 1,
            "intent": "schedule_direct",
            "latency_ms": round((time.time() - tool_start) * 1000, 2)
        })

    else:
        # --- Step 3: Retrieval + Compose for compound/info-seeking messages ---
        if not intent.get("is_rescheduling"):
            retrieve_start = time.time()
            docs = get_cached_docs(message, top_k=3)
            citations = [{"id": d["id"], "score": d["score"]} for d in docs]
            plan_steps.append({
                "step": len(plan_steps) + 1,
                "intent": "retrieve",
                "latency_ms": round((time.time() - retrieve_start) * 1000, 2)
            })

            # ✅ Compose using LLM for RAG questions
            compose_start = time.time()
            reply = compose_answer(message, docs, use_llm=True)
            plan_steps.append({
                "step": len(plan_steps) + 1,
                "intent": "compose_llm",
                "latency_ms": round((time.time() - compose_start) * 1000, 2)
            })

        # --- Step 4: Schedule if needed (after compose) ---
        if intent.get("is_scheduling") and has_patient and has_slot and has_location and not scheduled:
            tool_start = time.time()
            tool_result = schedule_appointment(entities, session_id)
            scheduled = True

            tool_calls.append({
                "name": "schedule_appointment",
                "args": entities,
                "result": tool_result
            })

            if tool_result.get("status") == "already_booked":
                reply += f" This appointment was already booked ({tool_result['appt_id']})."
            else:
                patient = entities.get("patient", "Patient")
                location = entities.get("location", "clinic")
                reply += f" Booked {patient} at {location} ({tool_result['appt_id']})."

            plan_steps.append({
                "step": len(plan_steps) + 1,
                "intent": "schedule_after_compose",
                "latency_ms": round((time.time() - tool_start) * 1000, 2)
            })

    # --- Step 5: Rescheduling branch ---
    if intent.get("is_rescheduling"):
        new_slot = entities.get("preferred_slot_iso")
        tool_start = time.time()
        tool_result = reschedule_appointment(session_id, new_slot)

        tool_calls.append({
            "name": "reschedule_appointment",
            "args": {"new_slot": new_slot},
            "result": tool_result
        })

        if tool_result["ok"]:
            time_display = new_slot.split('T')[1][:5]
            reply = f"Updated appointment to {time_display} ({tool_result['appt_id']})."
        else:
            reply = f"Could not reschedule: {tool_result.get('error', 'Unknown error')}"

        plan_steps.append({
            "step": len(plan_steps) + 1,
            "intent": "reschedule",
            "latency_ms": round((time.time() - tool_start) * 1000, 2)
        })

    total_latency = round((time.time() - start_time) * 1000, 2)
    return {
        "reply": reply,
        "citations": citations,
        "plan_steps": plan_steps,
        "tool_calls": tool_calls,
        "latency_ms": total_latency
    }