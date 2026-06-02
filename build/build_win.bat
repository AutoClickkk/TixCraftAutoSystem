@echo off
REM Build TixCraft.exe and zip it into dist/.
REM Usage:  build\build_win.bat
setlocal enabledelayedexpansion

set ROOT=%~dp0..
pushd "%ROOT%"

if not exist .venv (
    py -3.10 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat

pip install --upgrade pip || exit /b 1
pip install -r requirements-dev.txt || exit /b 1

REM Download Chrome for Testing + chromedriver for Windows.
python build\fetch_chrome.py || exit /b 1

if exist build\work rmdir /s /q build\work
if exist dist\TixCraft rmdir /s /q dist\TixCraft

pyinstaller --noconfirm --clean --workpath build\work --distpath dist build\tixcraft.spec || exit /b 1

REM One-file mode: dist\準點搶.exe is fully self-contained (Chrome included).
pushd dist
if exist "準點搶.exe" (
    powershell -Command "Compress-Archive -Path '準點搶.exe' -DestinationPath '準點搶-win-x64.zip' -Force"
    echo Built: dist\準點搶.exe
    echo Zip:   dist\準點搶-win-x64.zip
)
popd
popd
endlocal
