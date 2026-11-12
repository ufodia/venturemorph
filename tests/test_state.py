"""Contract tests for portable, project-isolated Venturemorph state."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "venturemorph" / "scripts" / "check_state.py"
TEMPLATE = ROOT / "skills" / "venturemorph" / "assets" / "project-state.template.json"
SPEC = importlib.util.spec_from_file_location("check_state", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def empty_state():
    state = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    state["project"]["id"] = "demo"
    return state


def populated_state():
    state = empty_state()
    state["updated_at"] = "2026-02-28"
    state["project"]["name"] = "Illustrative test fixture"
    state["evidence"] = [
        {"id": "demo:evidence:1", "date": "2026-02-27", "type": "observed", "source": "Synthetic test fixture, not real project data", "summary": "A local fixture provides a test observation."},
        {"id": "demo:evidence:2", "date": "2026-02-28", "type": "user_report", "source": "Synthetic owner statement in a test fixture", "summary": "Owner reports a preference for a small pilot."},
    ]
    state["assumptions"] = [{"id": "demo:assumption:1", "date": "2026-02-28", "statement": "The pilot may clarify the audience.", "status": "supported", "evidence_ids": ["demo:evidence:2"]}]
    state["recommendations"] = [
        {"id": "demo:recommendation:1", "date": "2026-02-27", "statement": "Use the previous pilot scope.", "status": "superseded", "rationale": "Earlier scope was too broad.", "evidence_ids": [], "revisit_when": "A later review establishes more capacity.", "acceptance_source": "Synthetic owner acceptance in test fixture"},
        {"id": "demo:recommendation:2", "date": "2026-02-28", "statement": "Run a smaller pilot.", "status": "accepted", "rationale": "The owner requested a narrow test.", "evidence_ids": ["demo:evidence:2"], "revisit_when": "The pilot result is reviewed.", "acceptance_source": "Synthetic owner acceptance in test fixture", "supersedes_id": "demo:recommendation:1"},
    ]
    state["experiments"] = [{"id": "demo:experiment:1", "date": "2026-02-28", "status": "completed", "hypothesis": "A narrow pilot produces a usable audience signal.", "metric": "Number of interpretable pilot responses", "threshold": "At least one interpretable response", "timebox": {"duration_days": 2, "started_at": "2026-02-27"}, "guardrail": "No paid outreach or external messages.", "evidence_ids": ["demo:evidence:2"], "recommendation_ids": ["demo:recommendation:2"], "result": {"summary": "Synthetic result used only to exercise validation.", "evidence_ids": ["demo:evidence:1"]}}]
    state["reviews"] = [{"id": "demo:review:1", "date": "2026-02-28", "summary": "Synthetic snapshot: the pilot is complete; the next question remains open.", "evidence_ids": ["demo:evidence:1"], "assumption_ids": ["demo:assumption:1"], "recommendation_ids": ["demo:recommendation:2"], "experiment_ids": ["demo:experiment:1"]}]
    return state


class StateValidationTests(unittest.TestCase):
    def assert_invalid(self, state, path, detail=None):
        errors = CHECK.validate_state(state)
        self.assertTrue(errors, "state unexpectedly validated")
        matching = [error for error in errors if error.startswith(path + ":")]
        self.assertTrue(matching, f"missing path {path!r}: {errors}")
        if detail:
            self.assertTrue(any(detail in error for error in matching), matching)

    def test_template_is_valid_and_contains_only_unknown_context(self):
        state = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(CHECK.validate_state(state), [])
        self.assertIsNone(state["project"]["name"])
        self.assertIsNone(state["updated_at"])
        for key in CHECK.COLLECTIONS:
            self.assertEqual(state[key], [])

    def test_populated_state_is_valid_and_validation_does_not_mutate(self):
        state = populated_state()
        before = copy.deepcopy(state)
        self.assertEqual(CHECK.validate_state(state, "demo"), [])
        self.assertEqual(state, before)

    def test_every_status_can_be_represented(self):
        for status in ("proposed", "accepted", "rejected", "superseded"):
            state = populated_state()
            state["recommendations"][1].pop("supersedes_id")
            state["recommendations"][1]["status"] = status
            self.assertEqual(CHECK.validate_state(state), [], status)
        for status in ("proposed", "running", "completed", "cancelled"):
            state = populated_state()
            state["experiments"][0]["status"] = status
            if status != "completed":
                state["experiments"][0]["result"] = None
            if status == "proposed":
                state["experiments"][0]["timebox"]["started_at"] = None
            self.assertEqual(CHECK.validate_state(state), [], status)
        for status in ("unvalidated", "supported", "refuted"):
            state = populated_state()
            state["assumptions"][0]["status"] = status
            self.assertEqual(CHECK.validate_state(state), [], status)

    def test_unknown_schema_and_boolean_schema_are_rejected(self):
        for version in (True, False, 2, "1", 1.0, None):
            with self.subTest(version=version):
                state = empty_state()
                state["schema_version"] = version
                self.assert_invalid(state, "$.schema_version")

    def test_strict_root_and_record_shape(self):
        state = empty_state()
        state["extra"] = "unexpected"
        del state["reviews"]
        self.assert_invalid(state, "$.extra", "unknown field")
        self.assert_invalid(state, "$.reviews", "required")
        state = populated_state()
        state["evidence"][0]["extra"] = False
        self.assert_invalid(state, "$.evidence[0].extra")
        self.assert_invalid([], "$", "object")

    def test_wrong_nested_types_report_paths(self):
        cases = [
            (lambda s: s.update(project=[]), "$.project"),
            (lambda s: s["project"].update(context=None), "$.project.context"),
            (lambda s: s["project"]["context"].update(constraints="none"), "$.project.context.constraints"),
            (lambda s: s.update(evidence={}), "$.evidence"),
            (lambda s: s["evidence"].__setitem__(0, "bad"), "$.evidence[0]"),
            (lambda s: s["assumptions"][0].update(evidence_ids=[False]), "$.assumptions[0].evidence_ids[0]"),
            (lambda s: s["experiments"][0].update(result=[]), "$.experiments[0].result"),
        ]
        for mutate, path in cases:
            with self.subTest(path=path):
                state = populated_state()
                mutate(state)
                self.assert_invalid(state, path)

    def test_blank_strings_and_invalid_enums_are_rejected(self):
        state = populated_state()
        state["evidence"][0].update(source="  ", type="inferred")
        state["assumptions"][0]["status"] = "confirmed"
        state["recommendations"][0]["status"] = "done"
        state["experiments"][0]["status"] = "done"
        for path in ("$.evidence[0].source", "$.evidence[0].type", "$.assumptions[0].status", "$.recommendations[0].status", "$.experiments[0].status"):
            self.assert_invalid(state, path)

    def test_project_id_format_and_expected_project_isolation(self):
        state = populated_state()
        errors = CHECK.validate_state(state, "another-project")
        self.assertTrue(any("$.project.id: project mismatch" in error for error in errors))
        state["project"]["id"] = "Demo project"
        self.assert_invalid(state, "$.project.id")

    def test_record_ids_cannot_cross_project_or_record_type(self):
        for identifier in ("other:evidence:1", "demo:review:1", "demo:evidence:", "demo:evidence:bad id"):
            with self.subTest(identifier=identifier):
                state = populated_state()
                state["evidence"][0]["id"] = identifier
                self.assert_invalid(state, "$.evidence[0].id")

    def test_duplicate_ids_and_references_are_rejected(self):
        state = populated_state()
        state["evidence"].append(copy.deepcopy(state["evidence"][0]))
        self.assert_invalid(state, "$.evidence[2].id", "duplicate")
        state["assumptions"][0]["evidence_ids"] *= 2
        self.assert_invalid(state, "$.assumptions[0].evidence_ids[1]", "duplicate")

    def test_all_reference_types_reject_dangling_or_wrong_type_ids(self):
        for field in ("evidence_ids", "assumption_ids", "recommendation_ids", "experiment_ids"):
            with self.subTest(field=field):
                state = populated_state()
                state["reviews"][0][field] = ["another-project:evidence:missing"]
                self.assert_invalid(state, f"$.reviews[0].{field}[0]", "unknown")
        state = populated_state()
        state["assumptions"][0]["evidence_ids"] = ["demo:experiment:1"]
        self.assert_invalid(state, "$.assumptions[0].evidence_ids[0]", "unknown evidence")

    def test_invalid_dates_and_timestamps_are_rejected(self):
        for date in ("2026-02-30", "2026-2-01", "2026-02-28T12:00:00Z", True, "tomorrow"):
            with self.subTest(date=date):
                state = populated_state()
                state["evidence"][0]["date"] = date
                self.assert_invalid(state, "$.evidence[0].date")
        state = populated_state()
        state["evidence"][0]["date"] = "2026-03-01"
        self.assert_invalid(state, "$.evidence[0].date", "later")
        state["updated_at"] = None
        self.assert_invalid(state, "$.updated_at", "required")

    def test_supported_assumption_requires_evidence(self):
        state = populated_state()
        state["assumptions"][0]["evidence_ids"] = []
        self.assert_invalid(state, "$.assumptions[0].evidence_ids", "require evidence")
        state["assumptions"][0]["status"] = "unvalidated"
        self.assertEqual(CHECK.validate_state(state), [])

    def test_accepted_decision_requires_acceptance_source(self):
        for source in (None, "", "   ", False):
            with self.subTest(source=source):
                state = populated_state()
                state["recommendations"][1]["acceptance_source"] = source
                self.assert_invalid(state, "$.recommendations[1].acceptance_source")

    def test_supersession_requires_existing_replaced_decision(self):
        state = populated_state()
        state["recommendations"][1]["supersedes_id"] = "demo:recommendation:missing"
        self.assert_invalid(state, "$.recommendations[1].supersedes_id", "unknown")
        state["recommendations"][1]["supersedes_id"] = "demo:recommendation:2"
        self.assert_invalid(state, "$.recommendations[1].supersedes_id", "itself")
        state = populated_state()
        state["recommendations"][0]["status"] = "proposed"
        self.assert_invalid(state, "$.recommendations[1].supersedes_id", "replaced")
        state = populated_state()
        state["recommendations"][1]["status"] = "proposed"
        self.assert_invalid(state, "$.recommendations[1].supersedes_id", "only an accepted")

    def test_supersession_chains_are_valid_but_cycles_are_not(self):
        state = populated_state()
        third = copy.deepcopy(state["recommendations"][1])
        third["id"] = "demo:recommendation:3"
        third["supersedes_id"] = "demo:recommendation:2"
        state["recommendations"][1]["status"] = "superseded"
        state["recommendations"].append(third)
        self.assertEqual(CHECK.validate_state(state), [])
        state["recommendations"][0]["supersedes_id"] = "demo:recommendation:2"
        self.assert_invalid(state, "$.recommendations[0].supersedes_id", "cycle")

    def test_superseding_decision_retains_acceptance_source_after_supersession(self):
        for source in (None, "", "   ", False):
            with self.subTest(source=source):
                state = populated_state()
                state["recommendations"][1].update(status="superseded", acceptance_source=source)
                self.assert_invalid(state, "$.recommendations[1].acceptance_source")

    def test_retired_unaccepted_proposal_does_not_require_acceptance(self):
        state = populated_state()
        state["recommendations"][0]["acceptance_source"] = None
        self.assertEqual(CHECK.validate_state(state), [])

    def test_experiment_timebox_rejects_bool_zero_and_bad_date(self):
        for duration in (True, False, 0, -1, 1.5, "2"):
            with self.subTest(duration=duration):
                state = populated_state()
                state["experiments"][0]["timebox"]["duration_days"] = duration
                self.assert_invalid(state, "$.experiments[0].timebox.duration_days")
        state = populated_state()
        state["experiments"][0]["timebox"]["started_at"] = "2026-03-01"
        self.assert_invalid(state, "$.experiments[0].timebox.started_at", "later")

    def test_completed_experiment_requires_result_and_result_evidence(self):
        state = populated_state()
        state["experiments"][0]["result"] = None
        self.assert_invalid(state, "$.experiments[0].result", "require a result")
        state = populated_state()
        state["experiments"][0]["result"] = {"summary": "Synthetic result", "evidence_ids": []}
        self.assert_invalid(state, "$.experiments[0].result.evidence_ids", "at least one")
        state["experiments"][0]["result"]["evidence_ids"] = ["demo:evidence:missing"]
        self.assert_invalid(state, "$.experiments[0].result.evidence_ids[0]", "unknown")

    def test_proposed_experiment_cannot_have_started_or_have_result(self):
        state = populated_state()
        experiment = state["experiments"][0]
        experiment.update(status="proposed", result=None)
        self.assert_invalid(state, "$.experiments[0].timebox.started_at", "must have a null")
        experiment["timebox"]["started_at"] = None
        self.assertEqual(CHECK.validate_state(state), [])
        experiment["result"] = {"summary": "Synthetic interim result", "evidence_ids": ["demo:evidence:1"]}
        self.assert_invalid(state, "$.experiments[0].result", "must have a null")

    def test_running_and_completed_experiments_require_start_date(self):
        for status in ("running", "completed"):
            with self.subTest(status=status):
                state = populated_state()
                state["experiments"][0]["status"] = status
                state["experiments"][0]["timebox"]["started_at"] = None
                self.assert_invalid(state, "$.experiments[0].timebox.started_at", "required")

    def test_cancelled_experiment_may_be_unstarted_but_result_requires_start(self):
        state = populated_state()
        experiment = state["experiments"][0]
        result = experiment["result"]
        experiment.update(status="cancelled", result=None)
        experiment["timebox"]["started_at"] = None
        self.assertEqual(CHECK.validate_state(state), [])
        experiment["result"] = result
        self.assert_invalid(state, "$.experiments[0].timebox.started_at", "required")
        experiment["timebox"]["started_at"] = "2026-02-27"
        self.assertEqual(CHECK.validate_state(state), [])

    def test_running_experiment_accepts_evidence_backed_interim_result(self):
        state = populated_state()
        state["experiments"][0]["status"] = "running"
        self.assertEqual(CHECK.validate_state(state), [])

    def test_json_legal_wrong_types_at_every_path_do_not_crash(self):
        def paths(value, prefix=()):
            yield prefix
            if isinstance(value, dict):
                for key, child in value.items():
                    yield from paths(child, prefix + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from paths(child, prefix + (index,))

        original = populated_state()
        replacements = (None, True, False, 0, 1.5, "", "wrong", [], {}, [{}], {"wrong": []})
        for path in paths(original):
            for replacement in replacements:
                with self.subTest(path=path, replacement=replacement):
                    state = copy.deepcopy(original)
                    if not path:
                        state = copy.deepcopy(replacement)
                    else:
                        parent = state
                        for key in path[:-1]:
                            parent = parent[key]
                        parent[path[-1]] = copy.deepcopy(replacement)
                    errors = CHECK.validate_state(state)
                    self.assertIsInstance(errors, list)
                    self.assertTrue(all(isinstance(error, str) for error in errors))


class CommandLineTests(unittest.TestCase):
    def run_file(self, contents, *arguments):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_bytes(contents)
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(path), *arguments], capture_output=True, text=True, check=False)
            self.assertEqual(path.read_bytes(), before, "validator changed the input file")
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ["state.json"])
            return result

    def test_utf8_bom_is_supported_and_command_is_read_only(self):
        contents = b"\xef\xbb\xbf" + json.dumps(populated_state()).encode("utf-8")
        result = self.run_file(contents, "--project-id", "demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VALID:", result.stdout)

    def test_wrong_project_exits_one_with_path(self):
        result = self.run_file(json.dumps(populated_state()).encode("utf-8"), "--project-id", "other")
        self.assertEqual(result.returncode, 1)
        self.assertIn("$.project.id", result.stderr)

    def test_malformed_json_invalid_utf8_duplicates_and_nonjson_numbers(self):
        for content, message in ((b"{", "line 1"), (b"\xff", "UTF-8"), (b'{"a":1,"a":2}', "duplicate object key"), (b'{"a": NaN}', "non-JSON numeric")):
            with self.subTest(content=content):
                result = self.run_file(content)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)

    def test_io_and_usage_errors_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(SCRIPT), str(Path(directory) / "missing.json")], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("IO ERROR", result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
