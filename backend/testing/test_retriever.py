from sentence_transformers import SentenceTransformer  # Only for embeddings, not LLM
import faiss
import json

from backend.services.knowledgeRetriever import HybridRetriever

## Load model
model = SentenceTransformer('all-MiniLM-L6-v2')  # Only for embeddings, not LLM

# Load documents
with open('backend/knowledgeBase.json', 'r') as f:
    docs = json.load(f)

documents = {d["id"]: d for d in docs}

# Build index
texts = [d["text"] for d in docs]
doc_ids = [d["id"] for d in docs]
embeddings = model.encode(texts)

dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
faiss.normalize_L2(embeddings)
index.add(embeddings)

# Create retriever
retriever = HybridRetriever(model, index, documents, doc_ids)

# Test queries
test_queries = [
    "Where can I park?",
    "What happens if I'm late?",
    "Do you accept insurance?",
    "Do you accept cash payment?"
]

for query in test_queries:
    print(f"\n🔍 Query: {query}")
    results = retriever.retrieve(query, top_k=3)
    for i, doc in enumerate(results, 1):
        print(f"  {i}. [{doc['id']}] (score: {doc['score']}) {doc['text'][:80]}...")