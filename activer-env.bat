@echo off
REM Active le venv TimaLove et ouvre un shell dans timalove/
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
  echo ERREUR : venv introuvable. Cree-le avec : python -m venv venv
  exit /b 1
)
call "%~dp0venv\Scripts\activate.bat"
cd /d "%~dp0timalove"
echo.
echo Environnement TimaLove active.
echo Dossier : %CD%
echo.
cmd /k
