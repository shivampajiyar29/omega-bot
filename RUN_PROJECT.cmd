@echo off
setlocal

cd /d "%~dp0"

if not defined POSTGRES_PASSWORD set "POSTGRES_PASSWORD=omegabot"
if not defined REDIS_PASSWORD set "REDIS_PASSWORD=omegabot"
if not defined LOCAL_API_URL set "LOCAL_API_URL=http://localhost:18000"
if not defined LOCAL_WS_URL set "LOCAL_WS_URL=ws://localhost:18000"
if not defined API_PORT set "API_PORT=18000"
if not defined WEB_PORT set "WEB_PORT=13000"

echo Starting OmegaBot full stack...
docker compose -f infra/docker-compose.local.yml --env-file .env up --build -d

if errorlevel 1 (
  echo.
  echo Failed to start containers. Check Docker Desktop and .env values.
  pause
  exit /b 1
)

echo.
echo OmegaBot started successfully.
echo Web: http://localhost:13000
echo API: http://localhost:18000/docs
echo.
pause
