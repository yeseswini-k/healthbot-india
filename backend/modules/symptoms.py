import json
import os
import re

_data = None
SAFETY_DISCLAIMER = "\n\n⚠️ **Disclaimer:** This is informational only. Please consult a qualified doctor before taking any medication."

def _load():
    global _data
    if _data is None:
        path = os.path.join(os.path.dirname(__file__), "../data/symptoms.json")
        with open(path) as f:
            _data = json.load(f)

def _fuzzy_match(word: str, candidates: list, threshold: float = 0.75) -> str:
    """Return best matching candidate if similarity >= threshold."""
    word = word.lower().strip()
    if len(word) < 3:
        return None
    best, best_score = None, 0
    for c in candidates:
        cl = c.lower()
        if abs(len(word) - len(cl)) > 4:
            continue
        # Character overlap score
        matches = sum(a == b for a, b in zip(word, cl))
        score = matches / max(len(word), len(cl))
        # Bonus if word starts with same letters
        if word[:3] == cl[:3]:
            score += 0.1
        if score > best_score:
            best_score, best = score, c
    return best if best_score >= threshold else None

def get_symptom_info(user_text: str) -> str:
    _load()
    text_lower = user_text.lower().strip()
    # Normalise spaces and punctuation
    text_lower = re.sub(r'[^\w\s]', ' ', text_lower)
    text_lower = re.sub(r'\s+', ' ', text_lower).strip()

    matched_keys = []

    # Pass 1: EXACT phrase match — longest keys first to avoid partial matches
    # e.g. "eye pain" should match "eye pain" not "ear pain"
    for key in sorted(_data.keys(), key=len, reverse=True):
        if key in text_lower and key not in matched_keys:
            matched_keys.append(key)

    # Validate pass 1 matches — ensure matched key words are actually in user text
    # This prevents "ear pain" matching when user typed "eye pain"
    validated = []
    for key in matched_keys:
        key_words = key.split()
        # All words of the key must appear in the text as whole words
        if all(re.search(r'\b' + re.escape(w) + r'\b', text_lower) for w in key_words):
            validated.append(key)
    matched_keys = validated

    # Pass 2: word-level exact match for multi-word symptoms not caught above
    if not matched_keys:
        for key in sorted(_data.keys(), key=len, reverse=True):
            words = key.split()
            if len(words) > 1:
                if all(re.search(r'\b' + re.escape(w) + r'\b', text_lower) for w in words):
                    if key not in matched_keys:
                        matched_keys.append(key)

    # Pass 3: fuzzy match on individual words in user text
    if not matched_keys:
        user_words = text_lower.split()
        all_keys = list(_data.keys())

        # Try each user word against all symptom keys
        for word in user_words:
            if len(word) < 4:
                continue
            # Direct substring
            for key in all_keys:
                if word in key or key in word:
                    if abs(len(word) - len(key)) <= 4 and key not in matched_keys:
                        matched_keys.append(key)
                        break
            # Fuzzy
            if not matched_keys:
                match = _fuzzy_match(word, all_keys, threshold=0.72)
                if match and match not in matched_keys:
                    matched_keys.append(match)

        # Try two-word combos
        if not matched_keys and len(user_words) >= 2:
            for i in range(len(user_words) - 1):
                combo = user_words[i] + " " + user_words[i+1]
                match = _fuzzy_match(combo, all_keys, threshold=0.75)
                if match and match not in matched_keys:
                    matched_keys.append(match)

    if not matched_keys:
        return None

    # Deduplicate and limit
    seen = set()
    unique_keys = []
    for k in matched_keys:
        entry = json.dumps(_data[k], sort_keys=True)
        if entry not in seen:
            seen.add(entry)
            unique_keys.append(k)
    matched_keys = unique_keys[:3]

    parts = []
    for key in matched_keys:
        info = _data[key]
        sev = info.get("severity", "mild")
        sev_emoji = {"high": "🔴", "moderate": "🟡", "mild": "🟢"}.get(sev, "⚪")

        conditions_str = ", ".join(info.get("conditions", []))
        otc = info.get("otc", [])
        advice = info.get("advice", "")

        block = f"### {sev_emoji} {key.title()}\n"
        block += f"**Possible causes:** {conditions_str}\n\n"
        if otc:
            block += f"**OTC options:** {', '.join(otc)}\n\n"
        else:
            block += "**⚠️ Requires doctor prescription** — no OTC options.\n\n"
        block += f"**Advice:** {advice}"
        parts.append(block)

    if len(matched_keys) == 1:
        header = f"## Symptoms: **{matched_keys[0].title()}**\n\n---\n\n"
    else:
        header = f"## Symptoms: **{', '.join(k.title() for k in matched_keys)}**\n\n---\n\n"

    result = header + "\n\n---\n\n".join(parts)

    for key in matched_keys:
        if _data[key].get("severity") == "high":
            result += "\n\n> 🔴 **One or more symptoms are HIGH SEVERITY — please see a doctor promptly.**"
            break

    return result + SAFETY_DISCLAIMER