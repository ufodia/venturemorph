# Portable project state, version 1

Use a separate copy of [the JSON template](../assets/project-state.template.json) for each project. Before adding records, replace `project.id` with a stable, project-specific slug. Do not copy another project's records into the file. The validator is read-only, requires only Python 3.8+ and the standard library, and makes no network calls.

```sh
python skills/venturemorph/scripts/check_state.py path/to/project-state.json --project-id your-project-id
```

When installed elsewhere, use the actual path to `scripts/check_state.py`. Pass the expected project ID from the active project, rather than copying it from the file being checked. Exit codes: `0` valid, `1` invalid data or malformed JSON, `2` file access or command usage error. Errors identify JSON paths. UTF-8 with or without a BOM is accepted. Duplicate object keys, non-JSON numeric constants, unknown fields and unknown schema versions are rejected. The command does not update dates or repair data.

## Root and identity

Every listed field is required unless marked optional. Objects reject extra fields. Strings must contain non-whitespace text. Dates are calendar dates in `YYYY-MM-DD` form, without a time component. `null` means unknown; do not replace it with a guessed fact, empty string or invented traction.

| Field | Type and meaning |
| --- | --- |
| `schema_version` | Integer `1`; booleans and `1.0` are invalid. |
| `project` | Object with `id`, `name`, `context`. |
| `project.id` | 1–64 lowercase letters, digits, `_` or `-`; first character is a letter or digit. Stable across sessions. |
| `project.name` | String or `null`. |
| `project.context` | Object with `offering`, `audience`, `market`, `stage`, `goal` (each string or `null`), and `constraints` (array of strings). |
| `updated_at` | Date, or `null` only while every record collection is empty. Must be at least as recent as every record's `date`. |
| `evidence`, `assumptions`, `reviews`, `recommendations`, `experiments` | Arrays of the records below. Empty arrays are valid. |

Treat `project.name` and `project.context` as the attributable current or accepted baseline, not a recommended future state. Keep an unaccepted pivot, name, audience, or changed constraint in recommendations/assumptions and the review snapshot until an actual change or explicit acceptance supports updating the baseline. Keep `project.id` stable even if the accepted name changes.

All record IDs follow `<project.id>:<kind>:<local-id>`. Kinds are `evidence`, `assumption`, `review`, `recommendation`, `experiment`. Local IDs begin with a letter or digit, then contain letters, digits, `.`, `_` or `-`; for example `acme:evidence:interview-01`. IDs are unique and immutable. The project/type prefix prevents foreign-project records and wrong-type references from silently becoming local facts. Every reference must resolve within the same file and correct collection. Reference arrays reject duplicates. Do not repurpose an old ID for a new observation or decision.

## Record fields

All records require `id` and `date`. `date` is the date the record was created or last deliberately revised, not a fabricated event timestamp. Put an earlier event date or reporting period in the summary/source when relevant.

| Collection | Additional required fields |
| --- | --- |
| `evidence` | `type`: `user_report` or `observed`; `source`: retrievable location or explicit provenance description; `summary`: what the source actually supports. |
| `assumptions` | `statement`; `status`: `unvalidated`, `supported` or `refuted`; `evidence_ids`: evidence-ID array. Supported/refuted assumptions require at least one reference. |
| `reviews` | `summary`: dated narrative snapshot including current understanding, decision statuses at review time, open questions, next focus, and the complete experiment contract below; `evidence_ids`, `assumption_ids`, `recommendation_ids`, `experiment_ids`: corresponding ID arrays. |
| `recommendations` | `statement`; `status`: `proposed`, `accepted`, `rejected` or `superseded`; `rationale`; `evidence_ids`; `revisit_when`: concrete condition to reconsider; `acceptance_source`: string or `null`. |
| `experiments` | `status`: `proposed`, `running`, `completed` or `cancelled`; `hypothesis`; `metric`; `threshold`; `timebox`; `guardrail`; `evidence_ids`; `recommendation_ids`; `result`. |

Recommendations become decisions only through explicit acceptance. `accepted` requires a nonempty `acceptance_source` identifying who accepted it and where/when acceptance was recorded. A recommendation is never accepted merely because evidence favors it or the assistant suggested it. Keep that acceptance source when a decision is later superseded. A proposed recommendation with no evidence must be presented as a hypothesis, not an established finding.

Recommendations optionally have `supersedes_id` (a nonempty recommendation ID, omitted when unused). Only an `accepted` or formerly accepted `superseded` decision may carry it, and that source decision must retain a nonempty `acceptance_source` even after it is superseded. Its target must exist, differ from itself and have status `superseded`; cycles are invalid. This allows retained historical chains. A retired, unaccepted proposal may have status `superseded` and a null acceptance source if it has no `supersedes_id`. Keep rejected and superseded records instead of deleting inconvenient history.

Experiment `timebox` is an object with `duration_days` (positive integer; booleans are invalid) and `started_at` (date or `null`). A known start date cannot be later than the experiment record's date. `threshold` is a string defining the success criterion, including units; `guardrail` defines the stop condition or acceptable risk boundary. `result` is `null` until a result exists, or an object with `summary` and a nonempty `evidence_ids` array. Proposed experiments require both a null start date and a null result. Running and completed experiments require a start date; completed experiments also require a result. Any nonnull result, including an interim or cancelled result, requires a start date. A cancelled experiment may remain unstarted with no result. Running or cancelled experiments may retain an evidence-backed interim result; completion never follows from elapsed time alone.

## Preserve the complete experiment contract

The compact experiment object is an index, not the entire protocol. In the associated dated `reviews.summary`, retain the decision, audience, intervention, comparator, recruitment/sample, baseline or its collection plan, event/numerator/denominator/window, proposed or agreed threshold, timebox, budget and effort caps, guardrail, and continue/change/stop/inconclusive actions. Preserve brand implications and which conditions were accepted at the time. Write unknowns explicitly.

The snapshot must let a state-only handoff recover the same protocol; do not rely on an unavailable report or mutable record references. A separate report can add detail but cannot substitute for the snapshot. See [the fictional populated example](../assets/project-state.example.json). Older valid files may lack a complete snapshot: retain them, mark the protocol incomplete, and recover it from source material or the user before interpreting a result. Structural validation cannot assess narrative completeness.

## Session updates and limits

Load and validate the active project's file before relying on it. If an expected project ID does not match, stop using that file for the active project. Add new evidence with its source and date, label user statements `user_report`, preserve unanswered questions as assumptions, and record explicit owner decisions separately from proposals through their status and acceptance source. Add a dated review after a material strategy review. Preserve the review's narrative as a historical snapshot; linked records describe the current record state, so references alone are not an immutable snapshot. Update `updated_at` when records change and validate again before saving through the host's normal file workflow.

Validation checks structure, dates, identity, statuses and reference integrity. It cannot verify that a cited source is true, accessible, causally informative, or sufficient to justify a recommendation; it cannot establish owner consent. Those judgments remain part of the review. Never treat a structurally valid file as proof of traction.
