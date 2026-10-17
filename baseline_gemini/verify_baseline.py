"""Offline behavioral checks; no dependencies, downloads, or API calls."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent


def methods(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}


def bind(node):
    scope = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<method>", "exec"), scope)
    return scope[node.name]


class BaselineChecks(unittest.TestCase):
    def test_retrieval_matches_upstream(self):
        for filename in ("authenticRAG.py", "onlysearchAuthenticRAG.py"):
            before, after = methods(ROOT / "upstream" / filename), methods(ROOT / filename)
            for name in ("sparse_search", "dense_search", "rrf_fusion", "hybrid_search"):
                self.assertEqual(ast.dump(before[name]), ast.dump(after[name]))

    def test_rrf_combines_shared_hits_with_original_zero_based_rank(self):
        method = bind(methods(ROOT / "onlysearchAuthenticRAG.py")["rrf_fusion"])
        result = method(None, [[("a", 99, {}), ("b", 90, {})], [("b", 0.9, {})]])
        self.assertEqual(result[0][0], "b")
        self.assertAlmostEqual(result[0][1], 1 / 61 + 1 / 60)

    def test_gemini_call_uses_configured_model(self):
        captured = {}
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))])
        instance = SimpleNamespace(gemini_model="model-from-env", client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
        method = bind(methods(ROOT / "authenticRAG.py")["call_gemini_api"])
        self.assertEqual(method(instance, "question", max_tokens=100, temperature=0.1), "answer")
        self.assertEqual(captured["model"], "model-from-env")
        self.assertEqual(captured["max_tokens"], 100)
        self.assertEqual(captured["temperature"], 0.1)

    def test_empty_response_raises_instead_of_indexing_error(self):
        def create(**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))])
        instance = SimpleNamespace(gemini_model="test", client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
        method = bind(methods(ROOT / "authenticRAG.py")["call_gemini_api"])
        with self.assertRaises(RuntimeError):
            method(instance, "question")

    def test_no_hits_does_not_call_llm(self):
        instance = SimpleNamespace(hybrid_search=lambda *args, **kwargs: [])
        method = bind(methods(ROOT / "onlysearchAuthenticRAG.py")["search_for_question"])
        self.assertEqual(method(instance, "question")["results"], [])


if __name__ == "__main__":
    unittest.main()
