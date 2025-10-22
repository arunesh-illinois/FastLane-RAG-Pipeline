import time
from fastapi import APIRouter
from backend.services.appointments import schedule_appointment, get_appointments, appointments, booked_slots
from backend.global_states import session_context
from backend.models.schedule_input import ScheduleInput

router = APIRouter()

@router.post("/tools/schedule_appointment")
def schedule_endpoint(payload: ScheduleInput):
    """
    Direct scheduling endpoint
    """
    start = time.time()

    result = schedule_appointment({
        "patient": payload.patient,
        "preferred_slot_iso": payload.preferred_slot_iso,
        "location": payload.location
    })

    result["latency_ms"] = round((time.time() - start) * 1000, 2)
    return result


@router.get("/tools/appointments")
def list_appointments():
    """List all appointments (for testing)"""
    return get_appointments()


@router.delete("/tools/appointments")
def clear_appointments():
    """Clear all appointments (for testing)"""
    appointments.clear()
    booked_slots.clear()
    session_context.clear()
    return {"ok": True, "message": "All appointments cleared"}