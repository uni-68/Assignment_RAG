"""แบบที่ 2 ค้นผู้สมัคร 20 ส่วน จัดอันดับใหม่ แล้วให้ Gemini ตอบเพียงครั้งเดียว"""
import math
import os
from time import perf_counter

from baseline_search import AuthenticSearchRAG as BaselineSearchRAG


class AuthenticSearchRAG(BaselineSearchRAG):
    candidate_count = 20

    def _load_reranker(self):
        if getattr(self, "_reranker", None) is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(
                os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
                max_length=512,
            )
        return self._reranker

    def hybrid_search(self, query, k=5, rrf_k=60):
        if k < 1 or k > self.candidate_count:
            raise ValueError("k must be between 1 and 20")
        self.retrieval_trace = {"candidate_count": 0, "candidates": [], "rerank_seconds": 0.0}
        sparse = self.sparse_search(query, k=self.candidate_count)
        dense = self.dense_search(query, k=self.candidate_count)
        candidates = self.rrf_fusion([sparse, dense], k=rrf_k)[:self.candidate_count]
        if not candidates:
            return []
        # ใช้ข้อความและบริบทจากช่องข้อมูลเดียวกับที่แบบที่ 1 ส่งให้โมเดลสร้างคำตอบ
        pairs = [(query, f"{doc.get('content', '')}\n{doc.get('contextualized_content', '')}")
                 for _, _, doc in candidates]
        started = perf_counter()
        scores = self._load_reranker().predict(pairs, batch_size=2, show_progress_bar=False)
        scores = [float(score) for score in scores]
        if len(scores) != len(candidates) or not all(math.isfinite(score) for score in scores):
            raise RuntimeError("Reranker returned invalid scores; stopped without calling Gemini")
        ranked = []
        for rrf_rank, ((doc_id, rrf_score, doc), score) in enumerate(zip(candidates, scores), 1):
            annotated = dict(doc, rrf_score=rrf_score, rrf_rank=rrf_rank, rerank_score=score)
            ranked.append((doc_id, score, annotated))
        # หากคะแนนเท่ากัน ให้คงลำดับเดิมจาก RRF ด้วยการเรียงแบบรักษาลำดับของ Python
        ranked.sort(key=lambda item: item[1], reverse=True)
        self.retrieval_trace = {
            "candidate_count": len(candidates),
            "rerank_seconds": perf_counter() - started,
            "candidates": [
                {"doc_id": doc_id, "rrf_rank": doc["rrf_rank"], "rrf_score": doc["rrf_score"],
                 "rerank_rank": rank, "rerank_score": score, "content": doc.get("content", ""),
                 "context": doc.get("contextualized_content", "")}
                for rank, (doc_id, score, doc) in enumerate(ranked, 1)
            ],
        }
        return ranked[:k]

    def search_for_question(self, question, k=5):
        # ใช้ข้อความคำสั่ง วิธีตัดบริบท โมเดล Gemini และค่าการสร้างคำตอบเดิมของแบบที่ 1
        result = super().search_for_question(question, k=k)
        trace = self.retrieval_trace
        selected = {item["doc_id"]: item for item in trace["candidates"]}
        for item in result["results"]:
            detail = selected[item["doc_id"]]
            item.update({key: detail[key] for key in
                         ("rrf_rank", "rrf_score", "rerank_rank", "rerank_score")})
        result["retrieval"] = {
            "version": "2-rerank", "score_type": "reranker relevance (not probability)",
            "reranker_model": os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
            "reranker_max_length": 512, "candidates_per_search": self.candidate_count,
            **trace,
        }
        return result


def main():
    from app import ask_once
    return ask_once()


if __name__ == "__main__":
    raise SystemExit(main())
