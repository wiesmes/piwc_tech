class MockProvider:
    def recognize(self, image_bytes, hint=None):
        if hint:
            return {"item": hint, "material": None, "needs_clarification": False, "question": None}
        return {"item": None, "material": None, "needs_clarification": True,
                "question": "What item is shown, and what material is its packaging made of?"}
