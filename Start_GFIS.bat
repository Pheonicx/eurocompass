@echo off
title Germany Finance Intelligence System

cd /d "E:\Projects\Germany-Finance-Intelligence-System"

call .venv\Scripts\activate.bat

echo.
echo =====================================
echo      Germany Finance Intelligence
echo =====================================
echo.

streamlit run dashboard\app.py