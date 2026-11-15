# Suggested two-minute pitch (revise to match demonstrated features)

**Hook (0:00–0:20)**

"You have a plastic cup in your hand. It looks recyclable, but does your recycling program actually take it? A camera alone cannot answer that question."

**Solution (0:20–0:40)**

"We built a waste-sorting assistant for Pennsylvania. Our camera recognizes the item, a separate policy engine checks documented disposal guidance, and a Raspberry Pi Pico shows the recommendation on a physical station."

**Demo (0:40–1:15)**

"Here's an aluminum can. Our system recognizes it, but Pennsylvania recycling programs vary by municipality, so it points to official state guidance instead of pretending every local bin accepts it. We can also test the physical sorting hardware using clearly labeled practice rules. Watch the recycle, compost, and landfill indicators respond."

**Differentiator (1:15–1:40)**

"What matters isn't just making a prediction—it's knowing when not to. If we scan a battery, covered electronic, or unclear wrapper, the system asks for clarification or points to a special collection program. Every state advisory includes an official source so someone can verify it."

**Evidence / close (1:40–2:00)**

"Our design separates recognition, local waste policy, and the physical interface. That makes it possible to add verified collection-program profiles across Pennsylvania without training a new image model for each city. [Insert only actual test results here.] The goal is a system people can trust not to guess."

## Devpost description (draft)

**Pennsylvania Smart Waste Assistant — source-backed guidance and an honest unknown state.**

Waste disposal is not just a visual recognition problem: the right destination depends on material, preparation, and local collection rules. Our prototype separates the task into image recognition, a Pennsylvania DEP–backed guidance layer, and a Raspberry Pi Pico indicator. Statewide advice is presented with source links. A definitive bin recommendation is only permitted when the relevant collection program and item conditions have been verified; otherwise the assistant asks the user to check local rules or packaging. In an explicitly labeled demonstration mode, the three physical bin indicators show the full hardware workflow. We designed the project to be extended with verified municipal and hauler profiles across Pennsylvania.

**Do not include invented accuracy percentages, waste saved, or live program coverage.** Use actual measured results. If a feature fails by submission, say it is unfinished.
