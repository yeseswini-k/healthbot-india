import json
import os
import re

_data = None
SAFETY_DISCLAIMER = "\n\n⚠️ **Disclaimer:** Informational only. Always consult a doctor or pharmacist before taking any medication."

def _load():
    global _data
    if _data is None:
        path = os.path.join(os.path.dirname(__file__), "../data/medicines.json")
        with open(path) as f:
            _data = json.load(f)

def _find_medicine(query: str):
    """Find medicine key by brand name or generic name, with fuzzy fallback."""
    q = query.lower().strip()
    if not q or len(q) < 2:
        return None, None

    # Exact key match
    if q in _data:
        return q, _data[q]

    # Exact brand match
    for key, info in _data.items():
        brands = [b.lower() for b in info.get("brand_names", [])]
        if q in brands:
            return key, info

    # Substring match (brand contains query or query contains brand)
    for key, info in _data.items():
        brands = [b.lower() for b in info.get("brand_names", [])]
        if any(q in b or b in q for b in brands):
            if max(len(q), max((len(b) for b in brands), default=0)) - min(len(q), min((len(b) for b in brands), default=999)) <= 5:
                return key, info

    # Fuzzy: check if query is close to any known name
    all_names = {}
    for key, info in _data.items():
        all_names[key] = (key, info)
        for brand in info.get("brand_names", []):
            all_names[brand.lower()] = (key, info)

    # Try word by word
    words = re.findall(r'[a-z0-9]+', q)
    for w in words:
        if len(w) < 4:
            continue
        for name, (key, info) in all_names.items():
            if w == name or w in name or name in w:
                if abs(len(w) - len(name)) <= 4:
                    return key, info

    return None, None


def get_medicine_info(query: str) -> str:
    _load()
    key, info = _find_medicine(query)

    if not info:
        return (
            f"💊 **Medicine Not Found: '{query}'**\n\n"
            "This medicine isn't in my database. Try:\n"
            "- The full generic name (e.g., *paracetamol*, *ibuprofen*)\n"
            "- A common brand name (e.g., *Crocin*, *Brufen*, *Dolo 650*)\n\n"
            "**Medicines I know include:**\n"
            "Paracetamol, Ibuprofen, Cetirizine, Omeprazole, Pantoprazole, Azithromycin, "
            "Amoxicillin, Ciprofloxacin, Metformin, Atorvastatin, Diclofenac, Ondansetron, "
            "Salbutamol, Montelukast, Levothyroxine, Betahistine, Cinnarizine, Minoxidil, "
            "and 50+ more."
        )

    brands_str = ", ".join(info.get("brand_names", [])[:6])
    uses = info.get("uses", "")
    guidance = info.get("general_guidance", "")
    contra = info.get("contraindications", "")
    forms = ", ".join(info.get("available_forms", []))
    category = info.get("category", "")
    generic = info.get("generic", key.title())

    resp = (
        f"## 💊 {generic}\n\n"
        f"**Category:** {category}\n\n"
        f"**Common Brands:** {brands_str}\n\n"
        f"**Uses:** {uses}\n\n"
        f"**How to Take:** {guidance}\n\n"
        f"**Do NOT take if:** {contra}\n\n"
        f"**Available as:** {forms}"
    )

    return resp + SAFETY_DISCLAIMER
