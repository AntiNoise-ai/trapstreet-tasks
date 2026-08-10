"""Generate filler_pool.json -- the bulk added at L4, to BOTH arms equally.

L4 exists to answer one objection: a null at 26 skills invites "26 is not a
stack". It adds ~100 skills from domains with no bearing on office work, so the
same overlap contrast is carried out at a catalog size nobody can dismiss.

Templated prose is acceptable HERE and would not be acceptable for the
low-overlap packs. The low-overlap packs are the control arm: if they read
thinner than the hand-written high-overlap packs, "the high arm was more
distracting" becomes a writing artifact. This filler goes into BOTH arms
identically, so it cannot create an asymmetry between them -- it can only add
bulk, which is exactly its job.

Run: python3 gen_filler.py   (committed output; rarely needed)
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Domains chosen to have no plausible bearing on an office-admin request.
DOMAINS = [
    ("kiln", "ceramics firing", "kiln", "firing chamber"),
    ("weir", "river flow regulation", "weir", "gate"),
    ("apiary", "beekeeping", "hive", "colony"),
    ("tannery", "leather processing", "drum", "hide batch"),
    ("cablecar", "aerial lift operation", "cabin", "haul rope"),
    ("hatchery", "fish rearing", "raceway", "cohort"),
    ("observatory", "telescope scheduling", "instrument", "observing block"),
    ("foundry", "metal casting", "furnace", "pour"),
    ("vineyard", "viticulture", "block", "harvest lot"),
    ("dredger", "channel dredging", "cutter", "spoil load"),
    ("aquifer", "groundwater monitoring", "borehole", "abstraction licence"),
    ("cannery", "food preserving", "retort", "sterilisation batch"),
    ("windfarm", "turbine operations", "turbine", "curtailment window"),
    ("archive", "cold-store conservation", "vault", "accession lot"),
    ("saltworks", "salt evaporation", "pan", "crystallisation run"),
    ("cablelay", "submarine cable laying", "plough", "splice"),
    ("smelter", "aluminium reduction", "potline", "anode set"),
    ("glasshouse", "orchid propagation", "bench", "propagation tray"),
    ("quarry", "aggregate extraction", "face", "blast round"),
    ("lockkeeper", "canal lock operation", "lock", "passage"),
    ("creamery", "cheese maturation", "cave", "wheel batch"),
    ("windtunnel", "aerodynamic testing", "test section", "run card"),
    ("peatland", "bog restoration", "compartment", "rewetting plan"),
    ("funicular", "incline railway", "car", "brake test"),
    ("sawmill", "timber conversion", "headrig", "log parcel"),
]

# Five "vendors", each with its own naming convention, verbosity and voice.
# A single template lattice -- which is what the first version shipped -- lets a
# reader dismiss the entire bulk as one pattern and attend only to the real
# skills, which makes "126 skills" overstate the effective load. Real stacks
# come from different authors and do not compress.
VENDORS = [
    ("{d}_{op}", "terse"),
    ("svc_{d}__{op}", "verbose"),
    ("{d}.{op}.v2", "dotted"),
    ("{op}_{d}", "imperative"),
    ("{D}{Op}Handler", "camel"),
]

VOICE = {
    "terse": "{verb} the {unit}.",
    "verbose": "{verb} the {unit} for a {domain} site. The call is idempotent within a shift and returns the "
               "prior value so a caller can reconcile. Values outside the commissioned band are refused rather "
               "than clamped, because downstream compliance reporting treats a clamped value as a fault.",
    "dotted": "{verb} the {unit}. Returns a status envelope; see the {domain} integration notes for retry semantics.",
    "imperative": "{verb} the {unit}. Fails closed if the {unit} is not currently in service.",
    "camel": "{verb} the {unit} within a {domain} deployment. Callers are expected to hold the shift lock.",
}

# Each domain contributes four operations, giving 100 skills.
OPERATIONS = [
    ("set_{d}_target",
     "Sets the operating target for a {unit} and holds it until the next scheduled change. "
     "The controller ramps toward the new value at a rate bounded by the commissioned limits "
     "for {domain}, and refuses any value outside the range the {unit} was certified for.",
     {"unit_id": "Identifier of the {unit} to adjust.", "target": "Requested operating target."}),
    ("read_{d}_history",
     "Returns logged readings for a {unit} over a requested window, at the interval the "
     "instrumentation was commissioned with. Gaps caused by sensor faults are reported as "
     "explicit nulls rather than interpolated, since {domain} records are used for compliance.",
     {"unit_id": "Identifier of the {unit} to read.", "window": "Time window to return."}),
    ("log_{d}_batch",
     "Files the outcome of a {batch} against the {unit} that produced it, together with the "
     "operator and the instrument calibration in force at the time. A {batch} whose readings "
     "fall outside the specified band is held for review rather than released.",
     {"unit_id": "Identifier of the {unit}.", "batch_ref": "Reference of the {batch}.",
      "result": "Recorded outcome."}),
    ("schedule_{d}_service",
     "Books a {unit} into a maintenance window, reserving both the slot and the competency "
     "group the job code requires. Conflicts with an existing booking are rejected outright "
     "rather than silently moved, because {domain} scheduling is audited.",
     {"unit_id": "Identifier of the {unit} to book in.", "job_code": "Maintenance job code.",
      "slot": "Requested maintenance window."}),
]


VERBS = ["Adjust", "Report on", "File a record against", "Book maintenance for",
         "Reconcile", "Certify", "Retire", "Commission"]


def main() -> None:
    tools = []
    for i, (prefix, domain, unit, batch) in enumerate(DOMAINS):
        # Rotate vendor and operation set per domain so no two neighbouring
        # entries share a shape, and no single pattern covers the pool.
        name_tpl, voice = VENDORS[i % len(VENDORS)]
        for j, (op_tpl, _desc_tpl, params) in enumerate(OPERATIONS):
            op = op_tpl.format(d="").replace("__", "_").strip("_")
            verb = VERBS[(i + j) % len(VERBS)]
            fmt = {"d": prefix, "domain": domain, "unit": unit, "batch": batch,
                   "op": op, "D": prefix.capitalize(), "Op": op.replace("_", " ").title().replace(" ", ""),
                   "verb": verb}
            props = {
                k: {"type": "string", "description": v.format(**fmt)}
                for k, v in params.items()
            }
            tools.append({
                "name": name_tpl.format(**fmt),
                "description": VOICE[voice].format(**fmt),
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": list(props)[: 1 + (i + j) % 2],
                },
            })

    names = [t["name"] for t in tools]
    assert len(names) == len(set(names)), "duplicate filler name"

    (HERE / "filler_pool.json").write_text(json.dumps({
        "_doc": (
            "GENERATED by gen_filler.py -- do not hand-edit. Bulk added at L4 to BOTH arms "
            "identically, so it adds catalog size without touching the overlap contrast. "
            "None of these has any bearing on an office-admin request; tests/test_build.py "
            "asserts no filler name collides with a base or pack skill."
        ),
        "tools": tools,
    }, indent=2) + "\n")
    print(f"Wrote filler_pool.json with {len(tools)} skills "
          f"({len(DOMAINS)} domains x {len(OPERATIONS)} operations).")


if __name__ == "__main__":
    main()
