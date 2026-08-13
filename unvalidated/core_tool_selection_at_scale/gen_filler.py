"""Generate filler_pool.json -- the pool of irrelevant-but-plausible tool
schemas used to pad catalogs out to N.

Run:  python3 gen_filler.py     (writes filler_pool.json; committed to the repo
                                 so the exact pool is auditable, not re-derived
                                 at build time)

Design constraints this file exists to satisfy:

1. **Verbosity parity.** Real MCP/OpenAPI tool schemas are 150-400 tokens --
   nested objects, enums, multi-sentence descriptions carrying constraints.
   A pool of one-line toy schemas would make N=300 a ~18k-token prompt, which
   is nowhere near the regime long-context degradation is actually reported
   in. Filler here is written to the same weight as the hand-authored family
   tools in families.json.

2. **Style parity.** Every tool the solution sees must read as though it came
   from the same catalog. If filler were visibly templated boilerplate and the
   correct tool were visibly hand-written prose, a model could find the answer
   by prose style alone and the whole instrument would be measuring the wrong
   thing. Hence: three action phrasings per operation, three domain-specific
   constraint clauses per domain, and a per-operation caveat sentence, rotated
   so no two entries read identically.

3. **Answer-space disjointness.** No filler tool may be a defensible answer to
   any of the eight family queries. Filler domains are drawn deliberately
   outside the eight families' territories, and every operation is bound to an
   object identifier the queries never mention. build_cases.py re-checks this
   with an explicit forbidden-substring assertion rather than trusting it.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --- domains -----------------------------------------------------------------
# Each: prefix (tool-name stem), noun (singular, used in prose), and three
# constraint clauses that get rotated so the same domain doesn't read the same
# way thirteen times over. Deliberately outside the eight families' answer
# space: no payments-refund, log-reading, calendar-availability, deployment,
# access-granting, message-composing, event-counting or object-copying verbs.
DOMAINS = [
    ("inventory_item", "stock item", [
        "Quantities are tracked per warehouse bin, so the same item may show different counts in different locations.",
        "Items below their reorder point are flagged automatically on the next nightly reconciliation.",
        "Serial-tracked items cannot be adjusted in bulk and must be handled individually.",
    ]),
    ("shipment", "shipment", [
        "Carrier tracking numbers are assigned at dispatch and are immutable afterwards.",
        "Shipments spanning multiple parcels are represented as one record with several tracking legs.",
        "Customs paperwork is generated separately and is not part of this record.",
    ]),
    ("warehouse_location", "warehouse location", [
        "Aisle, rack and bin together form the location key and must all be supplied.",
        "Locations holding stock cannot be decommissioned until they are emptied.",
        "Temperature-controlled locations carry an additional compliance attribute.",
    ]),
    ("supplier", "supplier", [
        "Suppliers are deduplicated on tax identifier rather than on trading name.",
        "A supplier must have at least one approved contact before orders can be raised against it.",
        "Payment terms are inherited from the supplier's category unless overridden.",
    ]),
    ("purchase_order", "purchase order", [
        "Orders past the approval threshold require a second approver before they can be issued.",
        "Line totals are recomputed from unit price and quantity and cannot be set directly.",
        "Partially received orders remain open until every line is reconciled.",
    ]),
    ("expense_report", "expense report", [
        "Reports are locked once submitted and must be recalled before further edits.",
        "Receipts above the documentation threshold must be attached or the report is rejected.",
        "Foreign-currency lines are converted at the rate on the transaction date.",
    ]),
    ("payroll_run", "payroll run", [
        "A run cannot be altered after it has been committed to the payment file.",
        "Off-cycle runs are kept separate from the regular calendar for reporting.",
        "Statutory deductions are recalculated whenever the run is reopened.",
    ]),
    ("employee_record", "employee file", [
        "Historical field values are retained so that any past date can be reconstructed.",
        "Records for departed employees remain readable for the statutory retention period.",
        "Compensation fields are visible only to holders of the payroll role.",
    ]),
    ("job_requisition", "job requisition", [
        "A requisition must carry an approved headcount slot before it can be opened.",
        "Requisitions are tied to a cost centre, which determines the approval chain.",
        "Closing a requisition automatically rejects any candidates still in process.",
    ]),
    ("candidate_profile", "candidate profile", [
        "Profiles are deduplicated on email address across all open requisitions.",
        "Assessment scores are attached by the scoring service and are read-only here.",
        "Anonymised review mode hides identifying fields from the response.",
    ]),
    ("onboarding_task", "onboarding task", [
        "Tasks are sequenced by dependency, so a blocked task cannot be started early.",
        "Overdue tasks escalate to the assignee's manager after two working days.",
        "Compliance tasks cannot be waived, only completed or formally exempted.",
    ]),
    ("training_course", "training course", [
        "Course versions are immutable; changing content publishes a new version.",
        "Completion credit is awarded only when every module has been finished.",
        "Certification-bearing courses carry an expiry after which retraining is required.",
    ]),
    ("survey_definition", "survey", [
        "Questions cannot be changed once responses have been recorded against them.",
        "Anonymous surveys discard respondent identity at the point of submission.",
        "Branching logic is validated as a directed acyclic graph before publication.",
    ]),
    ("support_ticket", "support ticket", [
        "Tickets inherit priority from the customer's service tier unless explicitly overridden.",
        "The first-response clock stops only when an agent replies publicly.",
        "Merged tickets keep their own history and redirect to the surviving record.",
    ]),
    ("knowledge_article", "knowledge-base article", [
        "Articles move through draft, review and published states in that order.",
        "Localised variants are linked to the source article and track its version.",
        "Unpublished articles are excluded from customer-facing search.",
    ]),
    ("sla_policy", "service-level policy", [
        "Policies are evaluated in priority order and the first match wins.",
        "Business-hours calendars are attached per region and affect elapsed-time maths.",
        "A policy in use by an active contract cannot be deleted.",
    ]),
    ("contract_record", "contract", [
        "Executed contracts are immutable; changes are captured as numbered amendments.",
        "Renewal notice periods are computed from the contract's governing jurisdiction.",
        "Counterparty entities are resolved against the legal-entity register.",
    ]),
    ("legal_matter", "legal matter", [
        "Matters under litigation hold cannot have documents removed from them.",
        "External counsel access is granted per matter and expires with the engagement.",
        "Budget forecasts are tracked separately from actual invoiced fees.",
    ]),
    ("insurance_policy", "insurance policy", [
        "Coverage changes take effect at the next renewal unless endorsed mid-term.",
        "Claims history affects the renewal quote and is carried across policy versions.",
        "Certificates of insurance are generated from the policy, not stored on it.",
    ]),
    ("hardware_asset", "hardware asset", [
        "Assets are identified by asset tag, which is distinct from the serial number.",
        "Depreciation schedules are derived from the asset class at time of purchase.",
        "Assets pending disposal are excluded from ordinary inventory counts.",
    ]),
    ("device_enrollment", "device enrollment", [
        "Enrollment binds a device to exactly one owner at a time.",
        "Compliance posture is re-evaluated on every check-in, not on demand.",
        "Wiped devices retain their enrollment record for audit purposes.",
    ]),
    ("tls_certificate", "TLS certificate", [
        "Certificates are matched to their private key by fingerprint at install time.",
        "Renewal is attempted automatically thirty days before expiry.",
        "Wildcard certificates cannot be issued for public suffix domains.",
    ]),
    ("dns_record", "DNS record", [
        "Changes propagate according to the record's time-to-live, not instantly.",
        "Apex records are restricted to types the zone's provider supports.",
        "Records managed by an external controller are read-only here.",
    ]),
    ("firewall_rule", "firewall rule", [
        "Rules are evaluated top to bottom and the first match terminates evaluation.",
        "Rules referencing a deleted address group are automatically disabled.",
        "Changes are staged and take effect only when the ruleset is committed.",
    ]),
    ("ml_model_version", "model version", [
        "Versions are immutable once registered; retraining produces a new version.",
        "Evaluation metrics are attached by the evaluation job and cannot be edited.",
        "A version serving live traffic cannot be deregistered.",
    ]),
    ("training_dataset", "training dataset", [
        "Datasets are content-addressed, so identical contents resolve to one record.",
        "Splits are recorded as manifests rather than as copies of the underlying rows.",
        "Datasets carrying restricted data require a documented lawful basis.",
    ]),
]

# --- operations --------------------------------------------------------------
# (suffix, [3 action phrasings], caveat, extra params beyond the shared ones)
OPS = [
    ("create", [
        "Creates a new {noun} record from the supplied field values and returns its identifier.",
        "Registers a {noun} in the system and assigns it a newly generated identifier.",
        "Opens a new {noun} record, populated with the field values provided by the caller.",
    ], "Required fields missing from the payload cause the call to fail without creating anything.",
     [("fields", "object", "Field values for the new record, keyed by field name.", None)]),

    ("get", [
        "Fetches a single {noun} by its identifier and returns its current field values.",
        "Reads one {noun} record, returning every field the caller is entitled to see.",
        "Retrieves the {noun} identified by the caller, including its computed fields.",
    ], "An identifier that does not resolve returns an empty result rather than an error.",
     [("include_related", "boolean", "Whether to expand linked records inline in the response.", None)]),

    ("list", [
        "Returns {noun} records matching the supplied filter, one page at a time.",
        "Enumerates {noun} records the caller can see, newest first, in pages.",
        "Lists {noun} records narrowed by the given filter and ordered by last update.",
    ], "Paging is cursor-based; the cursor from the previous response must be passed to advance.",
     [("filter", "object", "Field-level filter applied before paging.", None),
      ("page_size", "integer", "Maximum records to return in one page.", None)]),

    ("update", [
        "Applies a partial update to one {noun}, changing only the fields supplied.",
        "Modifies the named fields on a single {noun} and leaves the rest untouched.",
        "Writes new values into selected fields of an existing {noun} record.",
    ], "Fields omitted from the payload are left as they are rather than being cleared.",
     [("fields", "object", "Field values to overwrite, keyed by field name.", None)]),

    ("archive", [
        "Archives a {noun}, removing it from active views while retaining it for audit.",
        "Marks one {noun} as archived so it no longer appears in day-to-day listings.",
        "Retires a {noun} record, keeping it readable but excluding it from active use.",
    ], "Archiving is reversible; the record is never destroyed by this call.",
     [("reason", "string", "Reason recorded on the archived record.", None)]),

    ("search", [
        "Performs a full-text search across {noun} records and returns ranked matches.",
        "Searches the text fields of {noun} records for the caller's query terms.",
        "Finds {noun} records whose indexed text matches the supplied query string.",
    ], "The index refreshes asynchronously, so very recent writes may not appear immediately.",
     [("query", "string", "Free-text query string.", None),
      ("limit", "integer", "Maximum number of ranked matches to return.", None)]),

    ("set_status", [
        "Transitions one {noun} to a new status, subject to the allowed state machine.",
        "Moves a single {noun} into a different status if the transition is permitted.",
        "Changes the workflow status of one {noun} record.",
    ], "Transitions that the workflow does not allow are rejected and leave the record unchanged.",
     [("status", "string", "Target status.", ["open", "in_progress", "blocked", "closed", "cancelled"])]),

    ("assign_owner", [
        "Assigns responsibility for one {noun} to a named principal.",
        "Sets the owning principal of a single {noun} record.",
        "Transfers ownership of one {noun} to the principal supplied by the caller.",
    ], "The previous owner is notified and retains read access unless it is revoked separately.",
     [("owner", "string", "Principal to make responsible for the record.", None)]),

    ("add_note", [
        "Appends a timestamped note to one {noun}'s activity trail.",
        "Records a free-text note against a single {noun}.",
        "Adds an annotation to the activity history of one {noun} record.",
    ], "Notes are append-only and cannot be edited or removed once written.",
     [("note", "string", "Text of the note to append.", None),
      ("visibility", "string", "Who may read the note.", ["internal", "shared", "public"])]),

    ("bulk_import", [
        "Imports many {noun} records at once from a delimited file in object storage.",
        "Loads a batch of {noun} records from a file the caller has already uploaded.",
        "Ingests {noun} records in bulk from a file reference supplied by the caller.",
    ], "The call returns a job identifier; rows are validated individually and bad rows are reported at the end.",
     [("source_uri", "string", "Location of the file to import.", None),
      ("on_conflict", "string", "How to treat rows matching an existing record.", ["skip", "overwrite", "fail"])]),

    ("export_csv", [
        "Writes matching {noun} records to a delimited file and returns a download link.",
        "Produces a delimited export of the selected {noun} records for offline use.",
        "Renders {noun} records matching the filter into a downloadable delimited file.",
    ], "Large exports are produced asynchronously and the link becomes valid once the job completes.",
     [("filter", "object", "Field-level filter selecting which records to export.", None),
      ("delimiter", "string", "Column separator to use.", [",", ";", "\t"])]),

    ("validate", [
        "Checks one {noun} against a named ruleset and reports any violations found.",
        "Runs validation rules over a single {noun} and returns the problems detected.",
        "Evaluates one {noun} record for rule violations without altering it.",
    ], "Validation is read-only: nothing is corrected, and the record is returned unchanged.",
     [("ruleset", "string", "Name of the ruleset to evaluate against.", None)]),

    ("list_history", [
        "Returns the change history of one {noun}, oldest first.",
        "Lists the recorded revisions of a single {noun} record.",
        "Reads the audit trail for one {noun}, showing what changed and who changed it.",
    ], "History entries are retained for the configured audit window and cannot be amended.",
     [("since", "string", "Only return revisions recorded after this ISO-8601 timestamp.", None)]),
]

ID_PARAM_NAMES = {
    "create": None,  # create takes no id
}


def build_tool(dom_idx: int, domain: tuple, op_idx: int, op: tuple) -> dict:
    prefix, noun, clauses = domain
    suffix, phrasings, caveat, extra = op

    rot = (dom_idx + op_idx) % 3
    action = phrasings[rot].format(noun=noun)
    clause = clauses[(dom_idx + op_idx * 2) % 3]
    description = f"{action} {clause} {caveat}"

    props: dict = {}
    required: list[str] = []

    if suffix not in ("create", "list", "search", "bulk_import", "export_csv"):
        id_name = f"{prefix}_id"
        props[id_name] = {
            "type": "string",
            "description": f"Identifier of the {noun} to act on.",
        }
        required.append(id_name)

    for pname, ptype, pdesc, penum in extra:
        entry: dict = {"type": ptype, "description": pdesc}
        if penum:
            entry["enum"] = penum
        props[pname] = entry
        # Everything except optional refinements is required.
        if pname not in ("include_related", "page_size", "limit", "since",
                         "visibility", "delimiter", "reason"):
            required.append(pname)

    return {
        "name": f"{prefix}_{suffix}",
        "description": description,
        "parameters": {"type": "object", "properties": props, "required": required},
    }


def build() -> list[dict]:
    tools = []
    for dom_idx, domain in enumerate(DOMAINS):
        for op_idx, op in enumerate(OPS):
            tools.append(build_tool(dom_idx, domain, op_idx, op))

    names = [t["name"] for t in tools]
    if len(names) != len(set(names)):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise ValueError(f"duplicate filler tool names: {dupes}")
    return tools


if __name__ == "__main__":
    tools = build()
    out = {
        "_doc": (
            "GENERATED by gen_filler.py -- do not hand-edit. Irrelevant-but-plausible "
            "tool schemas used to pad catalogs to N. None of these is a defensible "
            "answer to any family query in families.json; build_cases.py asserts this."
        ),
        "tools": tools,
    }
    (HERE / "filler_pool.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote filler_pool.json: {len(tools)} tools.")
