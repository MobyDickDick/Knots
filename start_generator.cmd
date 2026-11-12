@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
python -m knots_grid.studio --open %*
if errorlevel 1 pause
endlocal
