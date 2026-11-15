# Pennsylvania statewide official-source audit — checked 2026-11-14

**PA DEP / Commonwealth of Pennsylvania official sources**

| Topic | Source | What it establishes | What it does NOT establish |
|---|---|---|---|
| Statewide Act 101 overview and local guidance | https://www.pa.gov/agencies/dep/residents/recycling-and-disposal | Act 101; statewide recycling program structure; DEP instructs residents to find and follow local program requirements | A uniform accepted-item list for every residential recycling bin |
| Statewide recycling program reporting | https://www.pa.gov/agencies/dep/programs-and-services/waste-programs/recycling-in-pennsylvania/statewide-recycling-data | Some municipalities are mandated to run recycling programs; program data reported by local governments | That every PA municipality accepts the same paper, glass, metal, plastic materials |
| Recycling coordinators | https://www.pa.gov/agencies/dep/programs-and-services/waste-programs/recycling-in-pennsylvania/public-recycling-resources/county-recycling-coordinators | County coordinator is a resource for local recycling and collection questions | Item-by-item acceptance at a particular station |
| Commercial requirements | https://www.pa.gov/agencies/dep/programs-and-services/waste-programs/recycling-in-pennsylvania/commercial-resources | In mandated municipalities, covered establishments have specified recycling obligations, including office paper, corrugated paper, aluminum and leaf waste | An unconditional statewide residential curbside rule |
| Composting facilities/programs | https://www.pa.gov/agencies/dep/programs-and-services/waste-programs/recycling-in-pennsylvania/composting | Compost options and program/facility information exist in PA | That an unlabeled compost bin or a compostable-fork claim means acceptance |
| Covered electronics | https://www.pa.gov/agencies/dep/programs-and-services/waste-programs/recycling-in-pennsylvania/electronics-recycling | Consumer covered-device recycling requirements and specialized programs | That electronics belong in an ordinary three-bin waste station |
| Household batteries | https://www.pa.gov/agencies/dep/programs-and-services/waste-programs/recycling-in-pennsylvania/public-recycling-resources/household-battery-recycling | Battery chemistries have different disposal and recycling rules; lithium-ion safety precautions | All batteries safely go in ordinary trash/recycling bins |
| Household hazardous waste | https://www.pa.gov/agencies/dep/programs-and-services/waste-programs/solid-waste-programs/hazardous-waste-program/household | Collection programs and safety/handling context | That every paint/chemical can should automatically receive the same bin recommendation |

## Source policy

`rules/locations/PA_STATEWIDE.json` intentionally contains **advisories only**. Each advisory carries an official source and checked date. An advisory returns `UNKNOWN` with a useful explanation, not an artificial `RECYCLE` / `COMPOST` / `LANDFILL` assignment. The file does not assert that PA DEP endorses the project.

**Before marking a local rule verified:** inspect the actual published rule, confirm exact accepted item AND preparation instructions AND category of premises (residential vs commercial) AND that the collection program is active at the physical station. Save source URL, date checked and a short evidence note. If the source is ambiguous, keep `UNKNOWN`.
