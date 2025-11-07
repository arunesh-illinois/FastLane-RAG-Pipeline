from pydantic import BaseModel
from typing import Optional


class ScheduleInput(BaseModel):
    patient: str
    preferred_slot_iso: str
    location: str
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    patient: Optional[str] = None
    preferred_slot_iso: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None