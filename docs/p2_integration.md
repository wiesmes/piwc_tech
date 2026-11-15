# P2 + P4 compatibility: contract and merge instructions

**Project target: Pennsylvania, USA (`PA_STATEWIDE`), NOT Princeton University.** The original document is named Princeton.docx, but its campus-specific proposal is not our chosen deployment scope. Fix the P2 markdown references to "Princeton official rules" before submitting documentation.

## Current compatibility assessment

The P2 attachment documents the recognition outputs and model behavior; it is **not** the actual `classifier.py`, `multi_classifier.py`, or merged FastAPI source. The adapter below is tested against its *documented payloads* only; live P2 implementation and real Pico integration still require verification.

- P2 single-object fields `item`, `material`, `needs_clarification`, `question` fit the original `decide(...)` interface.
- P2 multi-object dict (`object_count`, `objects`) CANNOT be sent directly to `decide` because it lacks a top-level `item` and it describes several different objects.
- The prior core `decide` did not independently check `material == 'unknown'`, `material_agreement`, `prediction_agreement`, or `fusion_status`. Those checks now live in `rules/p2_adapter.py`. **P3 must use the adapter** when calling P4 from P2.
- Internal bin codes agree: `RECYCLE`, `COMPOST`, `LANDFILL`, `UNKNOWN`. The engine never allows recognition models to pick a bin directly.
- Both P2's reported runtimes and P4's policy tests are provisional; inference performance on Raspberry Pi 5 remains untested.

## Code P3 should call

```python
from rules.p2_adapter import process_recognition
from backend.recognition.classifier import recognize

ai_result = recognize(image)   # accepts image file path or PIL Image
p4_result = process_recognition(ai_result, location='PA_STATEWIDE')
# p4_result['objects'][0] contains the detailed decision
# p4_result['bin'] is safe to dispatch to the Pico for a single item
```

For multi-object mode:

```python
from backend.recognition.multi_classifier import recognize_multiple
from rules.p2_adapter import process_recognition

ai_result = recognize_multiple(image)
p4_result = process_recognition(ai_result, location='PA_STATEWIDE')
for d in p4_result['objects']:
    print(d['object_id'], d['item'], d['bin'], d['question'])

# DO NOT send p4_result['bin'] as one collective disposal answer when >1 item.
# Show item-specific results, let user select one object and then send that
# selected object's bin command with corresponding item name to the Pico.
# Object IDs are temporary; clear selection and user attributes on each image.
```

The P4 adapter returns:

```json
{
  "bin": "UNKNOWN",
  "message": "...",
  "object_count": 1,
  "multiple_items": false,
  "needs_clarification": true,
  "objects": [
    {
      "object_id": null,
      "item": "plastic water bottle",
      "material": "plastic",
      "bin": "UNKNOWN",
      "needs_clarification": true,
      "message": "...",
      "explanation": "...",
      "question": "...",
      "rule_id": "PA-RECY-002",
      "source_url": "https://www.pa.gov/agencies/dep/residents/recycling-and-disposal",
      "rule_checked_date": "2026-11-14"
    }
  ]
}
```

This sample assumes `needs_clarification=false` from P2. If P2 asks whether a bottle is empty, the adapter preserves the question and will not invent a source-backed bin decision.

## Condition questions need structured metadata from P2

Current P2 output uses a single ambiguous `needs_clarification=true` for BOTH uncertain identification and an otherwise recognized item requiring human checking. This cannot be safely resolved just by passing an `empty=True` flag while the same `needs_clarification` remains true. A user-confirmed condition must not wipe out independent recognition/model disagreements.

**Smallest recommended P2 enhancement:**

```json
{
  "item": "plastic water bottle",
  "material": "plastic",
  "needs_clarification": true,
  "question": "Is the bottle empty?",
  "clarification_type": "condition",
  "required_attributes": ["empty"]
}
```

P3 passes `attributes={'empty': True}` after the user explicitly confirms. The adapter then clears ONLY that condition gate and passes the case to Pennsylvania policy verification. Without a verified local program, the result is still `UNKNOWN`, which is correct. For unclear identity/material, P2 should use `clarification_type='identity'` or `'material'`, and the adapter will continue to require rescan or a reliable recognition update. Never automatically clear uncertainty because the user answered a different question.

For multiple objects, use `attributes_by_object={1:{'empty':True}, 2:{'clean':True}}` for only the current image. P2's raw `object_id` values should be unique positive integers within that image. P3 must not reuse them after the next capture.

## Important policy limitation

`PA_STATEWIDE` is a geographic scope, NOT one universal municipal curbside collection program. Pennsylvania DEP advisories support explanatory `UNKNOWN` responses. A real `RECYCLE/COMPOST/LANDFILL` bin requires a specifically verified `program_id`, `rules_path`, available stream, item-specific source and verified conditions. `DEMO_ONLY` can trigger all three lights, but P3 must prominently label it **DEMO ONLY — NOT VERIFIED**.

## Exact changes to coordinate by owner

- **P2:** Update references to Princeton -> Pennsylvania statewide; add `clarification_type` and `required_attributes` for condition-only questions. Make OWLv2 vs CLIP *item* identity disagreements explicit (not just material agreement). Give P4 the exact list of recognized item labels and material values, and run live output examples from both functions.
- **P3:** Import `process_recognition`, not raw `decide`; show one result card per detected item; don't dispatch a collective command for an image with multiple items; implement per-item confirmation; show `message`, source link and `rule_checked_date` as available, plus demonstration mode.
- **P4:** Keep PA DEP advisories, rules engine, and item test dataset. Add safe aliases only where the item category matches (e.g., `plastic snack wrapper` -> `snack wrapper`, `leftover salad` -> `food scraps`). Do not alias `metal food can` to `aluminum can`: metal cans can differ by material and local acceptance.
- **P1:** Keep existing serial protocol; drive only the active/selected object's bin. On any uncertainty, illuminate the `UNKNOWN` pattern. Still show hardware COM/ACK failures honestly.

## Run tests

At repository root, with P4 files merged into the team's existing folder (no nested repository):

```powershell
python -m unittest discover -s tests -v
python -c "from rules.p2_adapter import process_recognition; print(process_recognition({'item':'plastic water bottle','material':'plastic','needs_clarification':True,'question':'Is the bottle empty?'}))"
```

Tests here use synthetic examples and the documented P2 outputs, not the actual downloaded CLIP/OWLv2 weights.
