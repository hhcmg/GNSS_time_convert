@echo off
setlocal

REM Reuse the isolated environment. PYBASE can select the seed Python on first use.
REM All project paths are resolved by build.py, so any working directory is valid.
if exist "%~dp0.venv\Scripts\python.exe" goto use_venv
if defined PYBASE goto use_pybase
where py >nul 2>&1
if not errorlevel 1 goto use_launcher

python "%~dp0scripts\build.py" %*
exit /b %errorlevel%

:use_venv
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\build.py" %*
exit /b %errorlevel%

:use_pybase
"%PYBASE%" "%~dp0scripts\build.py" %*
exit /b %errorlevel%

:use_launcher
py -3 "%~dp0scripts\build.py" %*
exit /b %errorlevel%
