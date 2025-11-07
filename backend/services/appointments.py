from datetime import datetime
from typing import Dict, Optional, Tuple
from backend.services.database import db_service


# Keep appt_counter for generating IDs
appt_counter = 1000
session_context: Dict[str, str] = {}  # session_id → last_appt_id


def get_next_appt_id() -> str:
    """Generate next appointment ID"""
    global appt_counter
    appt_id = f"A-{appt_counter}"
    appt_counter += 1
    return appt_id


async def schedule_appointment(params: dict, session_id: Optional[str] = None) -> dict:
    """
    Schedule a new appointment (idempotent)

    Args:
        params: {
            "patient": str,
            "preferred_slot_iso": str,
            "location": str,
            "notes": Optional[str]
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
    patient = params.get("patient", "Unknown").strip()
    slot = params.get("preferred_slot_iso", "")
    location = params.get("location", "Main").strip()
    notes = params.get("notes")
    
    appt_id = get_next_appt_id()
    
    result = await db_service.create_appointment(
        appointment_id=appt_id,
        patient=patient,
        slot=slot,
        location=location,
        notes=notes
    )
    
    # Track in session
    if session_id and "appt_id" in result:
        session_context[session_id] = result["appt_id"]
    
    return result


async def get_appointment(appt_id: str) -> Optional[Dict]:
    """Get a single appointment by ID"""
    return await db_service.get_appointment(appt_id)


async def get_all_appointments() -> dict:
    """Get all appointments"""
    appointments_list = await db_service.get_all_appointments()
    total = await db_service.get_appointments_count()
    
    return {
        "appointments": appointments_list,
        "total": total
    }


async def update_appointment(appt_id: str, updates: dict) -> dict:
    """
    Update an appointment
    
    Args:
        appt_id: Appointment ID
        updates: Dictionary of fields to update (patient, preferred_slot_iso, location, notes, status)
    
    Returns:
        {
            "ok": bool,
            "appointment": dict | None
        }
    """
    # Map API field names to database field names
    db_updates = {}
    if "preferred_slot_iso" in updates:
        db_updates["slot"] = updates["preferred_slot_iso"]
    if "patient" in updates:
        db_updates["patient"] = updates["patient"]
    if "location" in updates:
        db_updates["location"] = updates["location"]
    if "notes" in updates:
        db_updates["notes"] = updates["notes"]
    if "status" in updates:
        db_updates["status"] = updates["status"]
    
    appointment = await db_service.update_appointment(appt_id, **db_updates)
    
    return {
        "ok": appointment is not None,
        "appointment": appointment
    }


async def delete_appointment(appt_id: str) -> dict:
    """
    Delete an appointment permanently
    
    Returns:
        {
            "ok": bool,
            "appt_id": str,
            "message": str
        }
    """
    success = await db_service.delete_appointment(appt_id)
    
    if success:
        # Remove from session context if present
        for sid, aid in list(session_context.items()):
            if aid == appt_id:
                session_context.pop(sid, None)
                break
        
        return {
            "ok": True,
            "appt_id": appt_id,
            "message": "Appointment deleted successfully"
        }
    else:
        return {
            "ok": False,
            "appt_id": appt_id,
            "message": "Appointment not found"
        }


async def cancel_appointment(appt_id: str) -> dict:
    """
    Cancel an appointment (soft delete)
    
    Returns:
        {
            "ok": bool,
            "appt_id": str,
            "appointment": dict,
            "message": str
        }
    """
    appointment = await db_service.cancel_appointment(appt_id)
    
    if appointment:
        # Remove from session context if present
        for sid, aid in list(session_context.items()):
            if aid == appt_id:
                session_context.pop(sid, None)
                break
        
        return {
            "ok": True,
            "appt_id": appt_id,
            "appointment": appointment,
            "message": "Appointment cancelled successfully"
        }
    else:
        return {
            "ok": False,
            "appt_id": appt_id,
            "message": "Appointment not found"
        }


async def clear_all_appointments() -> dict:
    """Clear all appointments (for testing)"""
    count = await db_service.clear_all_appointments()
    session_context.clear()
    
    return {
        "ok": True,
        "message": f"All appointments cleared ({count} deleted)"
    }
