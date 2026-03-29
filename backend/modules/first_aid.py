import json
import os

_first_aid_data = None


def _load_data():
    global _first_aid_data
    if _first_aid_data is None:
        data_path = os.path.join(os.path.dirname(__file__), "../data/first_aid.json")
        with open(data_path, "r") as f:
            _first_aid_data = json.load(f)
    return _first_aid_data


def get_first_aid(topic: str) -> dict:
    data = _load_data()

    if not topic:
        topics_list = "\n".join([f"  • {t.replace('_', ' ').title()}" for t in data.keys()])
        return {
            "found": False,
            "message": f"Please specify a first aid topic. Available topics:\n{topics_list}"
        }

    topic_lower = topic.lower().strip()

    # Direct match
    if topic_lower in data:
        return _format_first_aid(data[topic_lower])

    # Partial match
    for key in data:
        if topic_lower in key or key in topic_lower:
            return _format_first_aid(data[key])

    # Word-level match
    for key in data:
        key_words = key.replace("_", " ").split()
        topic_words = topic_lower.split()
        if any(w in topic_words for w in key_words):
            return _format_first_aid(data[key])

    topics_list = "\n".join([f"  • {t.replace('_', ' ').title()}" for t in data.keys()])
    return {
        "found": False,
        "message": f"I don't have first aid information for **{topic}**. Available topics:\n{topics_list}"
    }


def _format_first_aid(info: dict) -> dict:
    steps_formatted = "\n".join([f"{i+1}. {step}" for i, step in enumerate(info["steps"])])

    severity = info.get("severity_note", "")
    severity_block = f"\n\n🚨 **{severity}**" if severity else ""

    response = (
        f"🩺 **{info['title']}**"
        f"{severity_block}\n\n"
        f"**Steps to Follow:**\n\n{steps_formatted}"
    )

    return {
        "found": True,
        "message": response,
        "data": info
    }
