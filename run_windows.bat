@echo off
echo Starting HealthBot India Backend...
cd backend
start cmd /k "pip install -r requirements.txt && uvicorn main:app --reload --port 8000"
cd ..
echo Starting HealthBot India Frontend...
cd frontend
start cmd /k "npm install && npm start"
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
