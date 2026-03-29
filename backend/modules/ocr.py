import io
import re
import json
import os
import numpy as np
from PIL import Image, ImageEnhance

_medicine_data = None
_substitutes_data = None

SAFETY_DISCLAIMER = "\n\n⚠️ **Disclaimer:** For informational purposes only. Always consult your doctor before taking any medication."


def _load_data():
    global _medicine_data, _substitutes_data
    if _medicine_data is None:
        path = os.path.join(os.path.dirname(__file__), "../data/medicines.json")
        with open(path) as f:
            _medicine_data = json.load(f)
    if _substitutes_data is None:
        path = os.path.join(os.path.dirname(__file__), "../data/substitutes.json")
        with open(path) as f:
            _substitutes_data = json.load(f)


def extract_raw_text(image_bytes: bytes) -> tuple:
    """Fast Tesseract OCR — try original image first, then enhanced."""
    image = Image.open(io.BytesIO(image_bytes))

    # Resize only if too small
    w, h = image.size
    if max(w, h) < 800:
        ratio = 1200 / max(w, h)
        image = image.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    try:
        import pytesseract

        # Try psm 6 on ORIGINAL image first — works best for structured prescriptions
        best, best_len = "", 0
        for cfg in ["--oem 3 --psm 6", "--oem 3 --psm 4", "--oem 1 --psm 6"]:
            try:
                text = pytesseract.image_to_string(image, lang='eng', config=cfg).strip()
                if len(text) > best_len:
                    best, best_len = text, len(text)
            except Exception:
                continue

        # If original gives good result, use it directly
        if best_len > 50:
            return best, "Tesseract"

        # Fallback: try enhanced grayscale
        gray = image.convert('L')
        enhanced = ImageEnhance.Contrast(gray).enhance(1.8)
        for cfg in ["--oem 3 --psm 6"]:
            try:
                text = pytesseract.image_to_string(enhanced, lang='eng', config=cfg).strip()
                if len(text) > best_len:
                    best, best_len = text, len(text)
            except Exception:
                continue

        if best.strip():
            return best, "Tesseract"

    except ImportError:
        pass

    # Last resort: EasyOCR
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        gray_arr = np.array(image.convert('L'))
        results = reader.readtext(gray_arr, detail=0, paragraph=True)
        text = "\n".join(results)
        if text.strip():
            return text, "EasyOCR"
    except ImportError:
        pass

    return "", "none"


def _build_lookup():
    _load_data()
    lookup = {}
    for key, info in _medicine_data.items():
        lookup[key.lower()] = key
        for brand in info.get("brand_names", []):
            lookup[brand.lower()] = key
    for brand, generic in _substitutes_data.get("brand_to_generic", {}).items():
        if brand.lower() not in lookup:
            lookup[brand.lower()] = generic
    return lookup


def find_medicines_in_text(text: str) -> list:
    """
    Find all medicine/drug items from prescription text.
    Handles multiple formats:
    - "DRUG NAME" column format (FOAM TRICLEAR, CREAM HYDRONIC...)
    - "TAB. XXXXX" / "CAP. XXXXX" format
    - Generic names written below
    Shows ALL identified items, even if not in database.
    """
    _load_data()
    lookup = _build_lookup()

    found_keys = set()
    found_names = set()  # Track all names including unrecognised
    results = []

    def add_known(key, display_name, instructions=""):
        if key in found_keys:
            return
        found_keys.add(key)
        found_names.add(display_name.lower())
        info = _medicine_data.get(key, {})
        results.append({
            "matched_name": display_name,
            "generic": info.get("generic", ""),
            "category": info.get("category", ""),
            "uses": info.get("uses", ""),
            "guidance": info.get("general_guidance", ""),
            "contraindications": info.get("contraindications", ""),
            "forms": info.get("available_forms", []),
            "instructions": instructions,
            "fuzzy": False,
            "in_db": True,
        })

    def add_unknown(display_name, form_type="", instructions=""):
        """Add an item that's not in the DB but was in the prescription."""
        key = display_name.lower()
        if key in found_names:
            return
        found_names.add(key)
        results.append({
            "matched_name": display_name,
            "generic": "",
            "category": f"Prescribed {form_type}".strip(),
            "uses": "",
            "guidance": instructions if instructions else "",
            "contraindications": "",
            "forms": [form_type] if form_type else [],
            "instructions": instructions,
            "fuzzy": False,
            "in_db": False,
        })

    # ── Pass 1: DRUG NAME column format ─────────────────────────────────
    # Format: FOAM TRICLEAR  |  90 day(s)  |  ...
    # First extract structured rows from prescription table
    lines = text.split("\n")
    
    # Skip header lines
    skip_phrases = ["drug name", "frequency", "duration", "instructions", "quantity",
                    "prescription", "medicine name", "dosage", "rx", "r\n"]
    
    drug_form_prefixes = ["foam", "cream", "gel", "serum", "ointment", "tablet", "capsule",
                          "cap", "tab", "syrup", "drops", "lotion", "solution", "injection",
                          "spray", "patch", "powder", "sachet", "suspension"]
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        line_lower = line.lower()
        
        # Skip empty lines and headers
        if not line or any(skip in line_lower for skip in skip_phrases):
            i += 1
            continue
        
        # Check if line starts with a drug form prefix (FOAM, CREAM, GEL, TAB, CAP, etc.)
        first_word = line_lower.split()[0] if line_lower.split() else ""
        
        # Also check for numbered items: "1) TAB. XXXX" or "1. CREAM XXXX"
        numbered = re.match(r'^\s*\d+[.)\s]+(.+)', line)
        if numbered:
            line = numbered.group(1).strip()
            line_lower = line.lower()
            first_word = line_lower.split()[0] if line_lower.split() else ""
        
        if first_word in drug_form_prefixes or re.match(r'^(tab|cap)[.,]\s', line_lower):
            # Extract drug name — remove dosage numbers at end and trailing instructions
            # Remove: "90 day(s)", "30 day(s)", "1-0-0", "After Food", numbers
            drug_name = re.sub(r'\s+\d+[-–]\d+[-–]\d+.*$', '', line).strip()
            drug_name = re.sub(r'\s+\d+\s*day.*$', '', drug_name, flags=re.IGNORECASE).strip()
            drug_name = re.sub(r'\s+\d+\s*capsule.*$', '', drug_name, flags=re.IGNORECASE).strip()
            drug_name = re.sub(r'\s+\d+\s*tablet.*$', '', drug_name, flags=re.IGNORECASE).strip()
            drug_name = re.sub(r'\s+[a-z]?\s*$', '', drug_name).strip()  # trailing single chars
            
            # Get instructions from next line if it looks like instructions
            instructions = ""
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                next_lower = next_line.lower()
                inst_keywords = ["morning", "night", "evening", "after food", "before food",
                                "empty stomach", "external use", "nose", "face", "scar",
                                "pimples", "patch", "apply", "twice", "once"]
                if any(kw in next_lower for kw in inst_keywords) and len(next_line) < 60:
                    instructions = next_line
            
            # Clean OCR noise from drug name
            drug_name = re.sub(r'[\\"\'|\[\]{}]', '', drug_name).strip()
            drug_name = re.sub(r'\s+\d+\s*mg$', '', drug_name, flags=re.IGNORECASE).strip()
            drug_name = re.sub(r'\s+\d+\s*(?:tablets?|capsules?|caps?|tabs?)\s*$', '', drug_name, flags=re.IGNORECASE).strip()
            drug_name = re.sub(r'\s+\d+[-–]\d+[-–]\d+.*$', '', drug_name).strip()
            drug_name = drug_name.strip()
            # Fix common OCR misreads in medicine names
            ocr_fixes = {
                "Asne": "Acne", "asne": "acne",
                "Acne Lode": "Acne Lode", "Acne Lofe": "Acne Lode",
                "Nignts": "Nights", "Morninq": "Morning",
            }
            for wrong, right in ocr_fixes.items():
                drug_name = drug_name.replace(wrong, right)
            # Skip if only a form word remains (e.g., just "Tablet", "Cream")
            clean_check = drug_name.lower().strip()
            # Remove dosage suffix for check
            clean_check = re.sub(r'\s+\d+.*$', '', clean_check).strip()
            if clean_check in drug_form_prefixes:
                i += 1
                continue
            # Skip very short names (likely OCR noise)
            if len(drug_name.strip()) < 4:
                i += 1
                continue
            if len(drug_name) >= 3:
                # Try to find in database
                matched = False
                # Check full name, then without form prefix
                candidates = [drug_name]
                words = drug_name.split()
                if len(words) > 1:
                    # Try without the form word (e.g., "FOAM TRICLEAR" -> "TRICLEAR")
                    candidates.append(" ".join(words[1:]))
                    candidates.append(words[-1])  # last word
                    candidates.append(words[1] if len(words) > 1 else words[0])
                
                for candidate in candidates:
                    cl = candidate.lower().strip()
                    # Fix common OCR misreads: "asne" -> "acne"
                    cl_fixed = cl.replace("asne", "acne").replace("acne lode", "acne lode")
                    for try_name in [cl, cl_fixed]:
                        if try_name in lookup:
                            add_known(lookup[try_name], drug_name.title(), instructions)
                            matched = True
                            break
                    if matched:
                        break
                    # Substring match
                    for name, key in lookup.items():
                        if len(name) >= 4 and (name in cl or cl in name or name in cl_fixed or cl_fixed in name):
                            if abs(len(name) - len(cl)) <= 6:
                                add_known(key, drug_name.title(), instructions)
                                matched = True
                                break
                    if matched:
                        break
                
                if not matched:
                    # Add as unknown but still show it
                    form_type = first_word.title() if first_word in drug_form_prefixes else "Medicine"
                    add_unknown(drug_name.title(), form_type, instructions)
        
        i += 1

    # ── Pass 2: Exact lookup — only for brand names, skip generics already covered ─────
    text_lower = text.lower()
    # Only match if the word appears in an actual medicine context (near TAB/CAP/CREAM etc.)
    medicine_context = re.sub(r'(?:drug name|frequency|duration|instructions|quantity|prescription).*?\n', '', text_lower, flags=re.IGNORECASE)
    for name in sorted(lookup.keys(), key=len, reverse=True):
        if len(name) < 5:
            continue
        if re.search(r'\b' + re.escape(name) + r'\b', medicine_context):
            key = lookup[name]
            # Skip if this would create a result with just a form word as name
            if name.lower().strip() in ['tablet', 'capsule', 'cream', 'gel', 'syrup', 'ointment', 'foam', 'serum']:
                continue
            if key not in found_keys:
                add_known(key, name.title())

    # ── Pass 3: Fuzzy match ───────────────────────────────────────────────
    for word in re.findall(r'\b[A-Za-z][A-Za-z0-9\-]{3,}\b', text):
        wl = word.lower()
        best_match, best_score = None, 0
        for name, key in lookup.items():
            if len(name) < 4 or abs(len(name) - len(wl)) > 3:
                continue
            score = sum(c1 == c2 for c1, c2 in zip(name, wl)) / max(len(name), len(wl))
            if score >= 0.82 and score > best_score:
                best_score, best_match = score, (name, key)
        if best_match:
            name, key = best_match
            if key not in found_keys and word.lower() not in found_names:
                add_known(key, word.title())

    # Final cleanup: remove entries where matched_name is just a form word alone
    drug_form_words = {'tablet', 'tablets', 'capsule', 'capsules', 'cream', 'gel', 
                       'ointment', 'syrup', 'foam', 'serum', 'lotion', 'spray', 'drops'}
    results = [r for r in results 
               if r['matched_name'].lower().strip() not in drug_form_words
               and len(r['matched_name'].strip()) > 3]
    return results


def extract_key_info(text: str) -> dict:
    info = {}

    # Doctor
    doc = re.search(r'Dr\.?\s+([A-Za-z][A-Za-z]{2,20})(?:\s+[A-Za-z\.]{1,5})?(?:\n|\r|,|;|\.|\s{2}|$)',
                    text, re.IGNORECASE)
    if doc:
        info["doctor"] = "Dr. " + doc.group(1).strip().title()

    # Hospital — look for "hospital" keyword in text
    hosp = re.search(r"([A-Za-z][A-Za-z\s']{2,30}(?:hospital|clinic|medical|health centre|health center))",
                     text, re.IGNORECASE)
    if hosp:
        info["hospital"] = hosp.group(1).strip().title()

    # Date
    date = re.search(r'(?:date[:\s]+)?(\d{1,2}[-/]\w+[-/]\d{2,4}|\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                     text, re.IGNORECASE)
    if date:
        info["date"] = date.group(1)

    # Diagnosis — look for "* MALARIA" after "Diagnosis:" heading
    diag_section = re.search(r'diagnosis[:\s*]*\n?\s*\*?\s*([A-Z][A-Z\s]{1,40}?)(?:\n|$)',
                              text, re.IGNORECASE)
    if diag_section:
        raw = diag_section.group(1).strip().lstrip("*: ").strip()
        noise = ["AND SAMPLE", "TEST FINDINGS", "SAMPLE", "ENTERING", "THESE ARE", "PRESCRIPTION"]
        clean = raw
        for n in noise:
            clean = clean.replace(n, "").strip()
        if len(clean) >= 2:
            info["diagnosis"] = clean.title()

    # Fallback: standalone disease names in text
    if not info.get("diagnosis"):
        disease = re.search(
            r'\b(MALARIA|DENGUE|TYPHOID|COVID[-\d]*|TUBERCULOSIS|TB|PNEUMONIA|'
            r'HYPERTENSION|DIABETES|ANAEMIA|ANEMIA|FRACTURE|APPENDICITIS)\b',
            text, re.IGNORECASE
        )
        if disease:
            info["diagnosis"] = disease.group(1).title()

    # Duration — pick largest
    durs = re.findall(r'(\d+)\s*(days?|weeks?|months?)', text, re.IGNORECASE)
    if durs:
        def to_days(n, unit):
            n = int(n)
            if 'week' in unit.lower(): n *= 7
            if 'month' in unit.lower(): n *= 30
            return n
        best = max(durs, key=lambda x: to_days(x[0], x[1]))
        info["duration"] = f"{best[0]} {best[1].title()}"

    # Follow-up
    followup = re.search(r'(?:follow.?up|next visit|review)[:\s]+([^\n]{3,20})',
                         text, re.IGNORECASE)
    if followup:
        info["followup"] = followup.group(1).strip()

    # Complaints — only from text BEFORE "Clinical Findings"
    complaints_text = text
    cf = re.search(r'clinical findings?', text, re.IGNORECASE)
    if cf:
        complaints_text = text[:cf.start()]
    complaints = re.findall(r'\*\s*([A-Z][A-Z\s]+?)(?:\n|\(|\d)', complaints_text)
    NOISE = ["THESE ARE", "ENTERING", "SAMPLE", "TEST FINDINGS", "PRESCRIPTION", "FINDINGS FOR"]
    cleaned = [c.strip() for c in complaints
               if 3 < len(c.strip()) < 50 and not any(n in c for n in NOISE)]
    if cleaned:
        info["complaints"] = cleaned[:3]

    # Patient
    pt = re.search(r'(?:patient|name)[:\s]+([A-Za-z][A-Za-z\s]{2,25}?)(?:\n|,|\(|age|\d|$)',
                   text, re.IGNORECASE)
    if pt:
        name = pt.group(1).strip()
        if 2 < len(name) < 30:
            info["patient"] = name.title()

    return info


def format_ocr_response(raw_text: str, method: str, medicines: list, key_info: dict) -> str:
    parts = ["## 📋 Prescription Analysis\n"]

    info_lines = []
    if key_info.get("doctor"):
        info_lines.append(f"👨‍⚕️ **Doctor:** {key_info['doctor']}")
    if key_info.get("hospital"):
        info_lines.append(f"🏥 **Hospital:** {key_info['hospital']}")
    if key_info.get("patient"):
        info_lines.append(f"🧑 **Patient:** {key_info['patient']}")
    if key_info.get("date"):
        info_lines.append(f"📅 **Date:** {key_info['date']}")
    if key_info.get("diagnosis"):
        info_lines.append(f"🩺 **Diagnosis:** {key_info['diagnosis']}")
    if key_info.get("complaints"):
        info_lines.append(f"📝 **Complaints:** {', '.join(key_info['complaints'])}")
    if key_info.get("duration"):
        info_lines.append(f"⏱️ **Course Duration:** {key_info['duration']}")
    if key_info.get("followup"):
        info_lines.append(f"🗓️ **Follow-up:** {key_info['followup']}")
    if info_lines:
        parts.append("\n".join(info_lines))

    if medicines:
        parts.append(f"---\n\n## 💊 Medicines Prescribed ({len(medicines)})\n")
        for i, m in enumerate(medicines, 1):
            lines = [f"### {i}. {m['matched_name']}"]
            # Show instructions if available (e.g. "NIGHTS - NOSE", "EXTERNAL USE MORNING")
            if m.get("instructions"):
                lines.append(f"📋 **Instructions:** {m['instructions']}")
            if m.get("in_db", True):
                # Known medicine — show full info
                if m["generic"] and m["generic"].lower() != m["matched_name"].lower():
                    lines.append(f"**Generic:** {m['generic']}")
                if m["category"]:
                    lines.append(f"**Type:** {m['category']}")
                if m["uses"]:
                    lines.append(f"**Used For:** {m['uses']}")
                if m["guidance"]:
                    lines.append(f"**How to Take:** {m['guidance']}")
                if m["contraindications"]:
                    lines.append(f"**⚠️ Avoid if:** {m['contraindications']}")
            else:
                # Unknown medicine — show what we know from prescription
                if m["category"]:
                    lines.append(f"**Form:** {m['category']}")
                lines.append("_ℹ️ This product is not in our database — consult your doctor or pharmacist for details._")
            parts.append("\n".join(lines))
    else:
        parts.append(
            "---\n\n**💊 No medicines identified.**\n\n"
            "Try a clearer, well-lit photo taken directly above the prescription."
        )

    result = "\n\n".join(parts)
    if medicines:
        result += SAFETY_DISCLAIMER
    return result


def process_prescription_image(image_bytes: bytes) -> dict:
    raw_text, method = extract_raw_text(image_bytes)

    if not raw_text.strip():
        return {
            "success": False,
            "message": (
                "❌ **Could not read this image.**\n\n"
                "Make sure Tesseract is installed:\n"
                "```\nbrew install tesseract\npip install pytesseract\n```\n\n"
                "**Tips:** Good lighting, camera directly above, text in focus."
            ),
            "raw_text": "",
            "medicines": []
        }

    medicines = find_medicines_in_text(raw_text)
    key_info = extract_key_info(raw_text)
    message = format_ocr_response(raw_text, method, medicines, key_info)

    return {
        "success": True,
        "message": message,
        "raw_text": raw_text,
        "medicines": medicines,
        "ocr_method": method
    }