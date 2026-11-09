@echo off
cd /d "%~dp0"
python rattys4skin.py
if errorlevel 1 pause
