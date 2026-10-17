# AuthenticRAG + Gemini — ถามหนึ่งครั้งต่อการเปิดโปรแกรม

## ขั้นตอนการรันใช้งานบน Windows (PowerShell)

**ระบบรับคำถามเพียง 1 ครั้งต่อการเปิดโปรแกรม เมื่อแสดงคำตอบแล้วจะจบการทำงาน ถ้าต้องการถามเพิ่ม ต้องเปิดโปรแกรมใหม่หรือรันคำสั่งถาม–ตอบอีกครั้ง**

### 1. เปิดโฟลเดอร์โปรเจกต์

ติดตั้ง Python 3.11 และ Docker Desktop ที่ใช้ Linux containers ก่อน จากนั้นเปิด Docker Desktop
และรอให้ Docker พร้อมทำงาน เปิด PowerShell แล้วรัน:

```powershell
cd "C:\Users\User\Desktop\4\Master D\NLP\Ass2\authentic_rag_gemini_once"
```

คำสั่งทุกขั้นตอนด้านล่างให้รันจากโฟลเดอร์นี้ หากย้ายโปรเจกต์ ให้เปลี่ยน path ในคำสั่ง `cd`

### 2. สร้าง environment และติดตั้งแพ็กเกจ (ครั้งแรก)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

ใช้ Python ใน `.venv` โดยตรงได้ ไม่จำเป็นต้อง activate environment

### 3. ตั้งค่า Gemini (ครั้งแรก)

ถ้ายังไม่มี `.env` ให้คัดลอกจากไฟล์ตัวอย่าง แล้วเปิดแก้ไข:

```powershell
Copy-Item .env.example .env
notepad .env
```

ถ้ามี `.env` ที่ตั้งค่าแล้ว ให้ข้าม `Copy-Item` เพื่อไม่เขียนทับค่าของเดิม
ใส่คีย์และชื่อโมเดลจริง แล้วบันทึกไฟล์:

```dotenv
GEMINI_API_KEY=ใส่คีย์จริงของคุณ
GEMINI_MODEL=ใส่ชื่อโมเดลที่บัญชีเรียกได้
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
```

ตรวจชื่อโมเดลจาก [เอกสาร Gemini](https://ai.google.dev/gemini-api/docs/models)
อย่าอัปโหลด `.env` ที่มี API key ขึ้น GitHub

### 4. เปิด OpenSearch

```powershell
docker compose up -d
```

รอให้ service พร้อม แล้วตรวจการเชื่อมต่อ:

```powershell
Invoke-RestMethod http://localhost:9200
```

ถ้าแสดงข้อมูลชื่อและเวอร์ชันของ OpenSearch แสดงว่าเชื่อมต่อได้
หากยังเชื่อมต่อไม่ได้ ให้ตรวจ log แล้วลองตรวจการเชื่อมต่ออีกครั้ง:

```powershell
docker compose logs opensearch
```

ถ้ามี OpenSearch เดิมที่พอร์ต 9200 อยู่แล้ว สามารถใช้ service เดิมได้โดยข้าม `docker compose up -d`
หรือเปลี่ยน `OPENSEARCH_PORT` ใน `.env` เพื่อเปิด service แยก เมื่อเปลี่ยนพอร์ตให้เปลี่ยน URL ตรวจการเชื่อมต่อด้วย
Compose ให้บริการเฉพาะ 127.0.0.1 โดยไม่มี authentication สำหรับทดลองบนเครื่อง

### 5. นำเข้าเอกสาร (ครั้งแรก หรือเมื่อแก้เอกสาร)

```powershell
.\.venv\Scripts\python.exe authenticRAG.py
```

หรือดับเบิลคลิก `ingest.cmd` รอจนมีข้อความ **“นำเข้าเรียบร้อย”** ก่อนเริ่มถาม
ขั้นนี้อ่าน Markdown → แบ่ง Chunk → Gemini สร้างบริบท → BGE-M3 สร้าง Embedding → เก็บใน OpenSearch
ไม่มีการถามคำถามทดสอบอัตโนมัติหลังนำเข้า

BGE-M3 จะโหลดจากอินเทอร์เน็ตครั้งแรกและสร้างเวกเตอร์บนเครื่อง จึงอาจใช้เวลานาน
การสร้างบริบทเรียก Gemini หนึ่งครั้งต่อ Chunk และใช้โควตา API
เมื่อใช้เอกสารเดิมและข้อมูลใน OpenSearch ยังอยู่ ไม่ต้องนำเข้าใหม่ทุกครั้ง

### 6. เปิดโปรแกรมเพื่อถาม 1 คำถาม

```powershell
.\.venv\Scripts\python.exe onlysearchAuthenticRAG.py
```

หรือดับเบิลคลิก `ask.cmd` โปรแกรมจะแสดงหัวข้อเอกสาร แล้วรอที่:

```text
อยากทราบอะไรเกี่ยวกับหัวข้อในเอกสาร?
>
```

พิมพ์คำถาม เช่น `ในเอกสารอธิบายสาเหตุของโรคหัดเยอรมันไว้อย่างไร` แล้วกด Enter
จากนั้นโปรแกรมเริ่มค้นข้อมูลด้วย BM25 + Vector Search รวมอันดับด้วย RRF เลือก Top-5
แล้วส่งข้อมูลให้ Gemini สร้างคำตอบ

**เมื่อตอบแล้ว โปรแกรมจะจบ ไม่มีการรับคำถามถัดไปในรอบเดิม**
ถ้าต้องการถามเพิ่ม ให้รันคำสั่งในขั้นที่ 6 อีกครั้ง หรือเปิด `ask.cmd` ใหม่
ไม่ต้องทำขั้นติดตั้ง ตั้งค่า และนำเข้าซ้ำ หากยังใช้ข้อมูลเดิม

กด Enter โดยไม่พิมพ์คำถาม หรือกด Ctrl+C เพื่อจบโดยไม่เรียก Gemini
เมื่อเปิดผ่าน `ask.cmd` หน้าต่างจะค้างไว้ให้อ่านผลด้วย `pause`
การกดปุ่มที่ข้อความ `Press any key to continue . . .` เป็นการปิดหน้าต่าง ไม่ใช่การเริ่มคำถามใหม่

ผลล่าสุดพร้อม Chunk และคะแนนเก็บใน `authentic_rag_search_results.json`
ไฟล์นี้ถูกเขียนทับเมื่อถามสำเร็จครั้งถัดไป

### 7. การใช้งานครั้งถัดไป

เปิด Docker Desktop และ PowerShell ในโฟลเดอร์โปรเจกต์ หากใช้ service จาก Compose ชุดนี้ ให้รัน:

```powershell
docker compose up -d
.\.venv\Scripts\python.exe onlysearchAuthenticRAG.py
```

รอ OpenSearch พร้อมก่อนสั่งถาม–ตอบ ต้องเปิด OpenSearch ไว้ตลอดช่วงที่ใช้งาน
หากต้องการหยุด service ของ Compose ชุดนี้หลังใช้งาน:

```powershell
docker compose stop
```

คำสั่งนี้หยุด service โดยเก็บข้อมูลไว้สำหรับการเปิดครั้งถัดไป

## ไฟล์หลัก

| ไฟล์ | หน้าที่ |
| --- | --- |
| authenticRAG.py | นำเข้าเอกสารอย่างเดียว ไม่มีการถามทดสอบอัตโนมัติ |
| onlysearchAuthenticRAG.py | เปิดหน้ารับคำถาม ตอบหนึ่งครั้งแล้วจบ |
| app.py | จัดการ Flow รับคำถาม แสดงหัวข้อ ตรวจข้อมูล และบันทึกผล |
| ask.cmd | ดับเบิลคลิกเพื่อถามหนึ่งครั้งบน Windows |
| ingest.cmd | ดับเบิลคลิกเพื่อนำเข้าข้อมูลบน Windows |
| corpus_input/ | Markdown ตัวอย่าง 4 ไฟล์จาก GitHub อาจารย์ |
| .env.example | ตัวอย่างค่าตั้ง ไม่ได้ใส่คีย์จริง |
| compose.yaml | OpenSearch 2.19.1 บน Docker |
| requirements.txt | dependencies |
| test_once.py | ทดสอบ Flow ออฟไลน์ |

## ตรวจออฟไลน์

เปิด PowerShell แล้วรันตามนี้ หากอยู่ในโฟลเดอร์โปรเจกต์แล้ว ข้ามคำสั่ง `cd` ได้:

```powershell
cd "C:\Users\User\Desktop\4\Master D\NLP\Ass2\authentic_rag_gemini_once"
python -m compileall -q authenticRAG.py onlysearchAuthenticRAG.py app.py
python -m unittest -v test_once.py
```

`compileall` ตรวจไวยากรณ์ Python หากผ่านจะไม่มีข้อความแสดง
ส่วน `unittest` รันการทดสอบพฤติกรรม 7 ข้อ หากผ่านจะแสดง `Ran 7 tests` และ `OK`
ไม่ต้องเปิด Docker หรือตั้ง API key สำหรับการตรวจชุดนี้

ตรวจว่ารอคำถามก่อนเริ่มบริการ ตอบเพียงครั้งเดียว ไม่ถามซ้ำเมื่อ error และไม่ถามอัตโนมัติหลังนำเข้า
การตรวจนี้ใช้บริการจำลอง ไม่ได้เรียก Gemini จริงหรือยืนยันการทำงานของ OpenSearch จริง
