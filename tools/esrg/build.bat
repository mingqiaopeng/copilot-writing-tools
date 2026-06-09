@echo off
REM esrg PyInstaller build wrapper
REM Usage: build.bat        → onefile .exe
REM        build.bat --dir  → onedir (faster startup, easier debug)

cd /d "%~dp0"
python build.py %*
pause
