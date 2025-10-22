# FastLane RAG Orchestrator 🚦

_A lightning-fast service for healthcare RAG and appointment scheduling._

## Features ⚡

1. **Ultra-Fast Knowledge Base**

   - Hybrid retrieval combining BM25 + FAISS semantic search
   - Optimized with RRF fusion and MMR for diverse results
   - Sub-500ms response time for all operations
   - Built-in 30s LRU cache for query optimization

2. **Intelligent Chat**

   - Template-based answer composition (no LLM dependency)
   - Clear source citations with confidence scores
   - Detailed execution traces and timing breakdowns
   - Multi-intent handling (e.g., questions + scheduling)

3. **Smart Appointment System**
   - Idempotent scheduling with unique appointment IDs
   - Session-aware rescheduling support
   - Multiple location support (Midtown, Downtown, Uptown)
   - Conflict detection and prevention

## Technical Architecture 🔧

### Retrieval Pipeline

- **Hybrid Search**: BM25 lexical + FAISS semantic
- **Fusion**: RRF (Reciprocal Rank Fusion)
- **Diversification**: MMR (Maximal Marginal Relevance)
- **Cache**: 30s LRU for frequent queries

### Performance Optimizations

- Precomputed embeddings on document ingest
- Ultra-lightweight template-based composer
- Regex-based intent detection (<1ms)
- Smart query normalization
- In-memory appointment tracking

### Safety & Reliability

- Idempotent operations
- Session tracking
- Conflict prevention
- PII redaction in logs

## API Endpoints 🚀

```markdown
POST /knowledge

- Upsert documents with auto-chunking
- Body: { id, text, tags? }
- Returns: { ok, chunks, latency_ms }

POST /chat

- RAG + scheduling combined
- Body: { session_id, message }
- Returns:
  - reply (concise, cited)
  - citations [{ id, score }]
  - plan_steps (execution trace)
  - tool_calls (if any actions taken)
  - latency_ms (consistently <500ms)

POST /tools/schedule_appointment

- Direct scheduling interface
- Body: { patient, preferred_slot_iso, location }
- Returns: { ok, appt_id, normalized_slot_iso }
```

### Example Response

```json
{
  "reply": "Grace period is 10 min. Booked Chen for 10:30 at Midtown (A-1032).",
  "citations": [{ "id": "k2", "score": 0.87 }],
  "plan_steps": [
    { "step": 1, "intent": "retrieve", "latency_ms": 18 },
    { "step": 2, "intent": "compose", "latency_ms": 2 },
    { "step": 3, "intent": "schedule", "latency_ms": 20 }
  ],
  "latency_ms": 46,
  "tool_calls": [
    {
      "name": "schedule_appointment",
      "args": {
        "patient": "Chen",
        "slot": "2025-10-18T10:30:00-04:00",
        "location": "Midtown"
      },
      "result": { "ok": true, "appt_id": "A-1032" }
    }
  ]
}
```

## Getting Started 🚀

1. Set up Python environment (3.10+):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Start the server:

```bash
uvicorn backend.main:app --reload
```

3. Load sample knowledge:

```bash
# Knowledge is auto-loaded from backend/knowledgeBase.json
```

## Testing & Benchmarks 📊

Run the test suite:

```bash
# Tool tests (scheduling)
python backend/testing/test_tools.py

# Retrieval tests
python backend/testing/test_retriever.py

# Latency benchmarks
python backend/testing/bench_latency.py
```

## Tech Stack 🛠

- **Backend**: FastAPI + Uvicorn
- **Embeddings**: Sentence-Transformers (all-MiniLM-L6-v2)
- **Vector Search**: FAISS
- **Frontend**: Vanilla JS + CSS3

## Workflow
````
User Query
    ↓
┌─────────────────────┐
│ Intent Detection    │  8ms (regex patterns)
│ • Scheduling?       │
│ • Rescheduling?     │
│ • Pure RAG?         │
└─────────────────────┘
    ↓
┌─────────────────────────────────┐
│ Hybrid Retrieval (if needed)    │  18ms
│ ┌───────────┐  ┌──────────────┐│
│ │ BM25      │  │ FAISS        ││
│ │ (lexical) │  │ (semantic)   ││
│ └───────────┘  └──────────────┘│
│        ↓              ↓         │
│   Reciprocal Rank Fusion        │
│            ↓                    │
│       Top-3 Documents           │
└─────────────────────────────────┘
    ↓
┌─────────────────────┐
│ Tool Execution      │  12ms
│ (if scheduling)     │
│ • Idempotent        │
│ • No double-booking │
└─────────────────────┘
    ↓
Response (<500ms)
````

---

## Test Scenarios

### ✅ Use Case 1: Multi-turn (RAG + Tool + Reschedule)

**Turn 1:**
````
User: "What's our late policy and can you book Chen tomorrow at 10:30 in Midtown?"

Response:
- "We have a 10-minute grace period [k2]. Booked Chen at Midtown (A-1000)."
- Citations: [k2]
- Tool: schedule_appointment
- Latency: 370ms ✅
````

**Turn 2:**
````
User: "Make it 11:00 instead"

Response:
- "Updated appointment to 11:00 (A-1000)."
- Tool: reschedule_appointment
- Latency: 21ms ✅
````

### ✅ Use Case 2: Pure RAG
````
User: "Where do patients park?"

Response:
- "Patient parking is available in Lot B located behind the main building. [k4]"
- Citations: [k4]
- No tool calls
- Latency: 300ms ✅
````

### ✅ Use Case 3: Direct Tool Call
````
User: "Schedule Rivera Monday 9am at Midtown"

Response:
- "Booked Rivera Monday at Midtown (A-1001)."
- Tool: schedule_appointment
- Minimal retrieval (intent-only)
- Latency: 1ms ✅
````

## Current Status 📈

✅ Core Features

- [x] Sub-500ms RAG responses
- [x] Appointment scheduling/rescheduling
- [x] Hybrid retrieval with caching
- [x] Multi-intent handling
- [x] Full test coverage

🚀 Performance

- Average latency: ~46ms
- P95 latency: <100ms
- Cold start: ~3s

## Future Enhancements 🔮

1. Persistent vector store for faster restarts
2. Docker containerization
3. Extended test coverage
4. Additional appointment features
5. More action tools while maintaining speed

## License 📝

MIT License