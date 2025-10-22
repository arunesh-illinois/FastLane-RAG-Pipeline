from datetime import datetime
from typing import Dict, Optional, Tuple

# In-memory appointment storage
appointments: Dict[str, dict] = {}
booked_slots = set()  # (patient_lower, slot, location_lower)
session_context: Dict[str, str] = {}  # session_id → last_appt_id
appt_counter = 1000


def schedule_appointment(params: dict, session_id: Optional[str] = None) -> dict:
    """
    Schedule a new appointment (idempotent)

    Args:
        params: {
            "patient": str,
            "preferred_slot_iso": str,
            "location": str
        }
        session_id: Optional session ID for tracking

    Returns:
        {
            "ok": bool,
            "appt_id": str,
            "normalized_slot_iso": str,
            "status": "created" | "already_booked"
        }
    """
    global appt_counter

    patient = params.get("patient", "Unknown").strip()
    slot = params.get("preferred_slot_iso", "")
    location = params.get("location", "Main").strip()

    # Normalize for deduplication
    patient_key = patient.lower()
    location_key = location.lower()
    slot_key = (patient_key, slot, location_key)

    # Check if already booked (idempotency)
    if slot_key in booked_slots:
        # Find existing appointment
        for appt_id, appt in appointments.items():
            if (appt["patient"].lower() == patient_key and
                    appt["slot"] == slot and
                    appt["location"].lower() == location_key):

                # Update session context
                if session_id:
                    session_context[session_id] = appt_id

                return {
                    "ok": True,
                    "appt_id": appt_id,
                    "normalized_slot_iso": slot,
                    "status": "already_booked"
                }

    # Create new appointment
    appt_id = f"A-{appt_counter}"
    appt_counter += 1

    appointments[appt_id] = {
        "patient": patient,
        "slot": slot,
        "location": location,
        "created_at": datetime.now().isoformat()
    }

    booked_slots.add(slot_key)

    # Track in session
    if session_id:
        session_context[session_id] = appt_id

    return {
        "ok": True,
        "appt_id": appt_id,
        "normalized_slot_iso": slot,
        "status": "created"
    }


def reschedule_appointment(session_id: str, new_slot: str) -> dict:
    """
    Reschedule the last appointment in the session by creating a new appointment ID
    """

    global appt_counter

    # Get last appointment from session
    appt_id = session_context.get(session_id)

    if not appt_id or appt_id not in appointments:
        return {
            "ok": False,
            "error": "No recent appointment found in session",
            "status": "error"
        }

    old_appt = appointments[appt_id]

    # Remove old slot from booked set
    old_key = (
        old_appt["patient"].lower(),
        old_appt["slot"],
        old_appt["location"].lower()
    )
    booked_slots.discard(old_key)

    # Create new appointment (with new ID)
    new_appt_id = f"A-{appt_counter}"
    appt_counter += 1

    new_appt = {
        "patient": old_appt["patient"],
        "slot": new_slot,
        "location": old_appt["location"],
        "created_at": datetime.now().isoformat(),
        "previous_appt_id": appt_id
    }

    appointments[new_appt_id] = new_appt

    # Add new slot to booked set
    new_key = (
        old_appt["patient"].lower(),
        new_slot,
        old_appt["location"].lower()
    )
    booked_slots.add(new_key)

    # Update session to track the latest appointment
    session_context[session_id] = new_appt_id

    return {
        "ok": True,
        "appt_id": new_appt_id,
        "normalized_slot_iso": new_slot,
        "status": "rescheduled"
    }



def get_appointments() -> dict:
    """Get all appointments (for testing)"""
    return {
        "appointments": list(appointments.values()),
        "total": len(appointments)
    }

def cancel_appointment(session_id: Optional[str] = None, appt_id: Optional[str] = None) -> dict:
    """
    Cancel an appointment by session_id or appt_id.

    Priority:
    - If appt_id is provided, cancel that one directly.
    - Otherwise, use the last appointment in the session.

    Returns:
        {
            "ok": bool,
            "appt_id": str (if found),
            "status": "cancelled" | "not_found"
        }
    """
    # Determine appointment ID
    target_appt_id = appt_id or session_context.get(session_id)

    if not target_appt_id or target_appt_id not in appointments:
        return {
            "ok": False,
            "error": "No matching appointment found to cancel",
            "status": "not_found"
        }

    appt = appointments[target_appt_id]

    # Remove from booked slots
    slot_key = (
        appt["patient"].lower(),
        appt["slot"],
        appt["location"].lower()
    )
    booked_slots.discard(slot_key)

    # Mark appointment as cancelled
    appt["cancelled_at"] = datetime.now().isoformat()
    appt["status"] = "cancelled"

    # Remove from session context if it matches
    if session_id and session_context.get(session_id) == target_appt_id:
        session_context.pop(session_id, None)

    return {
        "ok": True,
        "appt_id": target_appt_id,
        "status": "cancelled"
    }
