@echo off
setlocal
:: ============================================================
:: Z-CMDB Windows Build Bundle
:: Run on dev machine (has python 3.12 win_amd64 + pnpm)
:: ============================================================
cd /d "%~dp0\..\.."
set "PYVER=3.12.8"
set "OUT=dist\Z-CMDB"

echo [1/5] Building frontend ...
pushd frontend
call pnpm install --frozen-lockfile || (echo [ERROR] pnpm install failed & exit /b 1)
call pnpm build || (echo [ERROR] pnpm build failed & exit /b 1)
popd

echo [2/5] Assembling package ...
if exist dist rmdir /s /q dist
mkdir "%OUT%"
xcopy backend\app "%OUT%\app" /e /i /q
xcopy backend\alembic "%OUT%\alembic" /e /i /q
copy backend\alembic.ini "%OUT%\" >nul
xcopy frontend\dist "%OUT%\static" /e /i /q
mkdir "%OUT%\data" 2>nul

echo [3/5] Downloading embedded Python %PYVER% ...
curl -L -o embed.zip "https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip" || (echo [ERROR] download failed & exit /b 1)
powershell -Command "Expand-Archive -Path embed.zip -DestinationPath '%OUT%\python' -Force"
del embed.zip
copy deploy\windows\python312._pth "%OUT%\python\python312._pth" >nul

echo [4/5] Pre-installing dependencies (embedded Python %PYVER%) ...
:: Bootstrap pip into embedded Python via get-pip.py
curl -sL https://bootstrap.pypa.io/get-pip.py -o "%OUT%\python\get-pip.py"
"%OUT%\python\python.exe" "%OUT%\python\get-pip.py" --no-warn-script-location >nul 2>&1
del "%OUT%\python\get-pip.py"
:: Install setuptools (needed for sdist packages like python-libnmap)
"%OUT%\python\python.exe" -m pip install --target "%OUT%\site-packages" setuptools wheel --no-warn-script-location >nul 2>&1
:: Install project dependencies (embedded pip ensures cp312 wheels)
"%OUT%\python\python.exe" -m pip install --target "%OUT%\site-packages" --prefer-binary -r backend\requirements.txt || (echo [ERROR] pip install failed & exit /b 1)
:: Clean up pip's own packages (not needed at runtime)
if exist "%OUT%\python\Lib" rmdir /s /q "%OUT%\python\Lib"

echo [5/5] Copying launcher ...
copy deploy\windows\start.bat "%OUT%\" >nul

echo.
echo Build complete: %OUT%
echo To test: cd %OUT% ^& start.bat
