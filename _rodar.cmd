@echo off
rem Roda o Monitor de Fundos CVM e manda o resultado para o n8n.
cd /d "%~dp0"
python executar.py %*
echo.
echo Codigo de saida: %errorlevel%  (0 ok, 1 barrado pela qualidade, 2 erro)
pause
