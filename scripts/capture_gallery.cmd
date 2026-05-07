@echo off
setlocal

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Dang tao moi moi truong ao .venv bang Python 3.6...
    py -3.6 -m venv .venv
    if errorlevel 1 goto :error
)

echo [INFO] Dang kiem tra phien ban Python trong .venv...
".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 6) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Moi truong .venv hien tai khong dung Python 3.6.
    echo [ERROR] Hay xoa .venv va tao lai bang lenh: py -3.6 -m venv .venv
    exit /b 1
)

echo [INFO] Dang kiem tra thu vien bat buoc...
".venv\Scripts\python.exe" -c "import cv2, yaml, numpy" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Thieu thu vien, dang cai dat tu requirements.txt...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade setuptools wheel
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

set "PERSON=%~1"
if "%PERSON%"=="" (
    set /p PERSON=Nhap ten nguoi can thu thap gallery: 
)

if "%PERSON%"=="" (
    echo [ERROR] Ten nguoi khong duoc rong.
    exit /b 1
)

set "COUNT=%~2"
if "%COUNT%"=="" set "COUNT=20"

echo [INFO] Dang thu thap anh gallery cho %PERSON% (count=%COUNT%)...
".venv\Scripts\python.exe" -m src.app.capture_gallery --person "%PERSON%" --count %COUNT%
if errorlevel 1 goto :error

goto :end

:error
echo [ERROR] Khong the thu thap anh gallery.
exit /b 1

:end
endlocal
