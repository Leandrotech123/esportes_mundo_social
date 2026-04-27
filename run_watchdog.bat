@echo off
:loop
python run.py
echo Sistema caiu — reiniciando em 5 segundos...
timeout /t 5
goto loop
