# HealthBot India v2.0

AI-powered healthcare assistant built using FastAPI and React, featuring NLP-based symptom analysis, OCR for prescriptions, and an integrated medical database.

## Overview

HealthBot India is a full-stack application designed to assist users with basic healthcare needs. It provides symptom analysis, medicine suggestions, first aid guidance, OCR-based prescription reading, and substitute medicine recommendations.

## Features

* Symptom analysis using NLP
* Medicine recommendation system
* First aid guidance
* OCR-based prescription reading (EasyOCR + Tesseract support)
* Substitute medicine suggestions
* Google Maps integration for hospitals

## Tech Stack

* Backend: FastAPI (Python)
* Frontend: React.js
* NLP Processing
* OCR Integration

## Project Structure

healthbot-india/

* backend/

  * data/
  * modules/
  * routes/
  * main.py
  * requirements.txt

* frontend/

  * public/
  * src/
  * package.json

* run.sh

* run_windows.bat

* README.md

## Setup Instructions

### Backend

cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

### Frontend

cd frontend
npm install
npm start

## OCR Setup (Optional)

pip install easyocr opencv-python-headless

Alternative (Tesseract):

macOS: brew install tesseract
Ubuntu: sudo apt install tesseract-ocr

pip install pytesseract

## Usage

1. Start backend server
2. Start frontend
3. Open http://localhost:3000
4. Use chatbot for healthcare assistance

## Future Improvements

* Database integration
* Cloud deployment
* UI/UX enhancements
* Improved NLP accuracy

## Disclaimer

This project is for educational purposes only. Always consult a qualified medical professional for health-related decisions.
