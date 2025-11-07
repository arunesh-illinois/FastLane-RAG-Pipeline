import time
from fastapi import APIRouter, HTTPException
from backend.services.appointments import (
    schedule_appointment, 
    get_all_appointments, 
    get_appointment,
    update_appointment,
    delete_appointment,
    cancel_appointment,
    clear_all_appointments
)
from backend.variables.global_states import session_context
from backend.models.schedule_input import ScheduleInput, AppointmentUpdate

router = APIRouter()


@router.post("/tools/schedule_appointment")
async def schedule_endpoint(payload: ScheduleInput):
    """
    Create a new appointment (CREATE)
    """
    start = time.time()

    result = await schedule_appointment({
        "patient": payload.patient,
        "preferred_slot_iso": payload.preferred_slot_iso,
        "location": payload.location,
        "notes": payload.notes
    })

    result["latency_ms"] = round((time.time() - start) * 1000, 2)
    return result


@router.get("/tools/appointments")
async def list_appointments():
    """
    Get all appointments (READ - List)
    """
    return await get_all_appointments()


@router.get("/tools/appointments/{appointment_id}")
async def get_appointment_endpoint(appointment_id: str):
    """
    Get a single appointment by ID (READ - Single)
    """
    appointment = await get_appointment(appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return {"ok": True, "appointment": appointment}


@router.put("/tools/appointments/{appointment_id}")
async def update_appointment_endpoint(appointment_id: str, payload: AppointmentUpdate):
    """
    Update an appointment (UPDATE)
    """
    updates = payload.dict(exclude_unset=True)
    
    # Convert preferred_slot_iso to slot if present
    if "preferred_slot_iso" in updates:
        updates["preferred_slot_iso"] = updates["preferred_slot_iso"]
    
    result = await update_appointment(appointment_id, updates)
    
    if not result["ok"]:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return result


@router.patch("/tools/appointments/{appointment_id}")
async def patch_appointment_endpoint(appointment_id: str, payload: AppointmentUpdate):
    """
    Partially update an appointment (UPDATE - Partial)
    """
    updates = payload.dict(exclude_unset=True)
    
    result = await update_appointment(appointment_id, updates)
    
    if not result["ok"]:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return result


@router.delete("/tools/appointments/{appointment_id}")
async def delete_appointment_endpoint(appointment_id: str):
    """
    Delete an appointment permanently (DELETE)
    """
    result = await delete_appointment(appointment_id)
    
    if not result["ok"]:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return result


@router.post("/tools/appointments/{appointment_id}/cancel")
async def cancel_appointment_endpoint(appointment_id: str):
    """
    Cancel an appointment (soft delete)
    """
    result = await cancel_appointment(appointment_id)
    
    if not result["ok"]:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return result


@router.delete("/tools/appointments")
async def clear_appointments():
    """
    Clear all appointments (for testing) - DELETE All
    """
    return await clear_all_appointments()