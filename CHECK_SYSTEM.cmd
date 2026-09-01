@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 CHECK_SYSTEM.py
  goto done
)

where python >nul 2>nul
if %errorlevel%==0 (
  python CHECK_SYSTEM.py
  goto done
)

echo 找不到 Python。請先安裝 Python 3.13 或更新版本，再重新執行本檔。

:done
echo.
pause
