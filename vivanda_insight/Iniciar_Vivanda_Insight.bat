@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No se encontro el entorno virtual de Vivanda Insight.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py
pause