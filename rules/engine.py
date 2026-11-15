from __future__ import annotations

RULES = {
    "aluminum can": {"bin": "RECYCLE", "message": "Aluminum cans are accepted in recycling in most local programs.", "rule_id": "demo-aluminum-can", "source_url": "https://www.epa.gov/recycle/recycling-basics", "demo": True},
    "glass bottle": {"bin": "RECYCLE", "message": "Glass bottles are generally recyclable when empty and rinsed.", "rule_id": "demo-glass-bottle", "source_url": "https://www.epa.gov/recycle/recycling-basics", "demo": True},
    "coffee cup": {"bin": "LANDFILL", "message": "Many coffee cups are lined and cannot be recycled in standard collection streams.", "rule_id": "demo-coffee-cup", "source_url": "https://www.epa.gov/recycle/recycling-basics", "demo": True},
    "pizza box": {"bin": "COMPOST", "message": "Food-soiled cardboard can often be composted or handled as dry organics instead of landfill.", "rule_id": "demo-pizza-box", "source_url": "https://www.epa.gov/recycle/recycling-basics", "demo": True},
    "banana peel": {"bin": "COMPOST", "message": "Banana peels are compostable organic matter.", "rule_id": "demo-banana-peel", "source_url": "https://www.epa.gov/recycle/recycling-basics", "demo": True},
}


def recommend(item, location):
    normalized_location = (location or '').strip().upper()
    if not normalized_location or normalized_location == 'UNCONFIGURED':
        return {
            "bin": "UNKNOWN",
            "message": "No verified local disposal rule is configured for this item in the current location.",
            "rule_id": None,
            "source_url": None,
            "demo": True,
        }

    name = (item or '').strip().lower()
    if not name:
        return {"bin": "UNKNOWN", "message": "No item was recognized. Please confirm the object before sorting.", "rule_id": None, "source_url": None, "demo": True}

    rule = RULES.get(name)
    if rule:
        return dict(rule)

    return {"bin": "UNKNOWN", "message": "No verified disposal rule exists for this item and location.", "rule_id": None, "source_url": None, "demo": True}
