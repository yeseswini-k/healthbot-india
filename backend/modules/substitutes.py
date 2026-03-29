import json
import os
import re

_data = None
SAFETY_DISCLAIMER = "\n\n⚠️ **Disclaimer:** Consult your doctor or pharmacist before switching medicines."

def _load():
    global _data
    if _data is None:
        path = os.path.join(os.path.dirname(__file__), "../data/substitutes.json")
        with open(path) as f:
            _data = json.load(f)

def _normalise(s: str) -> str:
    return re.sub(r'[^a-z0-9 ]', '', s.lower().strip())

def get_substitute(query: str) -> str:
    _load()
    q = _normalise(query)
    if not q or len(q) < 2:
        return "Please specify the medicine name to find a substitute."

    b2g = _data.get("brand_to_generic", {})
    gen_subs = _data.get("generic_substitutes", {})

    # Step 1: direct brand_to_generic lookup
    generic_key = None
    if q in b2g:
        generic_key = b2g[q]
    else:
        # Partial brand match
        for brand, gen in b2g.items():
            if q in brand or brand in q:
                if abs(len(q) - len(brand)) <= 4:
                    generic_key = gen
                    break

    # Step 2: check if query is already a generic
    if not generic_key:
        for key in gen_subs:
            if q == _normalise(key) or q in _normalise(key) or _normalise(key) in q:
                generic_key = key
                break

    # Step 3: word-level fuzzy
    if not generic_key:
        words = re.findall(r'[a-z]+', q)
        for word in words:
            if len(word) < 4:
                continue
            for brand in b2g:
                if word in brand or brand in word:
                    generic_key = b2g[brand]
                    break
            if generic_key:
                break

    if not generic_key:
        return (
            f"🔄 **No substitute found for '{query}'.**\n\n"
            "Try using the exact generic or brand name. Examples:\n"
            "- *\"I don't have Crocin\"*\n"
            "- *\"substitute for Pan 40\"*\n"
            "- *\"alternative to Augmentin\"*"
        )

    # Look up substitutes
    sub_info = gen_subs.get(generic_key)
    if not sub_info:
        return (
            f"🔄 **Generic identified:** *{generic_key.title()}*\n\n"
            "Substitute brands not listed in database. Ask your pharmacist for generic alternatives."
        )

    brands = sub_info.get("brands", [])
    note = sub_info.get("note", "")
    brands_str = "\n".join([f"  • {b}" for b in brands])

    resp = (
        f"## 🔄 Substitutes for **{query.title()}**\n\n"
        f"**Generic:** *{generic_key.title()}*\n\n"
        f"**Available brands:**\n{brands_str}\n\n"
        f"**📝 Note:** {note}"
    )
    return resp + SAFETY_DISCLAIMER
