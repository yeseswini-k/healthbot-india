from fastapi import APIRouter
from pydantic import BaseModel
from modules.nlp import detect_intent, extract_medicine_name, extract_first_aid_topic, extract_pincode
from modules.symptoms import get_symptom_info
from modules.medicine import get_medicine_info
from modules.substitutes import get_substitute
from modules.first_aid import get_first_aid
from modules.hospital import find_hospitals, find_pharmacies, detect_specialty
import re

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

def is_pharmacy_request(text: str) -> bool:
    return any(kw in text.lower() for kw in [
        "pharmacy", "pharmacies", "chemist", "medicine shop",
        "medical shop", "drug store", "medplus", "apollo pharmacy",
        "find pharmacy", "pharmacy near", "pharmacy in",
        "chemist near", "chemist in",
    ])

def is_hospital_request(text: str) -> bool:
    return any(kw in text.lower() for kw in [
        "hospital", "clinic", "doctor", "specialist", "find hospital",
        "hospitals in", "hospitals near", "clinics in", "clinics near",
        "dermatologist", "cardiologist", "neurologist", "gynecologist",
        "gynaecologist", "ophthalmologist", "pediatrician", "paediatrician",
        "psychiatrist", "physiotherapist", "orthopedic", "orthopaedic",
        "eye hospital", "eye doctor", "skin doctor", "heart specialist",
        "ent", "bone doctor",
    ])

@router.post("/chat")
async def chat(req: ChatRequest):
    text = req.message.strip()
    if not text:
        return {"response": "Please type a message.", "intent": "unknown"}

    intent, confidence = detect_intent(text)

    if intent == "greeting":
        return {
            "response": (
                "👋 **Hello! I'm HealthBot India.**\n\n"
                "I can help you with:\n\n"
                "- 🤒 **Symptom Check** — *\"I have fever and dizziness\"*\n"
                "- 💊 **Medicine Info** — *\"What is Augmentin?\"*\n"
                "- 🔄 **Substitutes** — *\"I don't have Crocin\"*\n"
                "- 🩺 **First Aid** — *\"First aid for burns\"*\n"
                "- 🏥 **Hospitals** — *\"hospitals in vadapalani\"* or *\"600024\"*\n"
                "- 👁️ **Specialists** — *\"eye hospital in anna nagar\"*\n"
                "- 💊 **Pharmacy** — *\"pharmacy in ashok nagar\"*\n"
                "- 📋 **Prescription** — Upload photo via 📎\n\n"
                "*Works for any area or pincode across India!*"
            ),
            "intent": "greeting"
        }

    if intent == "first_aid":
        topic = extract_first_aid_topic(text)
        resp = get_first_aid(topic)
        return {"response": resp["message"], "intent": "first_aid"}

    if intent == "symptoms":
        resp = get_symptom_info(text)
        if resp:
            return {"response": resp, "intent": "symptoms"}
        return {
            "response": (
                "🤒 **I didn't find an exact symptom match.**\n\n"
                "Try describing more specifically:\n\n"
                "- *\"I feel dizzy and lightheaded\"*\n"
                "- *\"I have fever and body ache\"*\n"
                "- *\"My stomach hurts and I have loose motions\"*"
            ),
            "intent": "symptoms"
        }

    if intent == "medicine_info":
        med = extract_medicine_name(text)
        resp = get_medicine_info(med)
        return {"response": resp, "intent": "medicine_info"}

    if intent == "substitute":
        med = extract_medicine_name(text)
        resp = get_substitute(med)
        return {"response": resp, "intent": "substitute"}

    if intent == "hospital" or is_hospital_request(text) or is_pharmacy_request(text):
        pincode = extract_pincode(text)

        if is_pharmacy_request(text):
            result = await find_pharmacies(pincode=pincode, raw_text=text)
        else:
            specialty = detect_specialty(text)
            result = await find_hospitals(pincode=pincode, specialty=specialty, raw_text=text)

        return {"response": result["message"], "intent": "hospital"}

    if intent == "ocr":
        return {
            "response": (
                "📋 **Prescription Upload**\n\n"
                "Click the **📎 attachment button** to upload a prescription image.\n\n"
                "**Tips:**\n"
                "- Good lighting, no shadows\n"
                "- Camera directly above\n"
                "- Higher resolution = better accuracy"
            ),
            "intent": "ocr"
        }

    # Fallbacks
    sym_resp = get_symptom_info(text)
    if sym_resp:
        return {"response": sym_resp, "intent": "symptoms"}

    med_name = extract_medicine_name(text)
    if len(med_name) > 2:
        med_resp = get_medicine_info(med_name)
        if "not found" not in med_resp.lower():
            return {"response": med_resp, "intent": "medicine_info"}
        sub_resp = get_substitute(med_name)
        if "not found" not in sub_resp.lower():
            return {"response": sub_resp, "intent": "substitute"}

    # Bare pincode
    if re.fullmatch(r'\s*\d{6}\s*', text.strip()):
        result = await find_hospitals(pincode=text.strip(), raw_text=text)
        return {"response": result["message"], "intent": "hospital"}

    return {
        "response": (
            "🤔 **I'm not sure how to help with that.**\n\n"
            "Try:\n\n"
            "- *\"I have fever and dizziness\"* → Symptoms\n"
            "- *\"First aid for burns\"* → Emergency\n"
            "- *\"What is Augmentin?\"* → Medicine info\n"
            "- *\"I don't have Crocin\"* → Substitute\n"
            "- *\"Hospitals in vadapalani\"* → Hospital finder\n"
            "- *\"Dermatologist in kodambakkam\"* → Specialist\n"
            "- *\"Pharmacy in ashok nagar\"* → Pharmacy finder"
        ),
        "intent": "unknown"
    }