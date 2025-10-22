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
    Reschedule the last appointment in the session

    Args:
        session_id: Session ID
        new_slot: New ISO timestamp

    Returns:
        {
            "ok": bool,
            "appt_id": str,
            "normalized_slot_iso": str,
            "status": "rescheduled" | "error"
        }
    """
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

    # Update appointment
    old_appt["slot"] = new_slot
    old_appt["updated_at"] = datetime.now().isoformat()

    # Add new slot to booked set
    new_key = (
        old_appt["patient"].lower(),
        new_slot,
        old_appt["location"].lower()
    )
    booked_slots.add(new_key)

    return {
        "ok": True,
        "appt_id": appt_id,
        "normalized_slot_iso": new_slot,
        "status": "rescheduled"
    }


def get_appointments() -> dict:
    """Get all appointments (for testing)"""
    return {
        "appointments": list(appointments.values()),
        "total": len(appointments)
    }
