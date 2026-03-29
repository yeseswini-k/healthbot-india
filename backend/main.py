from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.ocr import router as ocr_router

app = FastAPI(
    title="HealthBot India API",
    description="AI-powered health assistant for India – symptom checker, first aid, medicine info, substitutes, OCR, hospital finder.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(ocr_router, prefix="/api", tags=["OCR"])


@app.get("/")
def root():
    return {
        "status": "running",
        "app": "HealthBot India",
        "version": "1.0.0",
        "endpoints": ["/api/chat", "/api/ocr/upload", "/docs"]
    }


@app.get("/health")
def health():
    return {"status": "ok"}
