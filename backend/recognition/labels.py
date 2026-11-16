
LABELS = {
    "plastic water bottle": "plastic",
    "plastic food container": "plastic",
    "plastic bag": "plastic",
    "aluminum beverage can": "metal",
    "metal food can": "metal",
    "glass bottle": "glass",
    "glass jar": "glass",
    "cardboard box": "cardboard",
    "office paper": "paper",
    "newspaper": "paper",
    "banana peel": "organic",
    "apple core": "organic",
    "leftover food scraps": "organic",
    "plastic snack wrapper": "plastic",
    "disposable coffee cup": "unknown",
    "styrofoam container": "foam",
    "plastic fork or spoon": "plastic",
    "paper napkin": "paper",
    "greasy pizza box": "cardboard",
    "unrecognized object": "unknown",
    "empty background": "unknown"
}

AMBIGUOUS_ITEMS = {
    "disposable coffee cup":
        "Does the cup have a compostable label?",

    "plastic food container":
        "Check the material and recycling label.",

    "plastic water bottle":
        "Is the bottle empty?",

    "plastic snack wrapper":
        "Check the packaging material.",

    "plastic fork or spoon":
        "Is the utensil certified compostable?",

    "greasy pizza box":
        "Is the cardboard contaminated with food?"
}


CLARIFICATION_METADATA = {
    "plastic water bottle": {
        "clarification_type": "condition",
        "required_attributes": ["empty"]
    },

    "disposable coffee cup": {
        "clarification_type": "material",
        "required_attributes": []
    },

    "plastic food container": {
        "clarification_type": "material",
        "required_attributes": []
    },

    "plastic snack wrapper": {
        "clarification_type": "material",
        "required_attributes": []
    },

    "plastic fork or spoon": {
        "clarification_type": "material",
        "required_attributes": []
    },

    "greasy pizza box": {
        "clarification_type": "condition",
        "required_attributes": ["food_soiled"]
    }
}



MATERIAL_PROMPTS = {
    "plastic": [
        "plastic packaging",
        "discarded plastic material",
        "a plastic bottle or container"
    ],
    "glass": [
        "glass waste",
        "a glass bottle or jar",
        "discarded glass material"
    ],
    "metal": [
        "metal waste",
        "an aluminum or steel can",
        "discarded metallic material"
    ],
    "paper": [
        "discarded paper",
        "a sheet of paper or newspaper",
        "paper waste"
    ],
    "cardboard": [
        "corrugated cardboard",
        "a discarded cardboard box",
        "brown cardboard packaging"
    ],
    "organic": [
        "food waste",
        "fruit and vegetable scraps",
        "discarded organic food"
    ],
    "unknown": [
        "mixed miscellaneous garbage",
        "an unidentified object",
        "an empty surface"
    ]
}

