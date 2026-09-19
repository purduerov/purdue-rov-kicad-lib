@echo off
chcp 65001 >nul 2>&1
title Purdue ROV - KiCad Central Library Manager
setlocal enabledelayedexpansion

REM 1. Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=py -3"
    ) else (
        echo ====================================================================
        echo [ERROR] Python was not found on your system!
        echo Please install Python 3 with tkinter enabled from python.org
        echo or from the Microsoft Store.
        echo ====================================================================
        pause
        exit /b 1
    )
) else (
    set "PY_CMD=python"
)

REM 2. Launch Library Manager (dependency_check will auto-prompt for any missing libraries)
%PY_CMD% "%~dp0scripts\library_manager_gui.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Library Manager exited with an error.
    pause
)
