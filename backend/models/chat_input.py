from pydantic import BaseModel


class ChatInput(BaseModel):
    session_id: str
    message: str