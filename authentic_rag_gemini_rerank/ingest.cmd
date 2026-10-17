@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0authenticRAG.py"
) else if exist "%~dp0..\authentic_rag_gemini_once\.venv\Scripts\python.exe" (
    "%~dp0..\authentic_rag_gemini_once\.venv\Scripts\python.exe" "%~dp0authenticRAG.py"
) else (
    python "%~dp0authenticRAG.py"
)
pause
