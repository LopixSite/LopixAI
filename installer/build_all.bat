@echo off
title LopixAI Setup Builder
cd /d "%~dp0\.."

echo =======================================================
echo     ✦ LopixAI Kurulum Paketi Uretici (Build All)
echo =======================================================
echo.

echo [1/2] LopixAI.exe derleniyor...
python packaging/build_exe.py
if %ERRORLEVEL% NEQ 0 (
    echo [-] LopixAI.exe derlenirken hata olustu!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] LopixAI-Setup.exe derleniyor...
python installer/build_installer.py
if %ERRORLEVEL% NEQ 0 (
    echo [-] LopixAI-Setup.exe derlenirken hata olustu!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo =======================================================
echo [✓] Tum kurulum dosyalari dist/ klasorunde hazir!
echo     - dist\LopixAI-Setup.exe
echo     - dist\LopixAI\LopixAI.exe
echo =======================================================
pause
