"""Reproduce the Gemini baseline from the untouched files in upstream/."""
from pathlib import Path
import difflib

ROOT = Path(__file__).resolve().parent


def replace_once(text, old, new):
    if old not in text:
        raise ValueError(f"Upstream changed; missing fragment: {old[:80]}")
    return text.replace(old, new)


patches = []
for filename in ("authenticRAG.py", "onlysearchAuthenticRAG.py"):
    original = (ROOT / "upstream" / filename).read_text(encoding="utf-8")
    code = original
    for line in ("import numpy as np\n", "import time\n", "from tqdm import tqdm\n",
                 "from langchain.schema import Document as LangchainDocument\n",
                 "from langchain_community.document_loaders import TextLoader\n"):
        code = code.replace(line, "")
    code = code.replace("from pathlib import Path\n", "")
    code = code.replace("# pip install opensearchpy sentence-transformers llama-index llama-index-embeddings-huggingface openai",
                        "# python -m pip install -r requirements.txt")
    code = "# Adapted from aekanun2020/2025-authenticRAG; see README.md.\n" + code
    code = code.replace("import os\n", "import os\nfrom pathlib import Path\nfrom dotenv import load_dotenv\n", 1)
    position = code.index("class ")
    code = code[:position] + 'ROOT = Path(__file__).resolve().parent\nload_dotenv(ROOT / ".env")\n\n' + code[position:]
    code = replace_once(code, "OPENROUTER_API_KEY", "GEMINI_API_KEY")
    code = replace_once(code, "https://openrouter.ai/api/v1", "https://generativelanguage.googleapis.com/v1beta/openai/")
    code = code.replace("Qwen API ผ่าน OpenRouter", "Gemini API ผ่าน OpenAI-compatible endpoint")
    code = code.replace("Qwen API", "Gemini API").replace("call_qwen_api", "call_gemini_api")
    code = replace_once(code, '        # ตั้งค่า embedding model',
        '        self.gemini_model = os.environ.get("GEMINI_MODEL", "").strip()\n'
        '        if not self.gemini_model:\n'
        '            raise ValueError("Set GEMINI_MODEL in .env to a model available to your API key")\n\n'
        '        # ตั้งค่า embedding model')
    code = replace_once(code, 'model="qwen/qwen-2.5-72b-instruct"', 'model=self.gemini_model')
    code = replace_once(code, 'return completion.choices[0].message.content',
        'text = completion.choices[0].message.content\n'
        '            if not text or not text.strip():\n'
        '                raise RuntimeError("Gemini returned empty text; inspect model and token limit")\n'
        '            return text')
    code = replace_once(code, '            return f"Gemini API error: {str(e)}"',
        '            raise RuntimeError("Gemini request failed; no error text will be indexed") from e')
    code = replace_once(code, '"anthropic-vector-index"', '"baseline-gemini-vector-index"')
    code = replace_once(code, '"anthropic-bm25-index"', '"baseline-gemini-bm25-index"')
    code = replace_once(code, 'opensearch_port=9200\n', 'opensearch_port=int(os.environ.get("OPENSEARCH_PORT", "9200"))\n')
    code = replace_once(code, 'opensearch_host="localhost",  # OpenSearch IP ตามที่ให้ไว้',
        'opensearch_host=os.environ.get("OPENSEARCH_HOST", "localhost"),')
    if filename == "authenticRAG.py":
        code = code.replace("from llama_index.core import Document\n", "from llama_index.core import Document\nfrom types import SimpleNamespace\n")
        code = replace_once(code, 'MarkdownNodeParser(chunk_size=256)', 'MarkdownNodeParser.from_defaults()')
        start = code.index('        # อ่านไฟล์ด้วย TextLoader')
        end = code.index('    def get_context_prompt', start)
        code = code[:start] + '''        # Preserve Markdown heading-based chunks without LangChain conversions.
        llama_docs = [
            Document(text=Path(path).read_text(encoding="utf-8"),
                     metadata={"source": str(path)})
            for path in md_paths
        ]
        chunks = self.md_parser.get_nodes_from_documents(llama_docs)
        print(f"Split documents into {len(chunks)} chunks")
        return [SimpleNamespace(page_content=node.text, metadata=node.metadata)
                for node in chunks]

''' + code[end:]
        code = code.replace("'./corpus_input'", "ROOT / 'corpus_input'")
        for name in ("1.md", "2.md", "44.md", "5555.md"):
            code = replace_once(code, f'"./corpus_input/{name}"', f'str(ROOT / "corpus_input" / "{name}")')
        code = replace_once(code, 'print("Some errors occurred during vector bulk upload.")',
            'raise RuntimeError("Vector bulk upload failed; inspect OpenSearch response")')
        code = replace_once(code, 'print("Some errors occurred during BM25 bulk upload.")',
            'raise RuntimeError("BM25 bulk upload failed; inspect OpenSearch response")')
    else:
        code = replace_once(code, '"authentic_rag_search_results.json")',
            'str(ROOT / "authentic_rag_search_results.json"))')
    code = code.replace("export GEMINI_API_KEY='your_api_key_here'", "copy .env.example to .env and set GEMINI_API_KEY and GEMINI_MODEL")
    (ROOT / filename).write_text(code, encoding="utf-8")
    patches.extend(difflib.unified_diff(original.splitlines(keepends=True), code.splitlines(keepends=True),
                   fromfile=f"upstream/{filename}", tofile=filename))
(ROOT / "changes_from_upstream.patch").write_text("".join(patches), encoding="utf-8")
print("Created two Gemini scripts and changes_from_upstream.patch")
