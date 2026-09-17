@echo off
setlocal enabledelayedexpansion
REM ===================================================================
REM  Install the cr-estimate skill into the DCP AI harness.
REM
REM  Usage:
REM    install-cr-estimate.bat                     auto-detect the harness
REM    install-cr-estimate.bat <harnessRoot>       point it explicitly
REM    install-cr-estimate.bat <harnessRoot> 41000 ...and smoke-test a batch
REM
REM  Double-clicking from Explorer works too.
REM ===================================================================

set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"
set "BUNDLE=%REPO_ROOT%\harness\bundle"
set "FAILED="

echo.
echo === Installing cr-estimate ===
echo.

REM ---------------------------------------------------------------- bundle
echo ==^> Checking the bundle
if not exist "%BUNDLE%\skills\cr-estimate\SKILL.md" (
    echo     ERROR: no bundle at "%BUNDLE%"
    echo     You are probably on the wrong branch. Run this, then try again:
    echo         git checkout claude/cr-generation-utility-s8sfrz
    goto :fail
)
echo     OK   %BUNDLE%

REM ------------------------------------------------------- harness location
echo.
echo ==^> Locating the harness
set "HARNESS="
if not "%~1"=="" (
    for %%I in ("%~1") do set "HARNESS=%%~fI"
) else (
    REM The clone usually sits inside the harness workspace, so try the parent
    REM folder first, then its parent.
    for %%I in ("%REPO_ROOT%\..") do call :try_harness "%%~fI"
    if not defined HARNESS for %%I in ("%REPO_ROOT%\..\..") do call :try_harness "%%~fI"
)

if not defined HARNESS (
    echo     ERROR: could not find a harness near "%REPO_ROOT%".
    echo     Pass it explicitly, for example:
    echo         install-cr-estimate.bat "C:\Microservices\Workspace\aiv2"
    goto :fail
)
call :check_harness "%HARNESS%"
if defined FAILED (
    echo     ERROR: "%HARNESS%" has no .github\skills, .github\validators and .github\workspace.
    echo     Pass the folder that contains the harness .github directory.
    goto :fail
)
echo     OK   %HARNESS%

REM ------------------------------------------------------------- copy files
echo.
echo ==^> Installing files
if exist "%HARNESS%\.github\skills\cr-estimate" (
    echo     !    replacing the existing skill
    rmdir /s /q "%HARNESS%\.github\skills\cr-estimate"
)
xcopy "%BUNDLE%\skills\cr-estimate" "%HARNESS%\.github\skills\cr-estimate\" /e /i /q /y >nul
if errorlevel 1 goto :fail
echo     OK   .github\skills\cr-estimate

copy /y "%BUNDLE%\validators\cr_complete.py" "%HARNESS%\.github\validators\" >nul
if errorlevel 1 goto :fail
echo     OK   .github\validators\cr_complete.py

REM ----------------------------------------------------------------- python
echo.
echo ==^> Checking python
set "PY="
call :try_python python
if not defined PY call :try_python py
if not defined PY call :try_python python3

if not defined PY (
    echo     !    no usable python on PATH.
    echo          Install Python 3.10+ from python.org ^(not the Microsoft Store^),
    echo          then run:  pip install openpyxl
    goto :done
)
echo     OK   using "%PY%"

"%PY%" -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo     !    openpyxl missing, installing
    "%PY%" -m pip install --quiet openpyxl
    if errorlevel 1 (
        echo     ERROR: could not install openpyxl. Run:  %PY% -m pip install openpyxl
        goto :fail
    )
)
echo     OK   openpyxl available

REM ------------------------------------------------------------ smoke test
if "%~2"=="" goto :done
echo.
echo ==^> Smoke test on batch %~2 ^(dry run, writes nothing^)
pushd "%HARNESS%"
"%PY%" ".github\skills\cr-estimate\scripts\cr_estimate.py" ".github\workspace\%~2" --dry-run
popd

:done
echo.
echo === Installed ===
echo.
echo Nothing has been generated yet - the smoke test above is a dry run.
echo.
echo To actually WRITE the CR workbook:
echo     cd /d "%HARNESS%"
if defined PY (
    echo     %PY% .github\skills\cr-estimate\scripts\cr_estimate.py .github\workspace\^<batch-id^>
) else (
    echo     python .github\skills\cr-estimate\scripts\cr_estimate.py .github\workspace\^<batch-id^>
)
echo.
echo That creates three files in .github\workspace\^<batch-id^>\02-design\cr\
echo     ^<batch^>-CR-Estimation.xlsx   ^<- the deliverable, open it in Excel
echo     cr-spec.json                 ^<- fix wrong numbers here, then re-run
echo     cr-evidence.md               ^<- why each number is what it is
echo.
echo If rows look flat at 2 MD, diagnose with:
echo     python .github\skills\cr-estimate\scripts\cr_estimate.py doctor .github\workspace\^<batch-id^>
echo.
echo Then make the three edits in harness\INSTALL.md section 3.
echo.
if not defined CI pause
exit /b 0

:fail
echo.
echo === FAILED ===
echo.
if not defined CI pause
exit /b 1

REM ------------------------------------------------------------- functions
:try_harness
call :check_harness %1
if not defined FAILED set "HARNESS=%~1"
set "FAILED="
exit /b 0

:check_harness
set "FAILED="
if not exist "%~1\.github\skills" set "FAILED=1"
if not exist "%~1\.github\validators" set "FAILED=1"
if not exist "%~1\.github\workspace" set "FAILED=1"
exit /b 0

:try_python
REM Reject the Microsoft Store stub, which is a 0-byte shim that opens the Store.
for /f "delims=" %%P in ('where %1 2^>nul') do (
    echo %%P | find /i "WindowsApps" >nul
    if errorlevel 1 (
        "%%P" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if not errorlevel 1 (
            set "PY=%%P"
            exit /b 0
        )
    )
)
exit /b 0
