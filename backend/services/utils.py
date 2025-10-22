from typing import Tuple, Optional
import re
import time
import faiss
import numpy as np
import requests
import backend.variables.global_states as global_state

OLLAMA_BASE_URL = "http://localhost:11434/api/generate"  # LLM endpoint (commented out)
OLLAMA_MODEL = "llama3.2:latest"  # LLM model (commented out)


## def detect_intent_llm(message: str, session_id: Optional[str] = None) -> dict:
##     """
##     Use LLM to detect intent and extract entities
##     More robust than regex, handles conversational context
##     """
##     # ... LLM logic ...
##     pass

def parse_time(time_str: str) -> Tuple[int, int, str]:
    """
    Parse time string to (hour, minute, period)
    Examples: "10:30am", "2pm", "11:00"
    """
    time_str = time_str.lower().strip()

    # Match patterns like "10:30am", "2pm", "11:00"
    match = re.search(r'(\d{1,2}):?(\d{0,2})\s*(am|pm)?', time_str)

    if not match:
        return 9, 0, "am"  # Default fallback

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    period = match.group(3) or ""

    # Convert to 24-hour format
    if period == "pm" and hour < 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0

    return hour, minute, period

def detect_intent_regex(message: str, session_id: Optional[str] = None) -> dict:
    """
    Lightweight regex-based intent detection for scheduling, rescheduling, or pure RAG.
    Designed for <100ms latency.
    """
    message_lower = message.lower()
    entities = {}

    # --- 0. Detect cancellation ---
    cancel_patterns = [
        r'\b(cancel|delete|remove|drop)\s+(?:appointment\s*)?(A-\d+)\b',  # cancel A-102
        r'\b(cancel|delete|remove|drop)\s+(?:my\s+)?appointment\b',
        r'\b(cancel|delete|remove|drop)\b'
    ]
    for pattern in cancel_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2 and match.group(2):
                entities["appt_id"] = match.group(2).upper()
            return {
                "is_scheduling": False,
                "is_rescheduling": False,
                "is_cancelling": True,
                "entities": entities
            }
    # --- 1. Detect rescheduling ---
    reschedule_patterns = [
        r'\b(?:reschedule|change|update|move|make it)\s+(?:to|for)?\s*(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)'
    ]
    for pattern in reschedule_patterns:
        if match := re.search(pattern, message_lower):
            time_str = match.group(1)
            hour, minute, _ = parse_time(time_str)
            return {
                "is_scheduling": False,
                "is_rescheduling": True,
                "is_cancelling": False,
                "entities": {
                    "preferred_slot_iso": f"2025-10-21T{hour:02d}:{minute:02d}:00-04:00"
                }
            }

    # --- 2. Detect new scheduling ---
    schedule_keywords = r'\b(?:schedule|book|appointment|reserve|set up)\b'
    is_scheduling = bool(re.search(schedule_keywords, message_lower))

    if is_scheduling:
        # --- Extract patient name ---
        # Handles: "schedule Rivera", "schedule for Rivera", "book for Rivera", "Rivera appointment"
        name_patterns = [
            r'(?i)\b(?:book|schedule)\s+(?:for\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            r'(?i)\bfor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            r'(?i)\b([A-Z][a-z]+)\s+(?:appointment|booking)\b'
        ]
        for pattern in name_patterns:
            if match := re.search(pattern, message):
                entities["patient"] = match.group(1)
                break

        # --- Extract time ---
        if time_match := re.search(r'\b(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)\b', message_lower):
            time_str = time_match.group(1)
            hour, minute, _ = parse_time(time_str)
            entities["preferred_slot_iso"] = f"2025-10-21T{hour:02d}:{minute:02d}:00-04:00"

        # --- Extract location ---
        if location_match := re.search(r'\b(midtown|downtown|uptown|main)\b', message_lower):
            entities["location"] = location_match.group(1).title()

    return {
        "is_scheduling": is_scheduling,
        "is_rescheduling": False,
        "is_cancelling": False,
        "entities": entities
    }

def compose_answer_template(query: str, retrieved_docs: list[dict]) -> str:
    """
        Template-based answer composer (no LLM).
        Ultra-fast (<50ms), deterministic, and good for latency-critical paths.
    """
    if not retrieved_docs:
        return "I don't have that information right now."

    # If top doc clearly dominates, just use it
    if len(retrieved_docs) >= 2:
        top_score = retrieved_docs[0].get('score', 0)
        next_score = retrieved_docs[1].get('score', 0)
        if top_score - next_score > 0.08 or top_score >= 0.5:
            d = retrieved_docs[0]
            sent = d['text'].split('. ')[0].strip()
            return f"{sent}. [{d['id']}]"

    # Otherwise include two best sentences
    parts = []
    for d in retrieved_docs[:2]:
        sent = d['text'].split('. ')[0].strip()
        parts.append(f"{sent}. [{d['id']}]")

    return ' '.join(parts)

def compose_answer_llm(query: str, retrieved_docs: list[dict]) -> str:
    """
    LLM-based composer using Ollama for more natural phrasing.
    Slightly slower (~300–400ms), but optional for richer responses.
    """
    if not retrieved_docs:
        return "I don't have that information right now."

    context = "\n".join(f"[{d['id']}] {d['text']}" for d in retrieved_docs)

    prompt = f"""Answer the question using ONLY the context below.Be concise (1–2 sentences). Cite sources using [id] notation.
    Context:{context}
    Question: {query}
    Answer:"""

    try:
        response = requests.post(
            OLLAMA_BASE_URL,
            json={
                "global_state.model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 150,
                },
            },
            timeout=3,  # keep it short to meet 500ms budget
        )

        if response.status_code != 200:
            print(f"⚠️ Ollama returned {response.status_code}")
            return compose_answer_template(query, retrieved_docs)

        result = response.json()
        answer = result.get("response", "").strip()

        # Guardrail: prefer short answers only
        if not answer or len(answer.split()) < 3:
            return compose_answer_template(query, retrieved_docs)

        return answer

    except requests.exceptions.Timeout:
        print("⚠️ LLM timeout — falling back to template")
        return compose_answer_template(query, retrieved_docs)
    except Exception as e:
        print(f"⚠️ LLM compose error: {e}")
        return compose_answer_template(query, retrieved_docs)

def compose_answer(query: str, retrieved_docs: list[dict], use_llm: bool = False) -> str:
    """
    Unified entrypoint.
    - use_llm=False → ultra-fast deterministic mode (default)
    - use_llm=True  → use Ollama mini-LLM for natural phrasing
    """
    return compose_answer_template(query, retrieved_docs)
    # if use_llm:
    #     return compose_answer_llm(query, retrieved_docs)
    # else:
    #     return compose_answer_template(query, retrieved_docs)

def rebuild_index():

    # Set a global random seed
    np.random.seed(1211)
    
    if not global_state.documents:
        print("⚠️ No documents to index")
        return

    start = time.time()
    texts = [d["text"] for d in global_state.documents.values()]
    global_state.doc_ids = list(global_state.documents.keys())
    embeddings = global_state.model.encode(texts, show_progress_bar=False)  # Only for retrieval, not LLM

    dimension = embeddings.shape[1]
    global_state.index = faiss.IndexFlatIP(dimension)
    embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
    faiss.normalize_L2(embeddings)
    global_state.index.add(embeddings)

    print(f"✅ FAISS index built in {(time.time() - start) * 1000:.2f}ms")

def get_cached_docs(query: str, top_k: int = 3):
    cached = global_state.query_cache.get(query)
    if cached:
        return cached
    docs = global_state.retriever.retrieve(query, top_k=top_k)
    global_state.query_cache.set(query, docs)
    return docs
