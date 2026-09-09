@echo off
title Purdue ROV KiCad Part Importer Wizard
setlocal enabledelayedexpansion

:: 1. Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=py -3"
    ) else (
        echo ====================================================================
        echo [ERROR] Python was not found on your system!
        echo Please install Python 3 (with tkinter enabled) from python.org
        echo or from the Microsoft Store.
        echo ====================================================================
        pause
        exit /b 1
    )
) else (
    set "PY_CMD=python"
)

:: 2. Launch Part Importer (dependency_check will auto-prompt for any missing libraries)
%PY_CMD% "%~dp0scripts\part_importer_gui.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Part Importer Wizard exited with an error.
    pause
)
