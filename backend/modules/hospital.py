import httpx
import re
from typing import Optional

REPUTED_CHAINS = [
    "apollo", "fortis", "miot", "kauvery", "rela", "mgm", "sims", "vijaya",
    "gleneagles", "global hospital", "manipal", "max", "medanta", "narayana",
    "aster", "columbia", "kokilaben", "lilavati", "hinduja", "breach candy",
    "christian medical", "vellore", "cmch", "aiims", "pgimer", "nimhans",
    "sankara", "shankar netralaya", "aravind", "rainbow", "kims", "yashoda",
    "care hospital", "sunshine", "star hospital", "continental", "omni",
    "prashanth", "kamakshi", "madras medical mission", "voluntary health",
    "vhs", "srm", "saveetha", "chettinad", "stanley", "rajiv gandhi",
    "government general", "esic", "district hospital", "government hospital",
    "taluk hospital", "primary health", "community health",
]

SPECIALTY_TRIGGERS = {
    "eye": [
        "eye hospital", "eye hospitals", "eye clinic", "eye clinics",
        "eye doctor", "eye doctors", "eye specialist", "eye specialists",
        "ophthalmologist", "ophthalmology", "opthamologist", "opthamology",
        "retina specialist", "cataract", "glaucoma specialist",
        "visit an eye", "visit eye", "eye problem", "eye issue",
    ],
    "skin": [
        "skin clinic", "skin clinics", "skin hospital", "skin doctor",
        "skin specialist", "dermatologist", "dermatology",
        "hair clinic", "hair loss clinic", "hair doctor", "trichologist",
        "trichology", "hair transplant clinic",
    ],
    "gynec": [
        "gynec", "gynaec", "gynecologist", "gynaecologist", "obgyn",
        "ob gyn", "obstetrics", "maternity hospital", "maternity clinic",
        "women hospital", "women's hospital", "ladies hospital",
        "pregnancy hospital", "fertility clinic", "ivf clinic", "ivf",
    ],
    "ent": [
        "ent", "ent doctor", "ent specialist", "ent clinic",
        "ear nose throat", "ear doctor", "ear specialist",
        "nose doctor", "throat specialist", "tonsil", "sinus specialist",
        "hearing clinic", "audiologist",
    ],
    "ortho": [
        "orthopedic", "orthopaedic", "orthopedist", "orthopaedist",
        "bone doctor", "bone specialist", "joint specialist",
        "joint replacement", "spine specialist", "fracture specialist",
    ],
    "cardio": [
        "cardiologist", "cardiology", "heart hospital", "heart clinic",
        "heart specialist", "heart doctor", "cardiac clinic",
    ],
    "neuro": [
        "neurologist", "neurology", "brain specialist", "brain doctor",
        "neuro hospital", "neuro clinic", "epilepsy doctor",
    ],
    "dental": [
        "dental", "dentist", "dental clinic", "dental hospital",
        "teeth doctor", "oral surgeon", "oral surgery",
    ],
    "child": [
        "pediatrician", "paediatrician", "pediatric", "paediatric",
        "children hospital", "children's hospital", "child specialist",
        "kids doctor", "kids hospital", "baby doctor",
    ],
    "cancer": [
        "cancer hospital", "cancer clinic", "oncologist", "oncology",
        "cancer treatment", "tumor specialist",
    ],
    "kidney": [
        "nephrologist", "nephrology", "kidney specialist", "kidney doctor",
        "dialysis center", "dialysis centre", "urologist", "urology",
    ],
    "diabetes": [
        "diabetologist", "diabetes specialist", "diabetes clinic",
        "endocrinologist", "endocrinology", "thyroid specialist",
    ],
    "mental": [
        "psychiatrist", "psychiatry", "mental health", "psychologist",
        "rehab center", "rehabilitation center", "deaddiction",
    ],
    "physio": [
        "physiotherapist", "physiotherapy", "physio clinic",
    ],
}

# Keywords in facility NAME → single specialty
SPECIALTY_NAME_KW = {
    "eye":     ["eye care", "eye clinic", "eye hospital", "eye centre", "eye center",
                "netralaya", "ophthalm", "opthalm", "retina centre", "vision care"],
    "skin":    ["skin clinic", "skin care", "dermatol", "hair transplant",
                "trichol", "cosmetol"],
    "gynec":   ["maternity", "fertility clinic", "ivf", "prenatal", "ladies hospital",
                "women hospital", "gynec", "gynaec"],
    "dental":  ["dental clinic", "dental care", "dental hospital", "dentist"],
    "physio":  ["physiotherapy clinic", "physio centre"],
    "dialysis":["dialysis centre", "dialysis center"],
    "deaddiction": ["deaddiction", "de-addiction"],
    "hearing": ["hearing clinic", "audiolog"],
}

GENERAL_SAVERS = [
    "multispeciality", "multi speciality", "multi-speciality",
    "super speciality", "super-speciality",
    "hospital", "medical center", "medical centre",
    "nursing home", "health center", "health centre",
    "medical college", "healthcare",
]

QUERY_NOISE = [
    "hospitals in", "hospitals near", "hospital in", "hospital near",
    "clinics in", "clinics near", "clinic in", "clinic near",
    "pharmacy in", "pharmacies in", "pharmacy near", "pharmacies near",
    "chemist in", "chemist near",
    "doctors in", "doctor in", "doctors near", "doctor near",
    "find hospitals", "find hospital", "find pharmacy",
    "list hospitals", "list clinics", "list pharmacies",
    "show hospitals", "show clinics",
    "i need to visit an", "i need to visit", "i want to visit",
    "i need a", "i need",
    "list them in", "list in",
]


def detect_specialty(text: str) -> Optional[str]:
    t = text.lower()
    for specialty, triggers in SPECIALTY_TRIGGERS.items():
        for trigger in sorted(triggers, key=len, reverse=True):
            if trigger in t:
                return specialty
    return None


def extract_location_from_text(text: str) -> str:
    """Strip ALL specialty triggers + query noise, return leftover as location."""
    t = text.lower().strip()

    # Strip specialty triggers (longest first)
    all_triggers = []
    for triggers in SPECIALTY_TRIGGERS.values():
        all_triggers.extend(triggers)
    for trigger in sorted(all_triggers, key=len, reverse=True):
        t = t.replace(trigger, " ")

    # Strip query noise (longest first)
    for noise in sorted(QUERY_NOISE, key=len, reverse=True):
        t = re.sub(r'\b' + re.escape(noise) + r'\b', ' ', t)

    # Strip pincodes, punctuation
    t = re.sub(r'\b\d{6}\b', '', t)
    t = re.sub(r'[?!.,]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t.title() if len(t) >= 3 else ""


async def geocode_area(area: str) -> Optional[tuple]:
    """
    Geocode an area/locality name in India.
    Returns (lat, lon, clean_label) or None.
    Specifically requests suburb/neighbourhood types to avoid getting buildings.
    """
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "HealthBotIndia/2.0"}

    attempts = [
        # Most specific first — request suburb type explicitly
        {"q": f"{area}, Chennai, India", "featuretype": "settlement"},
        {"q": f"{area}, Tamil Nadu, India"},
        {"q": f"{area}, India"},
    ]

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            for params_extra in attempts:
                params = {
                    "format": "json",
                    "limit": 5,
                    "countrycodes": "in",
                    "addressdetails": 1,
                    **params_extra
                }
                resp = await client.get(url, params=params, headers=headers)
                results = resp.json()
                if not results:
                    continue

                # Prefer results whose type is a place type, not a building/amenity
                GOOD_TYPES = {"suburb", "neighbourhood", "quarter", "village",
                              "town", "city_district", "residential", "locality",
                              "hamlet", "district", "county", "municipality"}
                BAD_CLASSES = {"amenity", "building", "shop", "office"}

                for r in results:
                    rtype = r.get("type", "")
                    rclass = r.get("class", "")
                    if rclass in BAD_CLASSES:
                        continue
                    lat = float(r["lat"])
                    lon = float(r["lon"])
                    label = _label_from_address(r.get("address", {}), area)
                    return lat, lon, label

                # All results were bad class — use first result but extract label from address
                r = results[0]
                lat = float(r["lat"])
                lon = float(r["lon"])
                label = _label_from_address(r.get("address", {}), area)
                return lat, lon, label

    except Exception:
        pass
    return None


async def geocode_pincode(pincode: str) -> Optional[tuple]:
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "HealthBotIndia/2.0"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"q": f"{pincode}, India", "format": "json",
                      "limit": 1, "countrycodes": "in", "addressdetails": 1}
            resp = await client.get(url, params=params, headers=headers)
            results = resp.json()
            if results:
                r = results[0]
                lat = float(r["lat"])
                lon = float(r["lon"])
                label = _label_from_address(r.get("address", {}), pincode)
                return lat, lon, label
    except Exception:
        pass
    return None


def _label_from_address(address: dict, fallback: str) -> str:
    """
    Extract a clean human-readable label from Nominatim addressdetails.
    Use suburb/neighbourhood first — skip admin zones like 'Zone 10'.
    """
    city = address.get("city") or address.get("town") or ""

    # Best: suburb or neighbourhood (most specific local name)
    for key in ["suburb", "neighbourhood", "quarter"]:
        val = address.get(key, "")
        if val and not val.isdigit() and not val.lower().startswith("zone"):
            if city and city.lower() != val.lower():
                return f"{val}, {city}"
            return val

    # If fallback looks like a real place name (not a pincode), use it + city
    if fallback and not fallback.isdigit() and len(fallback) > 2:
        if city and city.lower() not in fallback.lower():
            return f"{fallback}, {city}" if city else fallback
        return fallback

    # Last resort
    if city:
        return city
    return fallback


def _passes_filter(name: str, specialty: Optional[str]) -> bool:
    name_lower = name.lower()

    if specialty:
        # Specialty search: ONLY show facilities whose name explicitly matches
        sp_kws = SPECIALTY_NAME_KW.get(specialty, [])
        trigger_kws = [t for t in SPECIALTY_TRIGGERS.get(specialty, []) if len(t) > 4]
        return (any(kw in name_lower for kw in sp_kws) or
                any(kw in name_lower for kw in trigger_kws))

    # General search — exclude single-specialty non-hospitals
    has_general_saver = any(s in name_lower for s in GENERAL_SAVERS)
    if has_general_saver:
        return True

    # Check against all single-specialty keyword groups
    for sp, kws in SPECIALTY_NAME_KW.items():
        if any(kw in name_lower for kw in kws):
            return False

    return True


async def _query_overpass(query: str) -> list:
    try:
        async with httpx.AsyncClient(timeout=22.0) as client:
            resp = await client.post("https://overpass-api.de/api/interpreter",
                                     data={"data": query})
            return resp.json().get("elements", [])
    except Exception:
        return []


def _extract_coords(el, fb_lat, fb_lon):
    if el.get("type") == "way":
        c = el.get("center", {})
        return c.get("lat", fb_lat), c.get("lon", fb_lon)
    return el.get("lat", fb_lat), el.get("lon", fb_lon)


def _maps_link(name: str, lat: float, lon: float) -> str:
    """
    Google Maps link using name + lat/lon in query.
    Searching 'HospitalName lat,lon' opens that exact place — not a global search.
    """
    import urllib.parse
    query = f"{name} {lat},{lon}"
    encoded = urllib.parse.quote(query)
    return f"https://www.google.com/maps/search/?api=1&query={encoded}"


def _score_hospital(name: str, tags: dict) -> int:
    score = 0
    name_lower = name.lower()
    if any(c in name_lower for c in REPUTED_CHAINS):
        score += 10
    if tags.get("emergency") == "yes":
        score += 5
    if tags.get("beds"):
        try:
            score += min(int(tags["beds"]) // 50, 5)
        except Exception:
            score += 1
    if tags.get("phone") or tags.get("contact:phone"):
        score += 2
    if tags.get("website"):
        score += 1
    if any(kw in name_lower for kw in ["multispeciality", "super speciality",
                                        "medical center", "institute"]):
        score += 2
    return score


async def resolve_location(text: str, pincode: str = None) -> Optional[tuple]:
    if pincode:
        result = await geocode_pincode(pincode)
        if result:
            return result

    area = extract_location_from_text(text)
    if area and len(area) >= 3:
        result = await geocode_area(area)
        if result:
            return result

    return None


async def find_hospitals(pincode: str = None, specialty: Optional[str] = None,
                         raw_text: str = "") -> dict:
    loc = await resolve_location(raw_text, pincode)
    if not loc:
        return {
            "found": False,
            "message": (
                "❌ **Could not find that location.**\n\n"
                "Try:\n"
                "- *\"hospitals in vadapalani\"*\n"
                "- *\"eye hospital in kodambakkam\"*\n"
                "- *\"dermatologist in t nagar\"*\n"
                "- *\"hospitals near 600024\"*"
            )
        }

    lat, lon, area_label = loc

    query = f"""
[out:json][timeout:25];
(
  node["amenity"="hospital"](around:5000,{lat},{lon});
  way["amenity"="hospital"](around:5000,{lat},{lon});
  relation["amenity"="hospital"](around:5000,{lat},{lon});
  node["amenity"="clinic"](around:4000,{lat},{lon});
  way["amenity"="clinic"](around:4000,{lat},{lon});
  node["healthcare"="hospital"](around:5000,{lat},{lon});
  node["healthcare"="clinic"](around:4000,{lat},{lon});
);
out center 40;
"""
    elements = await _query_overpass(query)

    seen = set()
    facilities = []
    for el in elements:
        tags = el.get("tags", {})
        name = (tags.get("name") or tags.get("name:en") or
                tags.get("operator") or None)
        if not name or len(name.strip()) < 3 or name in seen:
            continue
        seen.add(name)
        if not _passes_filter(name, specialty):
            continue
        el_lat, el_lon = _extract_coords(el, lat, lon)
        facilities.append({
            "name": name.strip(),
            "emergency": tags.get("emergency", ""),
            "beds": tags.get("beds", ""),
            "maps_link": _maps_link(name, el_lat, el_lon),
            "score": _score_hospital(name, tags),
            "reputed": any(c in name.lower() for c in REPUTED_CHAINS),
        })

    facilities.sort(key=lambda x: (x["reputed"], x["score"]), reverse=True)
    facilities = facilities[:10]

    specialty_label = f" — {specialty.title()} Specialists" if specialty else ""
    header = f"## 🏥 Hospitals in {area_label}{specialty_label}"

    if not facilities:
        q = f"{specialty}+hospital" if specialty else "hospital"
        return {
            "found": False,
            "message": (
                f"{header}\n\n"
                f"No results found in map data for this area.\n\n"
                f"📍 [Search on Google Maps]"
                f"(https://www.google.com/maps/search/{q}+near+"
                f"{area_label.replace(' ', '+')})"
            )
        }

    lines = [f"{header}\n\n---\n"]
    for i, h in enumerate(facilities, 1):
        badge = " ⭐" if h["reputed"] else ""
        extras = []
        if h["emergency"] == "yes":
            extras.append("🚨 24hr Emergency")
        if h["beds"]:
            extras.append(f"🛏️ {h['beds']} beds")
        extras_str = "  ·  " + "  ·  ".join(extras) if extras else ""
        lines.append(
            f"**{i}. {h['name']}{badge}**{extras_str}\n"
            f"   📍 [Open in Google Maps]({h['maps_link']})\n"
        )

    return {"found": True, "message": "\n".join(lines)}


async def find_pharmacies(pincode: str = None, raw_text: str = "") -> dict:
    loc = await resolve_location(raw_text, pincode)
    if not loc:
        return {
            "found": False,
            "message": (
                "❌ **Could not find that location.**\n\n"
                "Try: *\"pharmacy in anna nagar\"* or *\"pharmacy near 600040\"*"
            )
        }

    lat, lon, area_label = loc

    query = f"""
[out:json][timeout:15];
(
  node["amenity"="pharmacy"](around:3000,{lat},{lon});
  way["amenity"="pharmacy"](around:3000,{lat},{lon});
  node["shop"="chemist"](around:3000,{lat},{lon});
  node["amenity"="chemist"](around:3000,{lat},{lon});
  node["healthcare"="pharmacy"](around:3000,{lat},{lon});
);
out center 25;
"""
    elements = await _query_overpass(query)

    PHARMA_CHAINS = ["apollo pharmacy", "medplus", "netmeds", "wellness forever",
                     "guardian pharmacy", "frank ross", "jan aushadhi", "noble pharmacy"]

    seen = set()
    pharmacies = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("operator") or None
        if not name or name in seen:
            continue
        seen.add(name)
        el_lat, el_lon = _extract_coords(el, lat, lon)
        hours = tags.get("opening_hours", "")
        is_chain = any(c in name.lower() for c in PHARMA_CHAINS)
        pharmacies.append({
            "name": name,
            "hours": hours,
            "maps_link": _maps_link(name, el_lat, el_lon),
            "is_chain": is_chain,
            "score": (5 if is_chain else 0) + (2 if hours else 0),
        })

    pharmacies.sort(key=lambda x: (x["is_chain"], x["score"]), reverse=True)
    pharmacies = pharmacies[:10]

    header = f"## 💊 Pharmacies in {area_label}"

    if not pharmacies:
        return {
            "found": False,
            "message": (
                f"{header}\n\nNo pharmacies found within 3km.\n\n"
                f"📍 [Search on Google Maps]"
                f"(https://www.google.com/maps/search/pharmacy+near+"
                f"{area_label.replace(' ', '+')})"
            )
        }

    lines = [f"{header}\n\n---\n"]
    for i, p in enumerate(pharmacies, 1):
        badge = " ⭐" if p["is_chain"] else ""
        hours_str = f"\n   🕐 {p['hours']}" if p['hours'] else ""
        lines.append(
            f"**{i}. {p['name']}{badge}**{hours_str}\n"
            f"   📍 [Open in Google Maps]({p['maps_link']})\n"
        )

    return {"found": True, "message": "\n".join(lines)}