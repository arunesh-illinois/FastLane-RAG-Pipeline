import time
from fastapi import APIRouter
import backend.variables.global_states as global_state
from backend.models.knowledge_input import KnowledgeInput
from backend.services.utils import rebuild_index

router = APIRouter()

@router.post("/knowledge")
def upsert_knowledge(payload: KnowledgeInput):
    """
    Upsert document (idempotent by ID)
    If ID exists, updates it. Otherwise creates new.
    """
    start = time.time()

    doc_id = payload.id
    text = payload.text
    tags = payload.tags

    # Check if updating existing doc
    is_new = doc_id not in global_state.documents

    # Upsert document
    global_state.documents[doc_id] = {
        "id": doc_id,
        "text": text,
        "tags": tags
    }

    # Rebuild global_state.index (acceptable for small datasets)
    rebuild_index()

    latency = (time.time() - start) * 1000

    return {
        "ok": True,
        "chunks": 1,
        "is_new": is_new,
        "total_docs": len(global_state.documents),
        "latency_ms": round(latency, 2)
    }

@router.get("/knowledge")
def list_knowledge():
    """List all global_state.documents"""
    return {
        "global_state.documents": list(global_state.documents.values()),
        "total": len(global_state.documents)
    }