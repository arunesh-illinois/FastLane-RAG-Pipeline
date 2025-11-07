import json, os, time
import backend.variables.global_states as global_state
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer

from backend.services.auth import verify_token
from backend.services.knowledgeRetriever import HybridRetriever
# detect_intent_llm removed (LLM intent detection commented out)
from backend.services.utils import rebuild_index
from backend.services.database import db_service
import asyncio
from typing import List
from backend.routes import health_check, knowledge, appointment_tools, chat

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # optional: map user id -> websocket
        self.user_map = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            self.user_map[user_id] = websocket

    def disconnect(self, websocket: WebSocket, user_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id and user_id in self.user_map:
            try:
                del self.user_map[user_id]
            except KeyError:
                pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                # on error, disconnect that socket
                try:
                    await connection.close()
                except Exception:
                    pass
                self.disconnect(connection)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown lifecycle"""

    print("🔄 Loading sentence transformer global_state.model...")
    start = time.time()
    global_state.model = SentenceTransformer('all-MiniLM-L6-v2')  # Only for embeddings, not LLM
    print(f"✅ Model loaded in {time.time() - start:.2f}s")

    # Initialize SQLite database
    print("🔄 Initializing database...")
    await db_service.init_db()

    # Load sample knowledge
    knowledge_path = "backend/variables/knowledgeBase.json"
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

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint that expects a `token` query param (JWT) for auth.
    If token is invalid, closes the connection with code 1008 (policy violation).
    """
    user_id = None
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.get('sub')

    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # simple echo/broadcast logic for demo
            # Expect messages to be JSON strings in real apps
            await manager.broadcast(f"{user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id)
        await manager.broadcast(f"{user_id} disconnected")

app.include_router(health_check.router)
app.include_router(knowledge.router)
app.include_router(appointment_tools.router)
app.include_router(chat.router)

print("✅ FastAPI app initialized")
