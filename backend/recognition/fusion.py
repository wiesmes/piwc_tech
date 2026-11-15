EXPECTED_MATERIALS = {
    "plastic water bottle": {"plastic"},
    "plastic beverage bottle": {"plastic"},
    "plastic food container": {"plastic"},
    "plastic bag": {"plastic"},
    "styrofoam container": {"plastic", "styrofoam", "foam"},
    "plastic utensils": {"plastic"},
    "pizza box": {"cardboard"},
    "disposable coffee cup": {"paper", "plastic", "composite"},
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
    "rubber glove": {"rubber"}
    
}


def fuse_predictions(detection, classification):
    result = classification.copy()

    detector_item = detection["detected_item"]
    clip_item = result["item"]
    clip_material = result["material"]

    expected = EXPECTED_MATERIALS.get(detector_item)

    result["clip_item"] = clip_item
    result["clip_material"] = clip_material
    result["material_agreement"] = None
    result["fusion_status"] = "unverified"

    if expected is not None:
        agreement = clip_material in expected

        result["material_agreement"] = agreement

        if agreement:
            result["fusion_status"] = "material_agreement"

        else:
            result["suggested_item"] = detector_item
            result["material"] = "unknown"
            result["needs_clarification"] = True
            result["fusion_status"] = "model_disagreement"

            result["question"] = (
                f"Is this a {detector_item}? "
                "Please confirm its material."
            )
            # Unsupported detector labels require clarification.
    if expected is None:
        result["material"] = "unknown"
        result["needs_clarification"] = True
        result["question"] = (
            "Please identify the item and confirm its material."
        )

    # Preserve uncertain predictions as unknown.
    if (
        result["needs_clarification"]
        and result.get("prediction_agreement") is False
    ):
        result["material"] = "unknown"

    return result
