# P4 integration: Pennsylvania statewide

## Ownership and acceptance criteria

| Owner | What P4 provides | Integration checkpoint |
|---|---|---|
| P2 — camera and recognition | The 15-object photographed test set; exact names and aliases from `PA_STATEWIDE.json` | P2 returns `{item,material,needs_clarification,question}` without assigning a bin. Names align; low-confidence result triggers clarification. |
| P3 — backend and UI | `from rules.engine import decide`; result `{bin,message,rule_id,source_url}` | P3 displays full explanation, clickable PA DEP URL, and **PA STATEWIDE / LOCAL VERIFIED / DEMO ONLY** status; calls P1 with only `bin`. |
| P1 — Pico and wiring | Labels and physical bin layout; `RECYCLE` green, `COMPOST` yellow, `LANDFILL` red, `UNKNOWN` all blink | Four manual button states work; acknowledge return or show real connection error, not a false success. |
| P4 — rules, test, presentation | `PA_STATEWIDE.json` sources, working rules module, 15 cases, test log, bins, pitch | One complete photo → recognition → rules → UI → **real** Pico run; metrics based on observed trials. |

## Implementation examples

```python
from rules.engine import decide

# A real Pennsylvania-wide advisory: returns UNKNOWN if local collection not verified.
r = decide({'item':'aluminum can', 'material':'metal',
            'needs_clarification':False, 'question':None},
           location='PA_STATEWIDE')

# A deliberately synthetic end-to-end showcase: label UI clearly as DEMO ONLY.
r_demo = decide({'item':'practice can','material':'metal',
                 'needs_clarification':False,'question':None},
                location='DEMO_ONLY',demo_mode=True,
                attributes={'empty':True})

# An actual local Pennsylvania collection program can later be used when
# **human-verified** official item acceptance, source, and stream are available:
# r_local = decide(recognition, location='PA_STATEWIDE',
#                  program_id='verified_program_id',
#                  rules_path='rules/locations/verified_program.json',
#                  attributes={'empty': True})
```

## Important handoff questions to resolve with P3

1. Do we display statewide `UNKNOWN` advisories on screen with the actual official source link?
2. Can P3 render `rule_id` on the result card and a prominent `DEMO ONLY` label when in simulation?
3. Can P3 ask a one-tap clarification question such as **"Is the can empty?"** and pass `attributes={'empty': True}` only if a person confirms it?
4. Does P3 transmit the literal bin command to P1 for the LED test, with connection/acknowledgment checks?
5. Can the team visually separate **"item recognized"** from **"collection program verified"**?

## P4 safety gates

- No automatic real recycling decision from plastic resin code alone.
- No compost recommendation without a source-verified, currently available stream.
- No battery, covered electronic or HHW placed into any of the ordinary prototype bins.
- No demo-only synthetic result represented as official Pennsylvania policy.
- The app should never claim Pennsylvania as one uniform collection jurisdiction.

## P2 integration amendment (Nov 14)

**P3 should now call `rules.p2_adapter.process_recognition(...)` rather than direct `rules.engine.decide(...)` for model results.** This adapter supports both single and multi-object payloads. In multi-object mode with more than one detection it deliberately returns aggregate `bin=UNKNOWN` until P3 displays and selects an individual result. See `docs/p2_integration.md` for implementation details. P2 should add structured condition metadata for user confirmation (`clarification_type`, `required_attributes`) rather than relying on free-text questions. Princeton University is not the configured location.
