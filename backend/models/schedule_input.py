from pydantic import BaseModel


class ScheduleInput(BaseModel):
    patient: str
    preferred_slot_iso: str
    location: str