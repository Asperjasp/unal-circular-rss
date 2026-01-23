@echo off
REM ==============================================================================
REM Health Scraper - Quick Start Script (Windows)
REM ==============================================================================
REM This script sets up and runs the Health Scraper locally.
REM 
REM Prerequisites:
REM   - Conda installed (Miniconda or Anaconda)
REM
REM Usage:
REM   Double-click this file or run from command prompt
REM ==============================================================================

echo.
echo ========================================
echo   Health Institutions Scraper
echo ========================================
echo.

REM Check if conda is installed
where conda >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Conda is not installed. Please install Miniconda or Anaconda first.
    echo Visit: https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

REM Check if environment exists
conda env list | findstr /C:"health-scraper" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Creating conda environment...
    conda env create -f environment.yml
)

REM Activate environment and run
echo Activating environment...
call conda activate health-scraper

echo.
echo =================================================
echo   Frontend: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Health:   http://localhost:8000/health
echo =================================================
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py

pause
