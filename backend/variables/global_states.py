from backend.services.lru_cache import LRUCache

documents = {}
index = None
doc_ids = []
model = None
retriever = None
session_context = {}
query_cache = LRUCache(capacity=30)