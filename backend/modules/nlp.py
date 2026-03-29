import re
from typing import Tuple

INTENT_PATTERNS = {
    "first_aid": [
        r"\b(first aid|emergency|burned?|burn|scalded?|cut|bleeding|bleed|faint|fainting|chok(e|ing)|fracture|broken bone|heart attack|stroke|allergic|anaphylaxis|electric shock|drowning|poison(ing)?|nosebleed|nose bleed|heat stroke|head injury)\b",
        r"\b(what (to|should) (do|i do)|how to treat|how do i treat)\b.{0,40}\b(burn|cut|wound|injury|pain|accident)\b",
    ],
    "medicine_info": [
        r"\b(what is|tell me about|explain|information about|info on|what does|how does|use of|uses of|purpose of|what are|side effects of|dosage of)\b.{0,40}\b(tablet|medicine|drug|capsule|syrup|medication|pill|injection|drops)\b",
        r"\b(paracetamol|ibuprofen|cetirizine|levocetirizine|fexofenadine|omeprazole|pantoprazole|rabeprazole|azithromycin|amoxicillin|ciprofloxacin|metronidazole|doxycycline|metformin|glimepiride|atorvastatin|rosuvastatin|diclofenac|naproxen|ondansetron|loperamide|ranitidine|domperidone|montelukast|salbutamol|aspirin|clopidogrel|amlodipine|losartan|telmisartan|propranolol|metoprolol|levothyroxine|escitalopram|sertraline|alprazolam|clonazepam|pregabalin|gabapentin|tamsulosin|sildenafil|clotrimazole|fluconazole|terbinafine|acyclovir|hydroxyzine|lactulose|minoxidil|cinnarizine|betahistine|prednisolone|hydroxychloroquine)\b",
        r"\b(crocin|dolo|calpol|brufen|combiflam|cetzine|alerid|levocet|allegra|omez|pan 40|azithral|mox|augmentin|ciplox|flagyl|metrogyl|glycomet|atorva|crestor|voveran|emeset|imodium|zinetac|domstal|montair|asthalin|disprin|ecosprin|clopilet|amlokind|telma|thyronorm|nexito|serta|alprax|rivotril|lyrica|urimax|viagra|penegra|candid|zovirax|terbicip|flucos|duphalac|electral|enterogermina|cyclopam|meftal|gelusil|sinarest|cheston|stugeron|vertin|shelcal|calcirol|neurobion|becosules|supradyn|tugain|nizoral|norflox|norflox-tz|wysolone|hcqs|atarax)\b",
    ],
    "substitute": [
        r"\b(substitute|alternative|replacement|instead of|don.t have|dont have|not available|out of stock|replace|equivalent|generic|similar to|same as|other option)\b",
        r"don.?t have\b",
        r"\binstead\b",
        r"can.?t find\b",
        r"not available\b",
    ],
    "hospital": [
        r"\b(hospital|clinic|doctor|physician|specialist|medical center|nursing home|health center|pharmacy|chemist|dispensary|emergency room)\b.{0,25}\b(near|nearby|around|close|in|find|locate|search)\b",
        r"\b(find|locate|search|nearest|nearby|close to)\b.{0,25}\b(hospital|clinic|doctor|medical|pharmacy|chemist)\b",
        r"\b(pincode|pin code|zip code|\d{6})\b",
        r"\b(pharmacy|pharmacies|chemist|medicine shop|medical shop)\b",
        r"\bhospital(s)?\b",
        r"\bnear me\b",
    ],
    "symptoms": [
        r"\b(symptom|feeling|suffer|experiencing|pain|ache|hurt|sick|ill|unwell|not feeling well|feel bad|having trouble|problem with)\b",
        r"\b(fever|headache|cough|cold|sore throat|stomach|acidity|heartburn|diarrhea|diarrhoea|loose motion|vomiting|nausea|back pain|rash|rashes|eye|toothache|anxiety|insomnia|joint pain|chest pain|breathing|urinary|dizzy|dizziness|vertigo|lightheaded|spinning|migraine|constipation|bloating|gas|fatigue|weakness|tiredness|body ache|period pain|acne|hair loss|dandruff|swelling|palpitations|dehydration|dengue|malaria|covid|asthma|allergy|depression|stress|motion sickness|ear pain|neck pain|shoulder pain|knee pain|fungal|itching|sunburn|thyroid)\b",
        r"\b(i have|i am having|i feel|i.m feeling|suffering from|diagnosed with|i.ve been|been having|experiencing)\b",
        r"\b(hurt|hurts|hurting|pain(ing)?|aching|sore|swollen|burning|stinging|throbbing)\b",
    ],
    "ocr": [
        r"\b(prescription|upload|image|photo|scan|ocr|extract text|read medicine|identify medicine|medicine list|decode)\b",
        r"\b(read my|analyze|analyse|check my)\b.{0,25}\b(prescription|medicine|tablet|report)\b",
        r"\bpresription\b",
        r"\bprescription\b",
    ],
    "greeting": [
        r"^(hi|hello|hey|good morning|good afternoon|good evening|howdy|greetings|namaste|namaskar|vanakkam|hii|helo)\b",
        r"^(what can you|what do you|how can you|can you help|help me)\b",
        r"^(who are you|what are you)\b",
    ],
}

SYMPTOM_ALIASES = {
    "dizzy": "dizziness",
    "dizziness": "dizziness",
    "vertigo": "vertigo",
    "spinning": "spinning",
    "lightheaded": "lightheaded",
    "light headed": "lightheaded",
    "light-headed": "lightheaded",
    "giddy": "dizziness",
    "loose motion": "loose motion",
    "loose motions": "loose motions",
    "tummy ache": "stomach pain",
    "stomach ache": "stomach pain",
    "belly pain": "stomach pain",
    "belly ache": "stomach pain",
    "abdominal pain": "stomach pain",
    "throat pain": "throat pain",
    "throat ache": "sore throat",
    "runny nose": "runny nose",
    "blocked nose": "blocked nose",
    "stuffy nose": "blocked nose",
    "dry cough": "dry cough",
    "wet cough": "wet cough",
    "phlegm": "wet cough",
    "mucus": "wet cough",
    "cant sleep": "insomnia",
    "can't sleep": "insomnia",
    "cannot sleep": "insomnia",
    "trouble sleeping": "insomnia",
    "no sleep": "insomnia",
    "sleep problem": "insomnia",
    "tired": "fatigue",
    "tiredness": "fatigue",
    "exhausted": "fatigue",
    "exhaustion": "fatigue",
    "lethargic": "fatigue",
    "weakness": "weakness",
    "weak": "weakness",
    "body pain": "body ache",
    "body pains": "body ache",
    "muscle pain": "body ache",
    "muscle ache": "body ache",
    "myalgia": "body ache",
    "period pain": "period pain",
    "period cramps": "menstrual cramps",
    "menstrual pain": "menstrual cramps",
    "menstrual cramp": "menstrual cramps",
    "painful periods": "period pain",
    "knee pain": "knee pain",
    "knee ache": "knee pain",
    "shoulder pain": "shoulder pain",
    "neck pain": "neck pain",
    "lower back pain": "lower back pain",
    "back ache": "back pain",
    "backache": "back pain",
    "constipated": "constipation",
    "no motion": "constipation",
    "hard stool": "constipation",
    "gas problem": "gas",
    "bloated": "bloating",
    "acne": "acne",
    "pimples": "acne",
    "pimple": "acne",
    "breakout": "acne",
    "skin rash": "skin rash",
    "itchy skin": "itching",
    "itching": "itching",
    "rash": "skin rash",
    "hives": "skin rash",
    "red eye": "red eye",
    "eye redness": "red eye",
    "pink eye": "red eye",
    "conjunctivitis": "eye irritation",
    "motion sickness": "motion sickness",
    "travel sickness": "motion sickness",
    "car sick": "motion sickness",
    "sea sick": "motion sickness",
    "seasick": "motion sickness",
    "dengue": "dengue",
    "dengue fever": "dengue",
    "malaria": "malaria",
    "typhoid": "typhoid",
    "covid": "covid",
    "coronavirus": "covid",
    "covid-19": "covid",
    "burning urine": "burning urination",
    "painful urination": "burning urination",
    "urinary pain": "burning urination",
    "uti": "urinary infection",
    "urine infection": "urinary infection",
    "hair fall": "hair loss",
    "hair falling": "hair loss",
    "balding": "hair loss",
    "bald": "hair loss",
    "dandruff": "dandruff",
    "flakes": "dandruff",
    "scalp flakes": "dandruff",
    "sunburn": "sunburn",
    "sun burn": "sunburn",
    "dehydrated": "dehydration",
    "high bp": "high blood pressure",
    "hypertension": "high blood pressure",
    "blood pressure high": "high blood pressure",
    "heart beat fast": "palpitations",
    "racing heart": "palpitations",
    "irregular heartbeat": "palpitations",
    "anxiety": "anxiety",
    "anxious": "anxiety",
    "panic": "anxiety",
    "panic attack": "anxiety",
    "stressed": "stress",
    "depressed": "depression",
    "depression": "depression",
    "asthma": "asthma",
    "wheezing": "asthma",
    "allergic": "allergies",
    "allergy": "allergies",
    "swollen feet": "swelling",
    "edema": "swelling",
    "oedema": "swelling",
    "thyroid": "thyroid",
    "thyroid problem": "thyroid",
    "mouth sore": "mouth ulcer",
    "canker sore": "mouth ulcer",
    "oral ulcer": "mouth ulcer",
    "heartburn": "heartburn",
    "acid reflux": "acidity",
    "indigestion": "acidity",
    "high sugar": "high blood sugar",
    "diabetes": "high blood sugar",
    "blood sugar high": "high blood sugar",
    "fungal": "fungal infection",
    "ringworm": "fungal infection",
    "athletes foot": "fungal infection",
    "flakes": "dandruff",
}

KNOWN_MEDICINES = [
    "paracetamol", "ibuprofen", "cetirizine", "levocetirizine", "fexofenadine",
    "omeprazole", "pantoprazole", "rabeprazole", "azithromycin", "amoxicillin",
    "ciprofloxacin", "metronidazole", "doxycycline", "metformin", "glimepiride",
    "atorvastatin", "rosuvastatin", "diclofenac", "naproxen", "ondansetron",
    "loperamide", "ranitidine", "domperidone", "montelukast", "salbutamol",
    "aspirin", "clopidogrel", "amlodipine", "losartan", "telmisartan",
    "propranolol", "metoprolol", "levothyroxine", "escitalopram", "sertraline",
    "alprazolam", "clonazepam", "pregabalin", "gabapentin", "tamsulosin",
    "sildenafil", "clotrimazole", "fluconazole", "terbinafine", "acyclovir",
    "hydroxyzine", "lactulose", "minoxidil", "cinnarizine", "betahistine",
    "prednisolone", "hydroxychloroquine", "cyclopam", "mefenamic acid",
    "crocin", "dolo", "dolo 650", "calpol", "brufen", "combiflam", "cetzine",
    "alerid", "levocet", "allegra", "omez", "pan 40", "azithral", "mox",
    "augmentin", "ciplox", "flagyl", "metrogyl", "glycomet", "atorva", "crestor",
    "voveran", "emeset", "imodium", "zinetac", "domstal", "montair", "asthalin",
    "disprin", "ecosprin", "clopilet", "amlokind", "telma", "thyronorm",
    "nexito", "serta", "alprax", "rivotril", "lyrica", "urimax", "candid",
    "zovirax", "terbicip", "flucos", "duphalac", "electral", "enterogermina",
    "meftal", "gelusil", "sinarest", "cheston", "stugeron", "vertin", "shelcal",
    "calcirol", "neurobion", "becosules", "supradyn", "tugain", "nizoral",
    "norflox", "norflox-tz", "wysolone", "hcqs", "atarax", "isabgol",
]


def detect_intent(text: str) -> Tuple[str, float]:
    text_lower = text.lower().strip()
    scores = {intent: 0 for intent in INTENT_PATTERNS}

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                scores[intent] += len(matches) * (2 if intent in ["first_aid", "substitute"] else 1)

    # OCR boost — "decode", "prescription", "presription" (typo), "read my prescription"
    ocr_keywords = ["prescription", "presription", "presciption", "decode prescription",
                    "upload", "scan", "ocr", "read prescription", "decode"]
    if any(kw in text_lower for kw in ocr_keywords):
        scores["ocr"] += 8

    substitute_keywords = ["don't have", "dont have", "substitute", "alternative", "instead of",
                           "not available", "replace", "can't find", "cant find", "out of stock",
                           "similar to", "find substitute", "find alternative"]
    if any(kw in text_lower for kw in substitute_keywords):
        scores["substitute"] += 6

    # Medicine info boost — "uses", "what is", "why take", "dosage", "side effects"
    medicine_info_keywords = ["uses", "use of", "used for", "what is", "why take", "why is",
                              "what does", "dosage", "dose", "side effect", "how to take",
                              "information", "info about", "tell me about", "details of",
                              "purpose of", "what for"]
    if any(kw in text_lower for kw in medicine_info_keywords):
        scores["medicine_info"] += 6
        scores["substitute"] = max(0, scores["substitute"] - 4)  # reduce substitute score

    first_aid_emergency = ["burn", "cut", "faint", "choke", "fracture", "heart attack", "stroke",
                           "bleeding", "drowning", "poisoning", "shock", "accident", "i cut",
                           "i am bleeding", "i'm bleeding"]
    if any(kw in text_lower for kw in first_aid_emergency):
        scores["first_aid"] += 5

    hospital_keywords = ["hospital", "clinic", "doctor near", "pharmacy near", "chemist near",
                         "pincode", "pin code", "find hospital", "near me"]
    if any(kw in text_lower for kw in hospital_keywords):
        scores["hospital"] += 6

    if re.fullmatch(r'\s*\d{6}\s*', text_lower):
        scores["hospital"] += 8

    for alias in SYMPTOM_ALIASES:
        if alias in text_lower:
            scores["symptoms"] += 3
            break

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score == 0:
        return "unknown", 0.0

    confidence = min(best_score / 10.0, 1.0)
    return best_intent, confidence


def extract_symptom_keywords(text: str) -> list:
    text_lower = text.lower()
    found = []

    for alias, canonical in SYMPTOM_ALIASES.items():
        if alias in text_lower and canonical not in found:
            found.append(canonical)

    direct_symptoms = [
        "fever", "headache", "migraine", "dizziness", "dizzy", "vertigo", "lightheaded",
        "spinning", "cough", "dry cough", "wet cough", "cold", "runny nose", "blocked nose",
        "sore throat", "throat pain", "stomach pain", "stomach ache", "acidity", "heartburn",
        "diarrhea", "loose motion", "loose motions", "vomiting", "nausea", "motion sickness",
        "back pain", "lower back pain", "neck pain", "shoulder pain", "knee pain",
        "skin rash", "itching", "fungal infection", "eye irritation", "red eye",
        "toothache", "ear pain", "anxiety", "stress", "insomnia", "joint pain",
        "chest pain", "difficulty breathing", "shortness of breath", "urinary infection",
        "burning urination", "cold and fever", "body ache", "fatigue", "weakness", "tiredness",
        "constipation", "bloating", "gas", "palpitations", "swelling", "hair loss", "dandruff",
        "period pain", "menstrual cramps", "mouth ulcer", "acne", "sunburn", "dehydration",
        "dengue", "malaria", "typhoid", "covid", "asthma", "allergies", "depression",
        "high blood pressure", "thyroid", "high blood sugar", "cant sleep"
    ]

    for symptom in direct_symptoms:
        if symptom in text_lower and symptom not in found:
            found.append(symptom)

    return found if found else []


def extract_medicine_name(text: str) -> str:
    text_lower = text.lower()

    # First: scan for known medicine names directly in the text (most reliable)
    for med in sorted(KNOWN_MEDICINES, key=len, reverse=True):  # longest match first
        if re.search(r'\b' + re.escape(med) + r'\b', text_lower):
            return med

    # Fallback: strip filler words and return remainder
    fillers = [
        "i don't have", "i dont have", "substitute for", "alternative to",
        "instead of", "don't have", "dont have", "find substitute", "find alternative",
        "what is", "tell me about", "information about", "side effects of", "dosage of",
        "what can i use", "i need", "give me", "please", "help me",
    ]
    result = text_lower
    for filler in sorted(fillers, key=len, reverse=True):
        result = result.replace(filler, " ")

    stop = {"the", "a", "an", "i", "me", "my", "is", "it", "of", "for", "and",
            "tablet", "medicine", "drug", "capsule", "syrup", "medication",
            "pill", "substitute", "alternative", "replacement", "instead", "use"}
    words = [w.strip("?,!.") for w in result.split() if w.strip("?,!.") not in stop and len(w.strip("?,!.")) > 1]
    return " ".join(words).strip()


def extract_first_aid_topic(text: str) -> str:
    topics_map = {
        "burns": ["burn", "burned", "burnt", "fire", "hot water", "scalded", "scald", "boiling water"],
        "cuts": ["cut", "wound", "bleeding", "bleed", "laceration", "scratch", "gash", "knife",
                 "i cut", "cut my", "cut myself", "i am bleeding", "i'm bleeding", "im bleeding"],
        "fainting": ["faint", "fainting", "unconscious", "passed out", "blackout", "collapse", "collapsed"],
        "choking": ["choke", "choking", "swallowed", "stuck in throat", "throat blocked"],
        "fracture": ["fracture", "broken bone", "break", "broke", "bone", "sprain"],
        "heart attack": ["heart attack", "cardiac", "chest pain radiating", "heart", "myocardial"],
        "stroke": ["stroke", "brain attack", "paralysis", "face drooping", "arm weakness", "slurred speech"],
        "allergic reaction": ["allergy", "allergic", "anaphylaxis", "anaphylactic", "hives", "throat swelling"],
        "eye injury": ["eye", "eyes", "chemical in eye", "dust in eye", "eye wash"],
        "nose bleed": ["nosebleed", "nose bleed", "nose bleeding", "blood from nose"],
        "electric shock": ["electric", "electrocuted", "electricity", "wire shock"],
        "heat stroke": ["heat stroke", "heatstroke", "overheated", "sunstroke"],
        "drowning": ["drowning", "drowned", "near drowning", "water accident"],
        "poisoning": ["poison", "poisoning", "ingested", "swallowed chemical", "toxic", "overdose"],
    }

    text_lower = text.lower()
    for topic, keywords in topics_map.items():
        if any(kw in text_lower for kw in keywords):
            return topic
    return ""


def extract_pincode(text: str) -> str:
    match = re.search(r'\b[1-9]\d{5}\b', text)
    if match:
        return match.group(0)
    return ""

# This file was patched - see KNOWN_MEDICINES and detect_intent