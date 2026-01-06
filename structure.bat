@echo off
echo ====================================
echo Project Structure Analysis
echo ====================================
echo.

echo [1] Directory Tree:
echo -------------------
tree /f /a | more

echo.
echo [2] File Counts by Type:
echo -------------------------
dir /s *.py 2>nul | find "File(s)"
dir /s *.html 2>nul | find "File(s)"
dir /s *.css 2>nul | find "File(s)"
dir /s *.js 2>nul | find "File(s)"

echo.
echo [3] Largest Files:
echo ------------------
for /f "tokens=*" %%i in ('dir /s /os /b') do echo %%~zi bytes - %%~nxi

pause