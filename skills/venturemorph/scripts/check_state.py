#!/usr/bin/env python3
"""Read-only validation of a Venturemorph v1 project-state JSON file."""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path


COLLECTIONS = {
    "evidence": "evidence",
    "assumptions": "assumption",
    "reviews": "review",
    "recommendations": "recommendation",
    "experiments": "experiment",
}
PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
LOCAL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class _Validator:
    def __init__(self):
        self.errors = []
        self.ids = {name: {} for name in COLLECTIONS}
        self.references = []
        self.record_dates = []
        self.supersessions = []

    def error(self, path, message):
        self.errors.append(f"{path}: {message}")

    def shape(self, value, path, required, optional=()):
        if not isinstance(value, dict):
            self.error(path, "expected an object")
            return False
        for key in sorted(set(required) - value.keys()):
            self.error(f"{path}.{key}", "required field is missing")
        for key in sorted(value.keys() - set(required) - set(optional)):
            self.error(f"{path}.{key}", "unknown field")
        return True

    def text(self, value, path, nullable=False):
        if nullable and value is None:
            return True
        if not isinstance(value, str) or not value.strip():
            self.error(path, "expected a nonempty string" + (" or null" if nullable else ""))
            return False
        return True

    def date(self, value, path, nullable=False):
        if nullable and value is None:
            return None
        if not isinstance(value, str) or not DATE.fullmatch(value):
            self.error(path, "expected an ISO date (YYYY-MM-DD)" + (" or null" if nullable else ""))
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            self.error(path, "invalid calendar date")
            return None

    def enum(self, value, path, choices):
        if not isinstance(value, str) or value not in choices:
            self.error(path, "expected one of: " + ", ".join(choices))

    def texts(self, value, path):
        if not isinstance(value, list):
            self.error(path, "expected an array of strings")
            return False
        for index, item in enumerate(value):
            self.text(item, f"{path}[{index}]")
        return True

    def refs(self, value, path, collection):
        if not self.texts(value, path):
            return
        seen = set()
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            if not isinstance(item, str):
                continue
            if item in seen:
                self.error(item_path, "duplicate reference")
            seen.add(item)
            self.references.append((item_path, item, collection))

    def record(self, item, path, required, collection, project_id, optional=()):
        if not self.shape(item, path, required, optional):
            return False
        identifier = item.get("id")
        if self.text(identifier, f"{path}.id"):
            prefix = f"{project_id}:{COLLECTIONS[collection]}:"
            if not identifier.startswith(prefix) or not LOCAL_ID.fullmatch(identifier[len(prefix):]):
                self.error(f"{path}.id", f"expected '{prefix}<local-id>' for this project and record type")
            if identifier in self.ids[collection]:
                self.error(f"{path}.id", "duplicate ID")
            self.ids[collection][identifier] = (item, path)
        parsed_date = self.date(item.get("date"), f"{path}.date")
        if parsed_date:
            self.record_dates.append((f"{path}.date", parsed_date))
        return True

    def validate(self, state, expected_project_id):
        root_fields = ("schema_version", "project", "updated_at", *COLLECTIONS)
        if not self.shape(state, "$", root_fields):
            return self.errors
        version = state.get("schema_version")
        if type(version) is not int or version != 1:
            self.error("$.schema_version", "unsupported schema version; expected integer 1")
        project = state.get("project")
        project_id = "<project-id>"
        if self.shape(project, "$.project", ("id", "name", "context")):
            candidate = project.get("id")
            if self.text(candidate, "$.project.id"):
                project_id = candidate
                if not PROJECT_ID.fullmatch(candidate):
                    self.error("$.project.id", "use 1-64 lowercase letters, digits, underscores or hyphens; begin with a letter or digit")
                if expected_project_id is not None and candidate != expected_project_id:
                    self.error("$.project.id", f"project mismatch: expected '{expected_project_id}'")
            self.text(project.get("name"), "$.project.name", nullable=True)
            context = project.get("context")
            fields = ("offering", "audience", "market", "stage", "goal", "constraints")
            if self.shape(context, "$.project.context", fields):
                for key in fields[:-1]:
                    self.text(context.get(key), f"$.project.context.{key}", nullable=True)
                self.texts(context.get("constraints"), "$.project.context.constraints")
        updated = self.date(state.get("updated_at"), "$.updated_at", nullable=True)
        has_records = False
        for collection in COLLECTIONS:
            records = state.get(collection)
            if not isinstance(records, list):
                self.error(f"$.{collection}", "expected an array")
                continue
            has_records = has_records or bool(records)
            for index, item in enumerate(records):
                getattr(self, collection)(item, f"$.{collection}[{index}]", project_id)
        if has_records and state.get("updated_at") is None:
            self.error("$.updated_at", "a date is required when the state contains records")
        if updated:
            for path, record_date in self.record_dates:
                if record_date > updated:
                    self.error(path, "must not be later than $.updated_at")
        for path, identifier, collection in self.references:
            if identifier not in self.ids[collection]:
                self.error(path, f"unknown {COLLECTIONS[collection]} ID '{identifier}' in this project")
        self.check_supersessions()
        return self.errors

    def evidence(self, item, path, project_id):
        fields = ("id", "date", "type", "source", "summary")
        if self.record(item, path, fields, "evidence", project_id):
            self.enum(item.get("type"), f"{path}.type", ("user_report", "observed"))
            for key in ("source", "summary"):
                self.text(item.get(key), f"{path}.{key}")

    def assumptions(self, item, path, project_id):
        fields = ("id", "date", "statement", "status", "evidence_ids")
        if self.record(item, path, fields, "assumptions", project_id):
            self.text(item.get("statement"), f"{path}.statement")
            self.enum(item.get("status"), f"{path}.status", ("unvalidated", "supported", "refuted"))
            self.refs(item.get("evidence_ids"), f"{path}.evidence_ids", "evidence")
            if item.get("status") in ("supported", "refuted") and item.get("evidence_ids") == []:
                self.error(f"{path}.evidence_ids", "supported or refuted assumptions require evidence")

    def reviews(self, item, path, project_id):
        ref_fields = {"evidence_ids": "evidence", "assumption_ids": "assumptions", "recommendation_ids": "recommendations", "experiment_ids": "experiments"}
        fields = ("id", "date", "summary", *ref_fields)
        if self.record(item, path, fields, "reviews", project_id):
            self.text(item.get("summary"), f"{path}.summary")
            for key, collection in ref_fields.items():
                self.refs(item.get(key), f"{path}.{key}", collection)

    def recommendations(self, item, path, project_id):
        fields = ("id", "date", "statement", "status", "rationale", "evidence_ids", "revisit_when", "acceptance_source")
        if self.record(item, path, fields, "recommendations", project_id, ("supersedes_id",)):
            for key in ("statement", "rationale", "revisit_when"):
                self.text(item.get(key), f"{path}.{key}")
            self.enum(item.get("status"), f"{path}.status", ("proposed", "accepted", "rejected", "superseded"))
            self.refs(item.get("evidence_ids"), f"{path}.evidence_ids", "evidence")
            needs_acceptance = item.get("status") == "accepted" or "supersedes_id" in item
            self.text(item.get("acceptance_source"), f"{path}.acceptance_source", nullable=not needs_acceptance)
            if "supersedes_id" in item:
                identifier = item["supersedes_id"]
                if self.text(identifier, f"{path}.supersedes_id"):
                    self.references.append((f"{path}.supersedes_id", identifier, "recommendations"))
                    self.supersessions.append((item.get("id"), identifier, item.get("status"), path))

    def experiments(self, item, path, project_id):
        fields = ("id", "date", "status", "hypothesis", "metric", "threshold", "timebox", "guardrail", "evidence_ids", "recommendation_ids", "result")
        if not self.record(item, path, fields, "experiments", project_id):
            return
        status = item.get("status")
        result = item.get("result")
        self.enum(status, f"{path}.status", ("proposed", "running", "completed", "cancelled"))
        for key in ("hypothesis", "metric", "threshold", "guardrail"):
            self.text(item.get(key), f"{path}.{key}")
        timebox = item.get("timebox")
        if self.shape(timebox, f"{path}.timebox", ("duration_days", "started_at")):
            duration = timebox.get("duration_days")
            if type(duration) is not int or duration < 1:
                self.error(f"{path}.timebox.duration_days", "expected a positive integer")
            start_value = timebox.get("started_at")
            started = self.date(start_value, f"{path}.timebox.started_at", nullable=True)
            if status == "proposed" and start_value is not None:
                self.error(f"{path}.timebox.started_at", "proposed experiments must have a null start date")
            if (status in ("running", "completed") or result is not None) and start_value is None:
                self.error(f"{path}.timebox.started_at", "a start date is required for running/completed experiments or any result")
            record_date = self.date(item.get("date"), f"{path}.date")
            if started and record_date and started > record_date:
                self.error(f"{path}.timebox.started_at", "must not be later than the experiment record date")
        self.refs(item.get("evidence_ids"), f"{path}.evidence_ids", "evidence")
        self.refs(item.get("recommendation_ids"), f"{path}.recommendation_ids", "recommendations")
        if status == "proposed" and result is not None:
            self.error(f"{path}.result", "proposed experiments must have a null result")
        if result is None:
            if status == "completed":
                self.error(f"{path}.result", "completed experiments require a result")
        elif self.shape(result, f"{path}.result", ("summary", "evidence_ids")):
            self.text(result.get("summary"), f"{path}.result.summary")
            self.refs(result.get("evidence_ids"), f"{path}.result.evidence_ids", "evidence")
            if result.get("evidence_ids") == []:
                self.error(f"{path}.result.evidence_ids", "results require at least one evidence reference")

    def check_supersessions(self):
        for identifier, target_id, status, path in self.supersessions:
            if identifier == target_id:
                self.error(f"{path}.supersedes_id", "a recommendation cannot supersede itself")
            if status not in ("accepted", "superseded"):
                self.error(f"{path}.supersedes_id", "only an accepted or formerly accepted (superseded) decision can supersede another")
            target = self.ids["recommendations"].get(target_id)
            if target and target[0].get("status") != "superseded":
                self.error(f"{path}.supersedes_id", "the replaced recommendation must have status 'superseded'")
        links = {source: target for source, target, _, _ in self.supersessions if isinstance(source, str)}
        for source, _, _, path in self.supersessions:
            if not isinstance(source, str):
                continue
            seen = set()
            current = source
            while current in links:
                if current in seen:
                    self.error(f"{path}.supersedes_id", "supersession cycle detected")
                    break
                seen.add(current)
                current = links[current]


def validate_state(state, expected_project_id=None):
    """Return path-qualified errors without mutating the supplied state."""
    return _Validator().validate(state, expected_project_id)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key '{key}'")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"non-JSON numeric constant '{value}'")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_file", type=Path, help="UTF-8 project-state JSON file (BOM accepted)")
    parser.add_argument("--project-id", help="require this project ID to prevent loading another project's state")
    args = parser.parse_args(argv)
    try:
        content = args.state_file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        print(f"INVALID: $: expected UTF-8 JSON ({error})", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"IO ERROR: {args.state_file}: {error}", file=sys.stderr)
        return 2
    try:
        state = json.loads(content, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except json.JSONDecodeError as error:
        print(f"INVALID: $: malformed JSON at line {error.lineno}, column {error.colno}: {error.msg}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"INVALID: $: {error}", file=sys.stderr)
        return 1
    errors = validate_state(state, args.project_id)
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1
    print(f"VALID: {args.state_file} (project {state['project']['id']}, schema 1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
