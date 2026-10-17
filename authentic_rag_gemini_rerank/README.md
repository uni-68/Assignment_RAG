# แบบที่ 2: AuthenticRAG + Gemini + Reranking

ต่อยอดจากแบบที่ 1 ใน `../authentic_rag_gemini_once/` เพิ่ม Reranking หลัง RRF
**ถามได้ 1 ครั้งต่อการเปิดโปรแกรม เมื่อตอบแล้วจะจบ หากต้องการถามเพิ่มให้เปิดใหม่**
ไม่มีรหัสผ่าน ไม่มีชุดคำถามอัตโนมัติ และไม่เปลี่ยน LLM ที่สร้างคำตอบ

## Flow

```text
แสดงหัวข้อเอกสาร → รอพิมพ์คำถาม
→ BM25 ไม่เกิน 20 + Vector Search ไม่เกิน 20
→ RRF รวมอันดับและตัดข้อมูลซ้ำตาม ID → เก็บไม่เกิน 20 Chunk
→ BAAI/bge-reranker-v2-m3 ประเมินคำถามคู่กับแต่ละ Chunk
→ เลือก 5 Chunk → Gemini สร้างคำตอบ → แสดงและบันทึกผล → จบโปรแกรม
```

ยังใช้ Markdown parser, contextual enrichment, BAAI/bge-m3, BM25, สูตร RRF และ
prompt/temperature/token limit ของ Gemini แบบเดิมทั้งหมด
แบบที่ 1 ค้นวิธีละ 10 และเลือก Top-5 จาก RRF ส่วนแบบที่ 2 ค้นวิธีละ 20 แล้ว rerank ไม่เกิน 20
จึงเปลี่ยนทั้งจำนวนผู้สมัครและเพิ่ม Reranker ต้องพิจารณาทั้งสองส่วนเมื่อเปรียบเทียบผล

## 1. เปิดโฟลเดอร์

เปิด Docker Desktop และ PowerShell:

```powershell
cd "C:\Users\User\Desktop\4\Master D\NLP\Ass2\authentic_rag_gemini_rerank"
```

## 2. ใช้ environment จากแบบที่ 1

ถ้าแบบที่ 1 ติดตั้งแพ็กเกจครบแล้ว ใช้ Python ตัวเดิมได้ ไม่ต้องสร้าง .venv ใหม่
Reranker ใช้ CrossEncoder ใน sentence-transformers ที่มีใน requirements อยู่แล้ว

```powershell
..\authentic_rag_gemini_once\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

คำสั่งจะติดตั้งเฉพาะส่วนที่ยังขาด หากไม่ต้องการใช้ environment ร่วม ให้สร้างของโฟลเดอร์นี้:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

คำสั่ง Python ด้านล่างใช้ environment แบบที่ 1 หากสร้างแยกให้ใช้ `.\.venv\Scripts\python.exe` แทน

## 3. ตั้งค่า Gemini

ถ้าโฟลเดอร์นี้ไม่มี `.env` โปรแกรมจะอ่าน `.env` ของแบบที่ 1 อัตโนมัติ
จึงใช้ API key, Gemini model และ OpenSearch เดียวกันโดยไม่คัดลอกคีย์
หากมี `.env` ในโฟลเดอร์นี้ จะเลือกไฟล์นี้แทน ต้องใส่ค่าที่จำเป็นให้ครบ
Environment variables ที่ตั้งใน Terminal มีลำดับสูงกว่าไฟล์ `.env` ตาม python-dotenv

ถ้าต้องการตั้งค่าแยก และยังไม่มี `.env`:

```powershell
Copy-Item .env.example .env
notepad .env
```

```dotenv
GEMINI_API_KEY=ใส่คีย์จริง
GEMINI_MODEL=ใช้รุ่นเดียวกับแบบที่หนึ่ง
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

อย่าคัดลอกทับ `.env` ที่ตั้งค่าแล้ว ชื่อโมเดล Gemini ต้องเป็นรุ่นที่บัญชีเรียกได้

## 4. เปิด OpenSearch เดิม

ถ้าเปิดจากแบบที่ 1 อยู่แล้ว ไม่ต้องเปิด Container ซ้ำ
หากยังไม่ได้เปิด service ของแบบที่ 1 ใช้:

```powershell
docker compose -f ..\authentic_rag_gemini_once\compose.yaml --env-file ..\authentic_rag_gemini_once\.env up -d
Invoke-RestMethod http://localhost:9200
```

รอจนแสดงข้อมูล OpenSearch ก่อนถาม (ถ้าใช้พอร์ตอื่นให้เปลี่ยน URL)
ไฟล์ compose.yaml ในโฟลเดอร์นี้เตรียมไว้กรณีใช้แยกเท่านั้น จะมี volume คนละชุดตามชื่อ Compose project
อย่าเปิดทั้งสองชุดที่พอร์ตเดียวกัน หากเปิดชุดใหม่จะไม่มีข้อมูลของชุดเดิมและต้องนำเข้าใหม่

## 5. นำเข้าเอกสารเฉพาะกรณียังไม่มีข้อมูล

**ถ้าแบบที่ 1 นำเข้าแล้ว ให้ข้ามขั้นนี้** ทั้งสองเวอร์ชันใช้ดัชนี
`once-gemini-vector-index` และ `once-gemini-bm25-index` ชุดเดียวกัน

```powershell
..\authentic_rag_gemini_once\.venv\Scripts\python.exe authenticRAG.py
```

หรือเปิด `ingest.cmd` นำเข้าเอกสารอย่างเดียว ไม่ถามอัตโนมัติ
นำเข้าใหม่ใช้โควตา Gemini สำหรับสร้างบริบท จึงไม่ต้องทำซ้ำเพื่อเพิ่ม Reranking
หากเปลี่ยน corpus/การแบ่ง Chunk ต้องจัดการดัชนีและนำเข้าใหม่เพื่อให้ข้อมูลตรงกัน

## 6. ถามหนึ่งครั้ง

```powershell
..\authentic_rag_gemini_once\.venv\Scripts\python.exe onlysearchAuthenticRAG.py
```

หรือดับเบิลคลิก `ask.cmd` ซึ่งเลือก .venv ของโฟลเดอร์นี้ก่อน แล้วจึงใช้ของแบบที่ 1
โปรแกรมแสดงหัวข้อเอกสาร รอคำถาม และค่อยโหลดโมเดล/เชื่อมบริการหลังพิมพ์คำถาม
Reranker ดาวน์โหลดครั้งแรกและทำงานบนเครื่อง ไม่ได้เรียก Gemini เพิ่มเพื่อจัดอันดับ
ต้องมีอินเทอร์เน็ตครั้งแรก พื้นที่และ RAM สำหรับทั้ง BGE-M3 และ Reranker การใช้ CPU อาจช้า

พิมพ์คำถามแล้วกด Enter รอคำตอบ เมื่อตอบแล้วโปรแกรมจบ
**หากต้องการถามอีก ให้เปิด ask.cmd ใหม่ หรือรันคำสั่งถามอีกครั้ง**
Enter ว่างหรือ Ctrl+C จะยกเลิก ถ้า Reranker ล้มเหลว โปรแกรมหยุด ไม่แอบใช้ผลแบบ Baseline
หน้าต่าง .cmd ค้างเพื่อให้อ่านผล การกดปุ่มที่ pause คือปิดหน้าต่าง ไม่ใช่ถามต่อ

## ผลลัพธ์และข้อจำกัด

`authentic_rag_search_results.json` เก็บผลล่าสุดในโฟลเดอร์นี้ แยกจากแบบที่ 1 และเขียนทับเมื่อสำเร็จครั้งถัดไป
มีคำถาม คำตอบ Top-5 และ `retrieval.candidates` ที่เก็บอันดับ RRF กับอันดับ Reranker ของผู้สมัคร
ค่า `results[].score` ของแบบที่ 2 คือคะแนน Reranker ส่วน `rrf_score` เก็บแยก คะแนนไม่ใช่ความน่าจะเป็น
`rerank_seconds` รวมเวลาโหลดโมเดลถ้ามี ไม่ใช่เวลาตอบทั้งหมด

Reranker จำกัด input คู่คำถาม–ข้อความไว้ 512 tokens และอาจตัดส่วนท้ายของ Chunk ยาว
หากหลักฐานอยู่นอกส่วนที่โมเดลอ่าน อันดับอาจแย่ลง ต้องประเมินผลจริง
ข้อจำกัดเดิม เช่น context จาก Chunk, การประมาณ tokens ภาษาไทย และ ID เมื่อ re-ingest ยังเหมือนแบบที่ 1
ไม่มีการรับประกันว่าทุกคำถามดีขึ้น และยังไม่ได้ทดสอบครบวงจรกับโมเดลจริงในรอบสร้างไฟล์นี้

## ไฟล์หลัก

| ไฟล์ | หน้าที่ |
| --- | --- |
| onlysearchAuthenticRAG.py | เพิ่ม Reranking และข้อมูลอันดับก่อน–หลัง |
| baseline_search.py | ส่วนค้นหาและสร้างคำตอบที่คงจากแบบที่ 1 |
| app.py | รับคำถามครั้งเดียว อ่านค่า .env และแสดงผล |
| authenticRAG.py | นำเข้าแบบเดิม กรณียังไม่มีข้อมูล |
| corpus_input/ | สำเนา Markdown เดิม 4 ไฟล์ |
| test_rerank.py | ตรวจ Flow และ Reranking ด้วยข้อมูลจำลอง |
| ../AnsA(3).md | คำอธิบายตอบโจทย์ข้อ (3) |

## ตรวจออฟไลน์

```powershell
python -m compileall -q app.py authenticRAG.py baseline_search.py onlysearchAuthenticRAG.py
python -m unittest -v test_rerank.py
```

ไม่ต้องเปิด Docker ใส่ API key หรือดาวน์โหลดโมเดล การตรวจนี้ไม่ยืนยันคุณภาพผลค้นหาจริง
