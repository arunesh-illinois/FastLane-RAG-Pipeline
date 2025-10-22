import re
from typing import List, Tuple, Dict
import numpy as np
import faiss


class HybridRetriever:
    """
    Hybrid retrieval: BM25 (lexical) + FAISS (semantic) with RRF fusion
    """

    def __init__(self, model, index, documents, doc_ids):
        self.model = model
        self.index = index
        self.documents = documents
        self.doc_ids = doc_ids

    def normalize_query(self, query: str) -> str:
        """Normalize query for better matching"""
        # Lowercase and remove extra whitespace
        query = query.lower().strip()
        query = re.sub(r'\s+', ' ', query)
        return query

    def bm25_search(self, query: str, top_k: int = 8) -> List[Tuple[str, float]]:
        """
        Simple BM25-like lexical search
        Scores based on term overlap
        """
        query_terms = set(self.normalize_query(query).split())
        scores = []

        for doc_id in self.doc_ids:
            text = self.documents[doc_id]["text"].lower()
            doc_terms = set(text.split())

            # Calculate overlap score
            overlap = len(query_terms & doc_terms)

            # Normalize by query length
            score = overlap / max(len(query_terms), 1)

            scores.append((doc_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def semantic_search(self, query: str, top_k: int = 8) -> List[Tuple[str, float]]:
        """
        FAISS vector similarity search
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        # Encode query
        query_emb = self.model.encode([query], show_progress_bar=False)

        # Normalize for cosine similarity
        faiss.normalize_L2(query_emb)

        # Search
        scores, indices = self.index.search(query_emb, min(top_k, self.index.ntotal))

        # Format results
        results = [
            (self.doc_ids[idx], float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx < len(self.doc_ids)  # Safety check
        ]

        return results

    def reciprocal_rank_fusion(
            self,
            lexical_results: List[Tuple[str, float]],
            semantic_results: List[Tuple[str, float]],
            k: int = 60
    ) -> List[Tuple[str, float]]:
        """
        Merge lexical and semantic results using RRF
        RRF score = sum(1 / (k + rank))
        """
        rrf_scores = {}

        # Add lexical ranks
        for rank, (doc_id, _) in enumerate(lexical_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)

        # Add semantic ranks
        for rank, (doc_id, _) in enumerate(semantic_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)

        # Sort by RRF score
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_docs

    def apply_mmr(self, fused_results, query: str, top_k: int = 3, lambda_param: float = 0.7):
        """
        Apply Maximal Marginal Relevance (MMR) to diversify results
        fused_results: list of (doc_id, score) from RRF
        """
        if not fused_results:
            return []

        # Encode query embedding
        query_emb = self.model.encode([query], show_progress_bar=False)
        faiss.normalize_L2(query_emb)

        # Encode top candidate docs
        candidate_ids = [doc_id for doc_id, _ in fused_results[:8]]
        candidate_texts = [self.documents[doc_id]["text"] for doc_id in candidate_ids]
        doc_embs = self.model.encode(candidate_texts, show_progress_bar=False)
        faiss.normalize_L2(doc_embs)

        # Compute similarities
        sim_query_doc = np.dot(doc_embs, query_emb.T).flatten()
        sim_doc_doc = np.dot(doc_embs, doc_embs.T)

        selected = []
        candidates = list(range(len(candidate_ids)))

        # Select first doc with highest similarity to query
        first = np.argmax(sim_query_doc)
        selected.append(first)
        candidates.remove(first)

        # Select remaining docs with MMR
        while len(selected) < top_k and candidates:
            mmr_scores = []
            for idx in candidates:
                redundancy = max(sim_doc_doc[idx][selected]) if selected else 0
                mmr_score = lambda_param * sim_query_doc[idx] - (1 - lambda_param) * redundancy
                mmr_scores.append(mmr_score)

            # Select best candidate
            best_idx = candidates[np.argmax(mmr_scores)]
            selected.append(best_idx)
            candidates.remove(best_idx)

        # Return selected top-k docs (preserving IDs and scores)
        final_docs = [(candidate_ids[i], float(sim_query_doc[i])) for i in selected]
        return final_docs

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Main retrieval pipeline:
        1. Normalize query
        2. BM25 lexical search (top-8)
        3. FAISS semantic search (top-8)
        4. RRF fusion
        5. Return top-K
        """
        import time

        # Timing breakdown
        timings = {}

        # Normalize
        start = time.time()
        normalized_query = self.normalize_query(query)
        timings['normalize'] = (time.time() - start) * 1000

        # Lexical search
        start = time.time()
        lexical_results = self.bm25_search(normalized_query, top_k=8)
        timings['lexical'] = (time.time() - start) * 1000

        # Semantic search
        start = time.time()
        semantic_results = self.semantic_search(query, top_k=8)
        timings['semantic'] = (time.time() - start) * 1000

        # Fusion
        start = time.time()
        fused_results = self.reciprocal_rank_fusion(lexical_results, semantic_results)
        timings['fusion'] = (time.time() - start) * 1000

        # Apply MMR for diversity
        start = time.time()
        mmr_results = self.apply_mmr(fused_results, query, top_k=top_k, lambda_param=0.7)
        timings['mmr'] = (time.time() - start) * 1000

        # Get top-K documents
        top_docs = mmr_results[:top_k]

        # Format output
        results = []
        for doc_id, score in top_docs:
            results.append({
                "id": doc_id,
                "text": self.documents[doc_id]["text"],
                "score": round(score, 3),
                "tags": self.documents[doc_id].get("tags", [])
            })

        return results