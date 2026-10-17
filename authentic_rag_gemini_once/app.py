"""ควบคุมการใช้งานผ่านเทอร์มินัล สำหรับนำเข้าเอกสารหรือรับคำถามเพียงหนึ่งครั้ง"""
import json
import os
import io
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "indexed_documents.json"


def documents():
    paths = sorted((ROOT / "corpus_input").glob("*.md"))
    if not paths:
        raise ValueError("ไม่พบไฟล์ .md ใน corpus_input")
    return paths


def titles(paths):
    result = []
    for path in paths:
        heading = next((line[2:].strip() for line in path.read_text(encoding="utf-8").splitlines()
                        if line.startswith("# ")), path.stem)
        result.append({"file": path.name, "title": heading})
    return result


def indexed_topics():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))["documents"]
    return titles(documents())


def make_rag(ingestion=False):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    for name in ("GEMINI_API_KEY", "GEMINI_MODEL"):
        if not os.environ.get(name, "").strip():
            raise ValueError(f"กรุณาตั้งค่า {name} ใน .env")
    host = os.environ.get("OPENSEARCH_HOST", "localhost")
    port = int(os.environ.get("OPENSEARCH_PORT", "9200"))
    if ingestion:
        from authenticRAG import AnthropicStyleContextualRAG
        return AnthropicStyleContextualRAG(host, port)
    # ตรวจว่ามีข้อมูลในดัชนีก่อนโหลดโมเดลแปลงข้อความเป็นเวกเตอร์
    from opensearchpy import OpenSearch
    client = OpenSearch(hosts=[{"host": host, "port": port}], use_ssl=False)
    for index in ("once-gemini-vector-index", "once-gemini-bm25-index"):
        if not client.indices.exists(index=index) or client.count(index=index)["count"] == 0:
            raise ValueError("ยังไม่มีข้อมูลใน OpenSearch กรุณารัน authenticRAG.py ก่อน")
    from onlysearchAuthenticRAG import AuthenticSearchRAG
    return AuthenticSearchRAG(host, port)


def ingest():
    try:
        paths = documents()
        rag = make_rag(ingestion=True)
        chunks = rag.load_documents([str(path) for path in paths])
        if not chunks:
            raise ValueError("ไม่พบ Chunk ที่นำเข้าได้")
        count = rag.add_documents_with_context(chunks)
        MANIFEST.write_text(json.dumps({"documents": titles(paths), "chunks": count},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nนำเข้าเรียบร้อย {count} Chunk — เปิด onlysearchAuthenticRAG.py เพื่อถามคำถาม")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nยกเลิกการนำเข้า")
        return 130
    except Exception as error:
        print(f"นำเข้าไม่สำเร็จ: {error}")
        return 1


def ask_once(input_fn=input, output_fn=print, rag_factory=None):
    """รับคำถามครั้งเดียวและตอบไม่เกินหนึ่งครั้ง หากคำถามว่างให้จบโดยไม่เชื่อมต่อบริการ"""
    try:
        topics = indexed_topics()
        output_fn("หัวข้อในเอกสารที่มี:")
        for item in topics:
            output_fn(f"• {item['title']}")
        question = input_fn("\nอยากทราบอะไรเกี่ยวกับหัวข้อในเอกสาร?\n> ").strip()
        if not question:
            output_fn("ไม่ได้พิมพ์คำถาม จบโปรแกรม")
            return 0
        output_fn("\nกำลังค้นหาข้อมูลและสร้างคำตอบ...")
        rag = (rag_factory or make_rag)()
        # ซ่อนข้อความแสดงรายละเอียดส่วนย่อยจากคลาสเดิม เพื่อให้หน้าถามตอบอ่านง่าย
        with redirect_stdout(io.StringIO()):
            result = rag.search_for_question(question, k=5)
        output_fn(f"\nคำตอบ:\n{result['answer']}")
        # บันทึกผลล่าสุดพร้อมข้อความส่วนย่อยที่ค้นได้ไว้ตรวจสอบ
        try:
            (ROOT / "authentic_rag_search_results.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            output_fn("บันทึกผลไม่สำเร็จ แต่แสดงคำตอบแล้ว")
        output_fn("\nจบโปรแกรม หากต้องการถามอีก ให้เปิดโปรแกรมใหม่")
        return 0
    except (KeyboardInterrupt, EOFError):
        output_fn("\nยกเลิก จบโปรแกรม")
        return 130
    except Exception as error:
        output_fn(f"ไม่สามารถตอบคำถามได้: {error}")
        output_fn("ตรวจ .env, แพ็กเกจ และ OpenSearch แล้วเปิดโปรแกรมใหม่")
        return 1
