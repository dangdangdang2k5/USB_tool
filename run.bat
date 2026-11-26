@echo off
chcp 65001 >nul
"%~dp0python\python.exe" "%~dp0usb_ai.py"
if errorlevel 1 (
    echo.
    echo Chuong trinh dung voi ma loi %errorlevel%.
    pause
)
