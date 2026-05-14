@echo off
echo Iniciando InvestAI...
c:\Users\HP\.julia\conda\3\x86_64\python.exe -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
pause
