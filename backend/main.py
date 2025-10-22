import json, os, time
import backend.global_states as global_state
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
from backend.services.knowledgeRetriever import HybridRetriever
# detect_intent_llm removed (LLM intent detection commented out)
from backend.services.utils import rebuild_index
from backend.routes import health_check, knowledge, appointment_tools, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown lifecycle"""

    print("🔄 Loading sentence transformer global_state.model...")
    start = time.time()
    global_state.model = SentenceTransformer('all-MiniLM-L6-v2')  # Only for embeddings, not LLM
    print(f"✅ Model loaded in {time.time() - start:.2f}s")

    # Load sample knowledge
    knowledge_path = "backend/knowledgeBase.json"
    if os.path.exists(knowledge_path):
        with open(knowledge_path, 'r') as f:
            docs = json.load(f)
        for doc in docs:
            global_state.documents[doc["id"]] = doc
        rebuild_index()
        print(f"✅ Loaded {len(global_state.documents)} global_state.documents")

        # Initialize global_state.retriever
        global_state.retriever = HybridRetriever(global_state.model, global_state.index, global_state.documents, global_state.doc_ids)
        print("✅ Retriever initialized")

    else:
        print("⚠️ knowledge.json not found, starting with empty knowledge base")

    yield  # <-- application runs here

    # Cleanup logic (if any)
    print("🛑 Shutting down app...")

app = FastAPI(title="FastLane RAG Orchestrator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_check.router)
app.include_router(knowledge.router)
app.include_router(appointment_tools.router)
app.include_router(chat.router)

print("✅ FastAPI app initialized")
