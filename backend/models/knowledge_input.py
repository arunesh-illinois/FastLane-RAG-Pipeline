from pydantic import BaseModel

class KnowledgeInput(BaseModel):
    id: str
    text: str
    tags: list[str] = []
