# RAG Baseline — Gemini API

ดัดแปลงจาก https://github.com/aekanun2020/2025-authenticRAG
ดาวน์โหลดต้นฉบับเมื่อ 17 ตุลาคม 2026 เก็บสำเนาที่ใช้เทียบไว้ใน `upstream/`
ชุดนี้สร้างใหม่ในแชตปัจจุบัน ไม่ใช่ไฟล์ ZIP ที่แชตเดิมเคยสร้าง

## ต้องติดตั้งอะไร

| รายการ | หน้าที่ |
| --- | --- |
| Python 3.10+ (แนะนำ 3.11 สำหรับชุดนี้) | รันสคริปต์ |
| Docker Desktop พร้อม Linux containers | รัน OpenSearch 2.19.1 |
| openai | เรียก Gemini ผ่าน endpoint ที่รองรับรูปแบบ OpenAI |
| opensearch-py | สร้างดัชนี เก็บข้อมูล และค้นหา |
| sentence-transformers | โหลด BAAI/bge-m3 และสร้าง embedding บนเครื่อง |
| llama-index-core | Document และ MarkdownNodeParser |
| python-dotenv | อ่านค่าจาก .env |
| Gemini API key และชื่อโมเดลที่บัญชีใช้ได้ | สร้างบริบทและคำตอบ |

requirements.txt รวมแพ็กเกจ Python แล้ว ไม่ต้องติดตั้ง Ollama, google-genai,
LangChain หรือ Conda เพิ่มสำหรับโค้ดที่ปรับชุดนี้ PyTorch จะมากับ dependencies ของ
sentence-transformers โดยการใช้ GPU ต้องจัดรุ่น PyTorch/CUDA ให้ตรงเครื่องเพิ่มเติม
CPU ใช้ได้แต่ช้ากว่า การโหลด BAAI/bge-m3 ครั้งแรกต้องใช้อินเทอร์เน็ตและพื้นที่หลาย GB
README ต้นฉบับแนะนำ RAM 8 GB ขึ้นไป แต่เครื่องต้องรองรับทั้ง OpenSearch และ embedding
พร้อมกัน จึงต้องพิจารณาหน่วยความจำที่เหลือจริงด้วย

## ติดตั้งและรันบน PowerShell

เปิด terminal ในโฟลเดอร์นี้:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

แก้ `.env` ใส่ `GEMINI_API_KEY` และ `GEMINI_MODEL` ที่บัญชีเรียกได้
ตรวจชื่อโมเดลจาก https://ai.google.dev/gemini-api/docs/models
อย่าใส่ key ลงในโค้ดหรือ commit `.env`

เปิด Docker Desktop แล้วใช้:

```powershell
docker compose up -d
Invoke-RestMethod http://localhost:9200
.\.venv\Scripts\python.exe authenticRAG.py
.\.venv\Scripts\python.exe onlysearchAuthenticRAG.py
```

รอ OpenSearch พร้อมก่อนรัน Python หากยังเชื่อมต่อไม่ได้ ให้ดู `docker compose logs opensearch`
หากเครื่องมี service ที่ใช้พอร์ต 9200 อยู่แล้ว เปลี่ยน `OPENSEARCH_PORT` ใน `.env`
Compose นี้ผูก service แบบไม่มี authentication ไว้กับ 127.0.0.1 สำหรับทดลองบนเครื่องเท่านั้น

ขั้นนำเข้าเรียก Gemini หนึ่งครั้งต่อ Chunk และ authenticRAG.py ทดลองถามอีกสองคำถาม
ขั้นค้นหาใน onlysearchAuthenticRAG.py ถามชุดเดิมห้าคำถาม เรียก Gemini เพื่อสร้างคำตอบ
ผลการเรียกขึ้นกับโควตาและค่าบริการของบัญชี จึงยังไม่ได้เรียก API จริงในแชตนี้

## ระบบทำงานอย่างไร

**นำเข้า — authenticRAG.py**

1. อ่าน Markdown ตัวอย่าง 1.md, 2.md, 44.md และ 5555.md แบบ UTF-8
2. แบ่งตามหัวข้อ Markdown ด้วย MarkdownNodeParser
3. ให้ Gemini เขียนบริบทสั้นของแต่ละ Chunk
4. รวมข้อความ Chunk + บริบท แล้วใช้ BAAI/bge-m3 สร้างเวกเตอร์
5. เก็บในสองดัชนี: baseline-gemini-vector-index สำหรับเวกเตอร์ และ
   baseline-gemini-bm25-index สำหรับข้อความและบริบท
6. refresh ดัชนี แล้วทดลองถามสองคำถามตามต้นฉบับ

**ค้นหา — onlysearchAuthenticRAG.py**

1. BM25 ค้นคำและความเกี่ยวข้องใน content กับ contextualized_content ได้ไม่เกิน 10 Chunk
2. BAAI/bge-m3 แปลงคำถามเป็นเวกเตอร์ แล้วค้นเวกเตอร์ใกล้เคียงไม่เกิน 10 Chunk
3. RRF รวมอันดับทั้งสองรายการ ใช้ k=60 และ rank เริ่มที่ 0 ตามต้นฉบับ
4. เลือก 5 Chunk แรก นำข้อความและบริบทที่มีให้ Gemini สร้างคำตอบ
5. บันทึกคำถาม คำตอบ เนื้อหา และคะแนนลง authentic_rag_search_results.json

Embedding ไม่ได้ส่งไป Gemini: ทำบนเครื่อง ส่วนข้อความที่ใช้สร้างบริบทและคำตอบ
จะส่งไป Gemini API ไม่มีการฝึกหรือ fine-tune โมเดลในระบบนี้

## เปลี่ยนจาก GitHub ตรงไหน

| ส่วน | ต้นฉบับ | ชุดนี้ |
| --- | --- | --- |
| API | OpenRouter | Gemini endpoint ผ่าน openai library |
| Key | OPENROUTER_API_KEY | GEMINI_API_KEY ใน .env |
| โมเดล LLM | Qwen กำหนดในโค้ด | GEMINI_MODEL กำหนดใน .env |
| อ่าน Markdown | TextLoader + แปลงผ่าน LangChain | Path.read_text UTF-8 + LlamaIndex โดยตรง |
| Markdown parser | ส่ง chunk_size=256 ให้ MarkdownNodeParser | from_defaults แบ่งตามหัวข้ออย่างชัดเจน |
| ชื่อดัชนี | anthropic-* | baseline-gemini-* แยกจากข้อมูลเดิม |
| path | ขึ้นกับ directory ที่สั่งรัน | อ้างจากตำแหน่งไฟล์สคริปต์ |
| API ว่าง/ล้มเหลว | คืนข้อความ error ซึ่งอาจถูกนำไปทำ embedding | ยก exception หยุดงาน |
| bulk upload error | แสดงข้อความแล้วทำงานต่อ | ยก exception |
| ติดตั้ง | คำสั่งกระจายในคู่มือ | requirements.txt และ compose.yaml |

MarkdownNodeParser แบ่งตามหัวข้อ ไม่ควรตีความว่าทุก Chunk มีขนาด 256 tokens
ชุดนี้ไม่ได้เพิ่มตัวแบ่งตามจำนวน tokens หรือ overlap จึงยังมี Chunk ยาวได้

ยังคง BAAI/bge-m3, BM25 standard analyzer, Vector Search, RRF และ Top-5 ตามต้นฉบับ
ยังไม่ได้เพิ่ม reranker หรือพิสูจน์ว่าค้นคืนดีขึ้น การเปลี่ยน API และปรับโครงสร้างโค้ด
ชุดนี้เป็น Baseline สำหรับข้อ (1) ยังไม่ใช่เวอร์ชันปรับปรุงตามข้อ (2) ของโจทย์
ต้องใช้ Gemini รุ่นเดียวกันและค่าร่วมเดียวกันเมื่อเปรียบเทียบกับเวอร์ชันปรับปรุง

## ข้อจำกัดที่คงจากต้นฉบับ

- `full_doc_content = doc.page_content` ส่งเฉพาะ Chunk ให้ Gemini ไม่ได้ส่งเอกสารเต็ม
  การใช้เอกสารเต็มจริงเป็นตัวเลือกสำหรับเวอร์ชันปรับปรุงภายหลัง
- vector index ไม่เก็บบริบทเสริม ผลที่พบเฉพาะทาง vector จึงอาจไม่มีบริบทนี้ตอนสร้างคำตอบ
- truncate_context ประเมิน tokens จากคำคั่นด้วยช่องว่าง ไม่ใช่ tokenizer จึงไม่แม่นกับภาษาไทย
- ID เป็น doc_0, doc_1 ฯลฯ ถ้าลดจำนวน Chunk แล้วนำเข้าซ้ำ ข้อมูลเก่าอาจค้าง
  ควรใช้ดัชนีใหม่หรือจัดการข้อมูลเดิมก่อนทดลองกับ corpus ที่เปลี่ยน
- การนำเข้าไม่เป็น transaction ข้ามสองดัชนี หากงานหยุดกลางทางควรนำเข้าชุดเดิมใหม่ให้ครบ
- ผลค้นหา Top-5 ไม่ได้ยืนยันว่ามีข้อมูลเพียงพอหรือตอบถูก ต้องประเมินกับชุดคำถามและเฉลย

## ไฟล์และวิธีตรวจ

- authenticRAG.py — นำเข้าและทดสอบถามสองคำถาม
- onlysearchAuthenticRAG.py — ค้นหาชุดคำถามและบันทึก JSON
- upstream/ — สำเนาต้นฉบับและคู่มือจาก GitHub
- corpus_input/ — เอกสารตัวอย่างจากต้นฉบับ
- changes_from_upstream.patch — diff โค้ดสองไฟล์เทียบต้นฉบับ
- adapt_upstream.py — สคริปต์สร้างโค้ดที่ปรับจากสำเนา upstream ซ้ำได้
- verify_baseline.py — ตรวจพฤติกรรมออฟไลน์โดยไม่เรียก API

```powershell
python -m compileall -q authenticRAG.py onlysearchAuthenticRAG.py
python verify_baseline.py
```

การตรวจออฟไลน์ไม่ยืนยันความเข้ากันได้ของแพ็กเกจที่ติดตั้งจริง, OpenSearch หรือ Gemini
requirements ใช้ช่วงเวอร์ชัน ยังไม่ใช่ lockfile ต้องทดสอบครบวงจรก่อนใช้ผลส่งงาน

อ้างอิง:
- https://github.com/aekanun2020/2025-authenticRAG
- https://ai.google.dev/gemini-api/docs/openai
