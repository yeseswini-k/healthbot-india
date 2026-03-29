from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from modules.ocr import process_prescription_image

router = APIRouter()


class OCRResponse(BaseModel):
    success: bool
    message: str
    raw_text: str
    medicines: list


@router.post("/ocr/upload", response_model=OCRResponse)
async def upload_prescription(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted (JPEG, PNG, BMP, TIFF)")

    # Limit file size to 10MB
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    result = process_prescription_image(contents)

    return OCRResponse(
        success=result["success"],
        message=result["message"],
        raw_text=result.get("raw_text", ""),
        medicines=result.get("medicines", [])
    )