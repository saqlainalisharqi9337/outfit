@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ========================================
echo   ADORE  -  Project context and diagrams
echo   Smart Cloth Advisor  ^|  FYP Group 24
echo  ========================================
echo.
echo  Master document:  CONTEXT.md
echo  (architecture, flow charts, ER diagram, how to run)
echo.

if exist "CONTEXT.md" (
  echo  Opening CONTEXT.md ...
  start "" "%~dp0CONTEXT.md"
) else (
  echo  ERROR: CONTEXT.md not found in %cd%
  pause
  exit /b 1
)

echo.
echo  Other docs in this folder:
echo    README.md
echo    PROJECT_ARCHITECTURE.md
echo    ML_PIPELINE.md
echo    API_DOCUMENTATION.md
echo    RECOMMENDATION_ENGINE.md
echo    NLP_DOCUMENTATION.md
echo    DATASET_DOCUMENTATION.md
echo    TESTING_REPORT.md
echo    LIMITATIONS.md
echo    DEPLOYMENT.md
echo.
echo  Tip: GitHub, VS Code, and Cursor render the Mermaid diagrams
echo       inside CONTEXT.md automatically.
echo.
pause
endlocal
