"""The mapping rules from harness artifacts onto the CR sheet."""
import json
import subprocess
import sys

import pytest

from cr_harness import constants as H
from cr_harness.derive import band_scope, complexity_flags, derive, snap_to_rung
from cr_harness.parse import WbsTask, load_workspace
from cr_tool.spec import parse as parse_spec

FIXTURE = "tests/fixtures/batch-42132"


def task(layer, size, task_id="WBS-K-X-01"):
    return WbsTask(id=task_id, story_key="K", layer=layer, size=size, ac_ids=["AC-1"])


@pytest.fixture(scope="module")
def derivation():
    return derive(load_workspace(FIXTURE))


class TestSnapToRung:
    @pytest.mark.parametrize("mean,expected", [
        (0.0, 0), (0.4, 0), (0.6, 1), (1.4, 1), (1.6, 2),
        (2.9, 2), (3.1, 4), (4.0, 4),
    ])
    def test_snaps_to_the_nearest_rung(self, mean, expected):
        assert snap_to_rung(mean) == expected

    def test_ties_go_to_the_lower_rung(self):
        # 3.0 is equidistant from 2 and 4; the lower rung means less reuse,
        # which yields a higher and therefore safer estimate.
        assert snap_to_rung(3.0) == 2
        assert snap_to_rung(0.5) == 0


class TestBandScope:
    @pytest.mark.parametrize("count,expected", [
        (0, "Not Applicable"), (1, "Small (1-3)"), (3, "Small (1-3)"),
        (4, "Medium (4-6)"), (6, "Medium (4-6)"), (7, "Large (>6)"),
    ])
    def test_bands(self, count, expected):
        assert band_scope(count) == expected


class TestComplexityFlags:
    def test_highest_declared_size_wins(self):
        flags = complexity_flags([task("BE", "S"), task("BE", "L")], [], "x")
        assert flags["ms"] == [0, 0, 1]

    def test_promotes_when_many_tasks_share_the_top_size(self):
        tasks = [task("BE", "M", f"WBS-K-BE-0{i}") for i in range(1, 4)]
        assert complexity_flags(tasks, [], "x")["ms"] == [0, 0, 1]   # 3x M -> complex

    def test_does_not_promote_below_the_threshold(self):
        tasks = [task("BE", "M"), task("BE", "M")]
        assert complexity_flags(tasks, [], "x")["ms"] == [0, 1, 0]

    def test_promotion_is_capped_at_complex(self):
        tasks = [task("BE", "L", f"WBS-K-BE-0{i}") for i in range(1, 5)]
        assert complexity_flags(tasks, [], "x")["ms"] == [0, 0, 1]

    def test_docs_tasks_produce_no_flag(self):
        flags = complexity_flags([task("DOCS", "L")], [], "x")
        assert all(sum(v) == 0 for v in flags.values())

    def test_unsized_tasks_default_to_medium_and_are_recorded(self):
        evidence = []
        flags = complexity_flags([task("FE", None)], evidence, "x")
        assert flags["ui"] == [0, 1, 0]
        assert "assumed M for unsized" in evidence[0].source

    def test_each_layer_is_scored_independently(self):
        flags = complexity_flags([task("BE", "L"), task("FE", "S"), task("DB", "M")], [], "x")
        assert flags["ms"] == [0, 0, 1]
        assert flags["ui"] == [1, 0, 0]
        assert flags["db"] == [0, 1, 0]

    def test_every_flag_is_cited(self):
        evidence = []
        complexity_flags([task("BE", "L")], evidence, "US-1 / AC-1")
        assert evidence[0].scope == "US-1 / AC-1"
        assert "WBS-K-X-01[L]" in evidence[0].source


class TestEndToEnd:
    def test_one_details_row_per_ac(self, derivation):
        assert len(derivation.spec["rows"]) == 3

    def test_one_story_row_per_ticket(self, derivation):
        assert [s["us_id"] for s in derivation.spec["stories"]] == ["SLADCYBQSK-42132"]

    def test_reproduces_the_reference_framework_unit(self, derivation):
        # The real ver_2 sheet scores this story's Framework Unit at 22.
        from cr_tool.compute import framework_unit
        spec = parse_spec(derivation.spec)
        assert framework_unit(spec.stories[0]) == 22

    def test_effort_matches_the_task_sizes(self, derivation):
        from cr_tool.compute import details_total, row_dev_effort
        spec = parse_spec(derivation.spec)
        # AC-1: MS complex 5 + UI medium 3 + DB complex 1 = 9
        assert row_dev_effort(spec.rows[0]) == 9
        assert details_total(spec.rows) == 19

    def test_the_spec_is_valid_for_the_renderer(self, derivation):
        parse_spec(derivation.spec)          # raises SpecError if not

    def test_integrations_are_deduplicated_against_participants(self, derivation):
        scope = derivation.spec["stories"][0]["scope"]["integration"]
        # ELS appears as an HLD bullet and a sequence participant; it counts once.
        assert scope["size"] == "Small (1-3)"

    def test_scope_is_marked_as_a_business_draft(self, derivation):
        for entry in derivation.spec["stories"][0]["scope"].values():
            assert H.DRAFT_SCOPE in entry["details"]

    def test_column_d_labels_new_versus_existing(self, derivation):
        column_d = derivation.spec["rows"][0]["technical_component"]
        assert "NEW API:" in column_d
        assert "EXISTING to REUSE/CHECK:" in column_d
        assert "BPM: none." in column_d

    def test_database_prose_points_at_confluence_not_the_repo(self, derivation):
        column_d = derivation.spec["rows"][0]["technical_component"]
        assert "approved DCP Confluence Physical Data Model" in column_d

    def test_every_decision_carries_evidence(self, derivation):
        assert derivation.evidence
        assert all(item.source for item in derivation.evidence)


class TestValidator:
    def run(self, workspace):
        return subprocess.run(
            [sys.executable, "harness/validators/cr_complete.py", "--workspace", str(workspace)],
            capture_output=True, text=True)

    def test_passes_on_a_generated_batch(self, tmp_path):
        import shutil
        batch = tmp_path / "batch"
        shutil.copytree(FIXTURE, batch)
        subprocess.run([sys.executable, "-c",
                        "import sys;sys.path.insert(0,'src');"
                        "from cr_harness.cli import main;main([str(sys.argv[1])])", str(batch)],
                       capture_output=True, check=True)
        result = self.run(batch)
        assert result.returncode == 0
        assert "PASS  cr-complete" in result.stdout

    def test_fails_when_the_cr_folder_is_missing_but_wbs_exists(self, tmp_path):
        import shutil
        batch = tmp_path / "batch"
        shutil.copytree(FIXTURE, batch)
        shutil.rmtree(batch / "02-design" / "cr", ignore_errors=True)
        result = self.run(batch)
        assert result.returncode == 1
        assert "run the cr-estimate skill" in result.stdout

    def test_stays_quiet_before_the_wbs_exists(self, tmp_path):
        batch = tmp_path / "batch"
        (batch / "01-requirements").mkdir(parents=True)
        result = self.run(batch)
        assert result.returncode == 0
        assert "not expected" in result.stdout

    def test_fails_on_a_story_with_no_details_row(self, tmp_path):
        import shutil
        batch = tmp_path / "batch"
        shutil.copytree(FIXTURE, batch)
        cr = batch / "02-design" / "cr"
        cr.mkdir(parents=True, exist_ok=True)
        (cr / "cr-evidence.md").write_text("x")
        (cr / "batch-CR-Estimation.xlsx").write_text("x")
        (cr / "cr-spec.json").write_text(json.dumps({
            "rows": [{"user_story": "A", "ms": [0, 1, 0]}],
            "stories": [{"us_id": "B"}],
        }))
        result = self.run(batch)
        assert result.returncode == 1
        assert "no Tender Story Points row" in result.stdout
        assert "no Details row estimates it" in result.stdout
