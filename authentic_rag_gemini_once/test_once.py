"""ทดสอบการทำงานผ่านเทอร์มินัลแบบออฟไลน์ โดยไม่ใช้คีย์ ไม่ดาวน์โหลดโมเดล และไม่ใช้ OpenSearch"""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import app

ROOT = Path(__file__).resolve().parent


class OnceTests(unittest.TestCase):
    def test_waits_for_input_before_initializing_services_and_answers_once(self):
        events = []
        rag = Mock()
        rag.search_for_question.return_value = {"answer": "คำตอบทดสอบ", "results": []}
        def read(prompt):
            events.append("input")
            return "  คำถามของฉัน  "
        def factory():
            self.assertEqual(events, ["input"])
            events.append("initialize")
            return rag
        output = []
        with tempfile.TemporaryDirectory() as folder, patch.object(app, "ROOT", Path(folder)):
            with patch.object(app, "indexed_topics", return_value=[{"title": "หัวข้อทดสอบ"}]):
                self.assertEqual(app.ask_once(read, output.append, factory), 0)
            saved = json.loads((Path(folder) / "authentic_rag_search_results.json").read_text(encoding="utf-8"))
        rag.search_for_question.assert_called_once_with("คำถามของฉัน", k=5)
        self.assertEqual(saved["answer"], "คำตอบทดสอบ")
        self.assertTrue(any("คำตอบทดสอบ" in line for line in output))

    def test_blank_question_exits_without_initialization(self):
        factory = Mock()
        self.assertEqual(app.ask_once(lambda _: "  ", lambda _: None, factory), 0)
        factory.assert_not_called()

    def test_eof_exits_without_initialization(self):
        factory = Mock()
        read = Mock(side_effect=EOFError)
        self.assertEqual(app.ask_once(read, lambda _: None, factory), 130)
        factory.assert_not_called()

    def test_failure_does_not_retry_or_prompt_again(self):
        read = Mock(return_value="question")
        factory = Mock(side_effect=RuntimeError("OpenSearch unavailable"))
        self.assertEqual(app.ask_once(read, lambda _: None, factory), 1)
        read.assert_called_once()
        factory.assert_called_once()

    def test_ingestion_does_not_ask_questions(self):
        rag = Mock()
        rag.load_documents.return_value = ["chunk"]
        rag.add_documents_with_context.return_value = 1
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(app, "MANIFEST", Path(folder) / "manifest.json"):
                with patch.object(app, "make_rag", return_value=rag):
                    self.assertEqual(app.ingest(), 0)
        rag.search_for_question.assert_not_called()
        rag.add_documents_with_context.assert_called_once_with(["chunk"])

    def test_retrieval_is_unchanged(self):
        def get_methods(path):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
            return {n.name: ast.dump(n) for n in cls.body if isinstance(n, ast.FunctionDef)}
        for filename in ("authenticRAG.py", "onlysearchAuthenticRAG.py"):
            before = get_methods(ROOT.parent / "baseline_gemini" / filename)
            after = get_methods(ROOT / filename)
            for name in ("sparse_search", "dense_search", "rrf_fusion", "hybrid_search"):
                self.assertEqual(before[name], after[name])

    def test_real_entry_point_accepts_blank_without_dependencies(self):
        result = subprocess.run([sys.executable, str(ROOT / "onlysearchAuthenticRAG.py")],
                                input="\n", capture_output=True, text=True,
                                encoding="utf-8", env={**__import__("os").environ, "PYTHONUTF8": "1"},
                                timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("อยากทราบอะไร", result.stdout)
        self.assertIn("จบโปรแกรม", result.stdout)


if __name__ == "__main__":
    unittest.main()
