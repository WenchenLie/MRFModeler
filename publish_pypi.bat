@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
set "PUBLISH_DIR=.publish-dist"

if not exist "%PYTHON%" (
    echo ERROR: Python virtual environment was not found at %PYTHON%.
    goto :failed
)

echo [1/5] Running tests...
"%PYTHON%" -m pytest -q
if errorlevel 1 goto :failed

echo [2/5] Installing or updating publishing tools...
where uv >nul 2>nul
if errorlevel 1 (
    echo ERROR: uv was not found on PATH.
    goto :failed
)
uv pip install --python "%PYTHON%" --upgrade build twine
if errorlevel 1 goto :failed

echo [3/5] Building distributions...
if exist "%PUBLISH_DIR%" rmdir /s /q "%PUBLISH_DIR%"
"%PYTHON%" -m build --outdir "%PUBLISH_DIR%"
if errorlevel 1 goto :failed

echo [4/5] Checking distributions...
"%PYTHON%" -m twine check "%PUBLISH_DIR%\*"
if errorlevel 1 goto :failed

echo [5/5] Uploading to PyPI...
"%PYTHON%" -m twine upload --disable-progress-bar --skip-existing --repository pypi "%PUBLISH_DIR%\*"
if errorlevel 1 goto :failed

echo.
echo SUCCESS: The package was uploaded, or the same files already exist on PyPI.
pause
exit /b 0

:failed
echo.
echo ERROR: Publishing failed. Review the messages above.
pause
exit /b 1
