@echo off
cd /d "C:\Users\Leandro\OneDrive\Área de Trabalho\esportes_mundo_social"
if not exist logs mkdir logs
start /min pythonw run.py > logs/output.log 2>&1
echo Sistema EsportesMundo iniciado em background!
echo Acesse: http://localhost:8000
pause
