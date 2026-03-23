@echo off
title YouTube Music Batch Downloader Pro - Installer
color 0A

echo ============================================================
echo   YouTube Music Batch Downloader Pro - Dependency Installer
echo ============================================================
echo.
echo This script will install the required libraries:
echo   - yt-dlp
echo   - ffmpeg
echo.
echo ------------------------------------------------------------

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python detected.
echo.

:: Check if pip is available
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not available. Please reinstall Python with pip included.
    echo.
    pause
    exit /b 1
)

echo [OK] pip detected.
echo.

:: Install yt-dlp
echo [1/2] Installing yt-dlp...
pip install -U yt-dlp
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install yt-dlp. Please check your internet connection.
    echo.
    pause
    exit /b 1
)
echo [OK] yt-dlp installed successfully.
echo.

:: Install ffmpeg via winget (Windows built-in package manager)
echo [2/2] Installing ffmpeg...

:: Try winget first
winget --version >nul 2>&1
if %errorlevel% equ 0 (
    echo     Using winget to install ffmpeg...
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    if %errorlevel% equ 0 (
        echo [OK] ffmpeg installed via winget.
        goto :done
    ) else (
        echo     winget install failed, trying pip fallback...
    )
)

:: Fallback: install ffmpeg-python wrapper via pip (for environments without winget)
echo     Using pip to install ffmpeg-python (Python wrapper)...
pip install ffmpeg-python
if %errorlevel% neq 0 (
    echo [WARNING] Could not install ffmpeg automatically.
    echo.
    echo Please install ffmpeg manually:
    echo   1. Download from https://ffmpeg.org/download.html
    echo   2. Extract the zip file
    echo   3. Add the "bin" folder to your system PATH
    echo.
) else (
    echo [OK] ffmpeg-python installed successfully.
)

:done
echo.
echo ============================================================
echo   Installation Complete!
echo   You can now run "YT Music to mp3.pyw"
echo ============================================================
echo.
pause
