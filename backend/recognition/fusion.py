EXPECTED_MATERIALS = {
    "plastic water bottle": {"plastic"},
    "plastic beverage bottle": {"plastic"},
    "plastic food container": {"plastic"},
    "plastic bag": {"plastic"},
    "aluminum beverage can": {"metal"},
    "metal food can": {"metal"},
    "glass bottle": {"glass"},
    "glass jar": {"glass"},
    "cardboard box": {"cardboard"},
    "sheet of paper": {"paper"},
    "newspaper": {"paper"},
    "paper napkin": {"paper"},
    "paper towel": {"paper"},
    "banana peel": {"organic"},
    "apple core": {"organic"},
    "food scraps": {"organic"},
    "leftover salad": {"organic"},
    "plastic snack wrapper": {"plastic", "composite"},
    "biscuit wrapper": {"plastic", "composite"},
    "candy wrapper": {"plastic", "composite"},
    "rubber band": {"rubber"},
    "rubber object": {"rubber"},
    "rubber glove": {"rubber"},
    "styrofoam container": {"plastic", "foam", "styrofoam"},
    "plastic utensils": {"plastic"},
    "pizza box": {"cardboard"},
    "disposable coffee cup": {"paper", "plastic", "composite"}
}

ITEM_GROUPS = [
    {
        "plastic water bottle",
        "plastic beverage bottle"
    },
    {
        "leftover salad",
        "food scraps",
        "leftover food scraps"
    },
    {
        "sheet of paper",
        "office paper"
    },
    {
        "plastic snack wrapper",
        "biscuit wrapper",
        "candy wrapper"
    },
    {
        "aluminum beverage can",
        "metal beverage can",
        "soda can"
    }
]


def normalize(value):
    return str(value or "").strip().lower()


def items_agree(item1, item2):
    item1 = normalize(item1)
    item2 = normalize(item2)

    if item1 == item2:
        return True

    return any(
        item1 in group and item2 in group
        for group in ITEM_GROUPS
    )


def fuse_predictions(detection, classification):
    result = classification.copy()

    detector_item = normalize(detection["detected_item"])
    clip_item = normalize(result["item"])
    clip_material = normalize(result["material"])

    expected = EXPECTED_MATERIALS.get(detector_item)

    result["clip_item"] = clip_item
    result["clip_material"] = clip_material
    result["material_agreement"] = None

    result["item_agreement"] = items_agree(
        detector_item, clip_item
    )

    result["fusion_status"] = "unverified"

    if expected is None:
        result["material"] = "unknown"
        result["needs_clarification"] = True
        result["question"] = (
            "Please identify the item and confirm its material."
        )

    elif clip_material not in expected:
        result["material_agreement"] = False
        result["fusion_status"] = "model_disagreement"
        result["material"] = "unknown"
        result["suggested_item"] = detector_item
        result["needs_clarification"] = True

        result["question"] = (
            f"Is this a {detector_item}? "
            "Please confirm its material."
        )

    elif not result["item_agreement"]:
        result["material_agreement"] = True
        result["fusion_status"] = "item_disagreement"
        result["suggested_item"] = detector_item
        result["needs_clarification"] = True

        result["question"] = (
            f"Is this a {detector_item}? "
            "Please confirm the item."
        )

    else:
        result["material_agreement"] = True
        result["fusion_status"] = "material_agreement"

    return result
