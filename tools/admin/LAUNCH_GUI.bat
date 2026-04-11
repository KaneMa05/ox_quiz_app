@echo off
rem OX Quiz admin launcher (pip + quiz_image_gui.py). NOT requirements-ocr.txt.
rem If Notepad opens .bat on double-click, use RUN_LAUNCH_GUI.cmd or fix .bat association.
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "OX_QUIZ_ADMIN_TOOLS=1"
set "REQ=%~dp0requirements-ocr.txt"
set "GUISCRIPT=%~dp0quiz_image_gui.py"

if not exist "%REQ%" (
  echo ERROR: requirements not found:
  echo   "%REQ%"
  pause
  exit /b 1
)

echo.
echo [1/2] pip install pytesseract Pillow ...
echo   file: "%REQ%"
echo.

set "PIP_OK=0"

call py -3 -m pip install -r "%REQ%"
if not errorlevel 1 set "PIP_OK=1"

if "%PIP_OK%"=="0" (
  echo py -3 failed, trying: python -m pip ...
  call python -m pip install -r "%REQ%"
  if not errorlevel 1 set "PIP_OK=1"
)

if "%PIP_OK%"=="0" (
  echo python failed, trying: py -3 --user ...
  call py -3 -m pip install --user -r "%REQ%"
  if not errorlevel 1 set "PIP_OK=1"
)

if "%PIP_OK%"=="0" (
  echo python3 -m pip ...
  call python3 -m pip install -r "%REQ%"
  if not errorlevel 1 set "PIP_OK=1"
)

if "%PIP_OK%"=="0" (
  echo.
  echo WARNING: pip install failed. GUI may still open if packages exist.
  echo Run by hand from this folder ^(ox-quiz-app^):
  echo   py -3 -m pip install -r "tools\admin\requirements-ocr.txt"
  echo   or:  python -m pip install -r "tools\admin\requirements-ocr.txt"
  echo.
)

set "REQV=%~dp0requirements-vision.txt"
if exist "%REQV%" (
  echo.
  echo [Vision] pip install openai pymupdf ...
  call py -3 -m pip install -r "%REQV%"
  if errorlevel 1 call python -m pip install -r "%REQV%"
  echo.
)

echo.
echo [2/2] Starting GUI ...
call py -3 "%GUISCRIPT%"
if not errorlevel 1 goto :done

call python "%GUISCRIPT%"
if not errorlevel 1 goto :done

call python3 "%GUISCRIPT%"
if not errorlevel 1 goto :done

echo.
echo Could not start GUI. Install Python 3 and ensure py or python is in PATH.
pause
exit /b 1

:done
endlocal
exit /b 0
