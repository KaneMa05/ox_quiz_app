@echo off
rem If LAUNCH_GUI.bat fails, this runs it via cmd call (also use if .bat opens in Notepad).
setlocal
cd /d "%~dp0"
call "%~dp0LAUNCH_GUI.bat"
endlocal
