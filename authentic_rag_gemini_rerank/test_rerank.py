"""ทดสอบออฟไลน์ด้วยผลค้นหาและตัวจัดอันดับจำลอง โดยไม่เรียก API หรือดาวน์โหลดโมเดล"""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import app
from onlysearchAuthenticRAG import AuthenticSearchRAG

ROOT = Path(__file__).resolve().parent


def fake_rag(sparse, dense, scores):
    rag = AuthenticSearchRAG.__new__(AuthenticSearchRAG)
    rag.sparse_search = Mock(return_value=sparse)
    rag.dense_search = Mock(return_value=dense)
    rag._reranker = Mock()
    rag._reranker.predict.return_value = scores
    return rag


def hit(number):
    return (f"doc_{number}", 1.0, {"content": f"passage {number}"})


class RerankTests(unittest.TestCase):
    def test_reranker_changes_order_and_keeps_both_scores(self):
        rag = fake_rag([hit(1), hit(2)], [hit(1), hit(2)], [-1.0, 3.0])
        result = rag.hybrid_search("question", k=1)
        self.assertEqual(result[0][0], "doc_2")
        self.assertEqual(result[0][2]["rrf_rank"], 2)
        self.assertEqual(result[0][2]["rerank_score"], 3.0)
        self.assertIn("rrf_score", result[0][2])
        pairs = rag._reranker.predict.call_args.args[0]
        self.assertEqual(pairs[1][0], "question")
        self.assertIn("passage 2", pairs[1][1])

    def test_twenty_candidates_and_five_selected_with_deduplication(self):
        hits = [hit(i) for i in range(20)]
        rag = fake_rag(hits, hits, list(range(20)))
        selected = rag.hybrid_search("q")
        rag.sparse_search.assert_called_once_with("q", k=20)
        rag.dense_search.assert_called_once_with("q", k=20)
        self.assertEqual(len(selected), 5)
        self.assertEqual(rag.retrieval_trace["candidate_count"], 20)
        self.assertEqual(len(set(item["doc_id"] for item in rag.retrieval_trace["candidates"])), 20)

    def test_union_is_capped_at_twenty_before_predict(self):
        rag = fake_rag([hit(i) for i in range(20)], [hit(i) for i in range(20, 40)], [1] * 20)
        rag.hybrid_search("q")
        self.assertEqual(len(rag._reranker.predict.call_args.args[0]), 20)

    def test_ties_preserve_rrf_order(self):
        rag = fake_rag([hit(1), hit(2)], [], [0.5, 0.5])
        self.assertEqual([r[0] for r in rag.hybrid_search("q")], ["doc_1", "doc_2"])

    def test_empty_search_does_not_predict_or_generate(self):
        rag = fake_rag([], [], [])
        rag.generate_response = Mock()
        result = rag.search_for_question("q")
        self.assertEqual(result["results"], [])
        rag._reranker.predict.assert_not_called()
        rag.generate_response.assert_not_called()

    def test_invalid_or_failed_reranker_does_not_call_gemini(self):
        for scores in ([], [float("nan")], [float("inf")]):
            rag = fake_rag([hit(1)], [], scores)
            rag.generate_response = Mock()
            with self.assertRaises(RuntimeError):
                rag.search_for_question("q")
            rag.generate_response.assert_not_called()
        rag = fake_rag([hit(1)], [], [])
        rag._reranker.predict.side_effect = RuntimeError("failed")
        with self.assertRaises(RuntimeError):
            rag.hybrid_search("q")

    def test_answer_receives_reranked_text_and_result_contains_trace(self):
        rag = fake_rag([hit(1), hit(2)], [], [0, 1])
        rag.generate_response = Mock(return_value="answer")
        result = rag.search_for_question("q", k=1)
        self.assertEqual(result["answer"], "answer")
        self.assertEqual(result["results"][0]["doc_id"], "doc_2")
        self.assertEqual(result["results"][0]["rrf_rank"], 2)
        context = rag.generate_response.call_args.args[1]
        self.assertIn("passage 2", context)
        self.assertNotIn("passage 1", context)
        json.dumps(result)

    def test_cli_waits_for_question_then_answers_once(self):
        events = []
        rag = Mock()
        rag.search_for_question.return_value = {"answer": "test answer", "results": []}
        def read(prompt):
            events.append("input")
            return " question "
        def factory():
            self.assertEqual(events, ["input"])
            return rag
        output = []
        with tempfile.TemporaryDirectory() as folder, patch.object(app, "ROOT", Path(folder)):
            with patch.object(app, "indexed_topics", return_value=[{"title": "topic"}]):
                self.assertEqual(app.ask_once(read, output.append, factory), 0)
        rag.search_for_question.assert_called_once_with("question", k=5)

    def test_blank_real_cli_exits_without_services(self):
        import os
        result = subprocess.run([sys.executable, str(ROOT / "onlysearchAuthenticRAG.py")],
                                input="\n", capture_output=True, text=True, encoding="utf-8",
                                env={**os.environ, "PYTHONUTF8": "1"}, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("อยากทราบอะไร", result.stdout)

    def test_gemini_prompt_and_retrieval_primitives_match_version_one(self):
        def methods(path):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
            return {node.name: ast.dump(node) for node in cls.body if isinstance(node, ast.FunctionDef)}
        before = methods(ROOT.parent / "authentic_rag_gemini_once" / "onlysearchAuthenticRAG.py")
        after = methods(ROOT / "baseline_search.py")
        for name in ("call_gemini_api", "generate_response", "truncate_context",
                     "sparse_search", "dense_search", "rrf_fusion"):
            self.assertEqual(before[name], after[name])


if __name__ == "__main__":
    unittest.main()
