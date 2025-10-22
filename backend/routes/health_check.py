import time
from fastapi import APIRouter
import backend.variables.global_states as global_state
import backend.main as main
from backend.services.utils import compose_answer

router = APIRouter()
@router.get("/")
def root():
    return {"status": "healthy", "documents_loaded": len(global_state.documents)}

@router.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

@router.get("/test-retrieval")
def test_retrieval(query: str = "Where can I park?"):
    """Test retrieval endpoint"""
    if global_state.retriever is None:
        return {"error": "Retriever not initialized"}

    start = time.time()
    results = main.get_cached_docs(query, top_k=3)
    latency = (time.time() - start) * 1000

    return {
        "query": query,
        "results": results,
        "latency_ms": round(latency, 2)
    }

@router.get("/test-compose")
def test_compose(query: str = "Where can I park?"):
    """Test retrieval + composition"""
    if global_state.retriever is None:
        return {"error": "Retriever not initialized"}

    start = time.time()

    # Retrieve
    retrieve_start = time.time()
    docs = main.get_cached_docs(query, top_k=3)
    retrieve_time = (time.time() - retrieve_start) * 1000

    # Compose
    compose_start = time.time()
    answer = compose_answer(query, docs)
    compose_time = (time.time() - compose_start) * 1000

    total_time = (time.time() - start) * 1000

    return {
        "query": query,
        "answer": answer,
        "citations": [{"id": d["id"], "score": d["score"]} for d in docs],
        "timing": {
            "retrieve_ms": round(retrieve_time, 2),
            "compose_ms": round(compose_time, 2),
            "total_ms": round(total_time, 2)
        }
    }