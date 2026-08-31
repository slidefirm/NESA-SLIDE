@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "demos\html\demo-deck.html" (
  echo 找不到示範簡報。請先執行 CHECK_SYSTEM.cmd 確認環境，
  echo 或執行：python scripts\render_randomized_html_demo.py --output demos\html\demo-deck.html --theme brand-editorial
  echo.
  pause
  exit /b 1
)

start "" "%~dp0demos\html\demo-deck.html"
