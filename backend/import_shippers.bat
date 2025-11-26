@echo off
echo.
echo ============================================================
echo    IMPORTING TEST SHIPPERS TO MONGODB
echo ============================================================
echo.

cd /d "%~dp0.."
node scripts/import_shippers.js

echo.
echo ============================================================
echo    IMPORT COMPLETE
echo ============================================================
echo.
pause
