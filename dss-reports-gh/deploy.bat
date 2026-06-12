@echo off
REM ============================================================
REM DSS Reports - Deploy to IIS
REM ============================================================
REM Usage:
REM   deploy.bat                     Deploy dynamic HTML reports (recommended)
REM   deploy.bat --static            Generate Python reports first, then deploy
REM   deploy.bat "\\share\new.csv"   Copy new CSV first, then deploy dynamic
REM
REM IIS target: Update IIS_TARGET below to match your server path
REM ============================================================

SET PROJECT=C:\DSS\DSSAI\dss-reports
SET PYTHON=%PROJECT%\.venv\Scripts\python.exe
SET IIS_TARGET=C:\inetpub\wwwroot\dss-reports

echo.
echo ============================================================
echo   DSS Reports - Deploy to IIS
echo ============================================================
echo.

REM If a CSV path was passed as argument (not --static), copy it into data/
IF NOT "%~1"=="" IF NOT "%~1"=="--static" (
    echo Copying new data file: %~1
    copy /Y "%~1" "%PROJECT%\data\"
    echo.
)

IF "%~1"=="--static" (
    echo Mode: Static (Python-generated HTML^)
    echo.
    echo Generating reports...
    cd /d "%PROJECT%"
    "%PYTHON%" run.py --all
    IF ERRORLEVEL 1 (
        echo.
        echo ERROR: Report generation failed!
        pause
        exit /b 1
    )
    echo.
    echo Deploying to IIS: %IIS_TARGET%
    if not exist "%IIS_TARGET%" mkdir "%IIS_TARGET%"
    xcopy /Y "%PROJECT%\output\*.html" "%IIS_TARGET%\"
) ELSE (
    echo Mode: Dynamic (HTML fetches data at runtime^)
    echo.

    REM Prepare data files
    echo Preparing data files...
    cd /d "%PROJECT%"
    "%PYTHON%" -c "from reports.generate_entity_json import generate; generate()"

    REM Deploy HTML + data
    echo.
    echo Deploying to IIS: %IIS_TARGET%
    if not exist "%IIS_TARGET%" mkdir "%IIS_TARGET%"
    if not exist "%IIS_TARGET%\data" mkdir "%IIS_TARGET%\data"

    xcopy /Y "%PROJECT%\static\*.html" "%IIS_TARGET%\"
    xcopy /Y "%PROJECT%\static\data\*.*" "%IIS_TARGET%\data\"

    REM Copy source data CSVs into IIS data dir
    if exist "%PROJECT%\data\Advisors_by_Channel.csv" (
        copy /Y "%PROJECT%\data\Advisors_by_Channel.csv" "%IIS_TARGET%\data\"
    )
    if exist "%PROJECT%\data\channel_mandatoryrequirements_finalprod.csv" (
        copy /Y "%PROJECT%\data\channel_mandatoryrequirements_finalprod.csv" "%IIS_TARGET%\data\"
    )
)

echo.
echo ============================================================
echo   DONE - Reports deployed to %IIS_TARGET%
echo ============================================================
echo.
pause
