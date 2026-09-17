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


FIXTURE_41000 = "tests/fixtures/batch-41000"


class TestAcGrouping:
    def test_sub_acs_fold_into_one_row(self):
        from cr_harness.derive import group_acs
        from cr_harness.parse import AcceptanceCriterion as AC
        groups = group_acs([AC("AC-1", "a"), AC("AC-1.1", "b"), AC("AC-2", "c")])
        assert [g.label for g in groups] == ["AC-1-AC-1.1", "AC-2"]

    def test_a_long_run_is_labelled_by_its_endpoints(self):
        from cr_harness.derive import group_acs
        from cr_harness.parse import AcceptanceCriterion as AC
        groups = group_acs([AC(f"AC-7.{n}", "x") for n in range(1, 8)])
        assert [g.label for g in groups] == ["AC-7.1-AC-7.7"]

    def test_flat_acs_are_untouched(self):
        from cr_harness.derive import group_acs
        from cr_harness.parse import AcceptanceCriterion as AC
        groups = group_acs([AC("AC-1", "a"), AC("AC-2", "b"), AC("AC-3", "c")])
        assert [g.label for g in groups] == ["AC-1", "AC-2", "AC-3"]

    def test_the_row_text_names_every_ac_it_covers(self):
        from cr_harness.derive import group_acs
        from cr_harness.parse import AcceptanceCriterion as AC
        text = group_acs([AC("AC-1", "first"), AC("AC-1.1", "second")])[0].requirement_text()
        assert "(AC-1) first" in text and "(AC-1.1) second" in text


class TestVersionResolution:
    def test_picks_the_highest_version(self):
        workspace = load_workspace(FIXTURE_41000)
        assert workspace.sources["hld"].endswith("versions/hld-v5.md")
        assert workspace.sources["lld"].endswith("versions/lld-v4.md")

    def test_the_version_number_beats_modification_time(self, tmp_path):
        # mtimes do not survive a copy or a clone, so they must not decide this.
        import os, shutil, time
        from cr_harness.parse import resolve_design_doc
        batch = tmp_path / "b"
        shutil.copytree(FIXTURE_41000, batch)
        plain = batch / "02-design" / "hld.md"
        now = time.time()
        os.utime(plain, (now, now))
        assert resolve_design_doc(batch, "hld").name == "hld-v5.md"

    def test_survives_a_copy_that_resets_timestamps(self, tmp_path):
        import shutil
        from cr_harness.parse import load_workspace as load
        batch = tmp_path / "copied"
        shutil.copytree(FIXTURE_41000, batch)
        assert load(batch).sources["lld"].endswith("versions/lld-v4.md")

    def test_falls_back_to_the_plain_file_with_no_versions_folder(self):
        from cr_harness.parse import resolve_design_doc
        from pathlib import Path
        assert resolve_design_doc(Path(FIXTURE), "hld").name == "hld.md"

    def test_an_explicit_override_wins(self):
        workspace = load_workspace(
            FIXTURE_41000, hld_path=f"{FIXTURE_41000}/02-design/versions/hld-v2.md")
        assert workspace.sources["hld"].endswith("hld-v2.md")


class TestLldOnlyMode:
    def test_selected_automatically_when_there_is_no_wbs(self):
        derivation = derive(load_workspace(FIXTURE_41000))
        assert derivation.mode == "lld"
        assert any("Impact Analysis" in note for note in derivation.notes)

    def test_impact_levels_map_onto_complexity(self):
        from cr_harness.derive import impact_complexity_flags
        from cr_harness.parse import ImpactRow
        rows = [ImpactRow("Backend", "svc", "High", "x"),
                ImpactRow("Frontend", "cmp", "Low", "y"),
                ImpactRow("Database", "tbl", "Medium", "z")]
        flags = impact_complexity_flags(rows, [], "x")
        assert flags["ms"] == [0, 0, 1]
        assert flags["ui"] == [1, 0, 0]
        assert flags["db"] == [0, 1, 0]

    def test_integration_rows_count_as_backend(self):
        from cr_harness.derive import impact_complexity_flags
        from cr_harness.parse import ImpactRow
        flags = impact_complexity_flags([ImpactRow("Integration", "UOB", "High", "x")], [], "s")
        assert flags["ms"] == [0, 0, 1]

    def test_unparsable_impact_is_skipped_not_guessed(self):
        from cr_harness.derive import impact_complexity_flags
        from cr_harness.parse import ImpactRow
        # The unfilled template literally contains "High/Medium/Low".
        flags = impact_complexity_flags([ImpactRow("Backend", "x", "High/Medium/Low", "")], [], "s")
        assert all(sum(v) == 0 for v in flags.values())

    def test_rows_get_real_differentiated_effort(self):
        from cr_tool.compute import row_dev_effort
        spec = parse_spec(derive(load_workspace(FIXTURE_41000)).spec)
        efforts = [row_dev_effort(r) for r in spec.rows]
        # The bug this replaces produced an identical 2 MD on every row.
        assert len(set(efforts)) > 1
        assert min(efforts) >= 2

    def test_column_d_still_labels_endpoints_and_bpm(self):
        derivation = derive(load_workspace(FIXTURE_41000))
        blob = "\n".join(r["technical_component"] for r in derivation.spec["rows"])
        assert "EXISTING to REUSE/CHECK:" in blob
        assert "EXISTING to MODIFY:" in blob
        assert "BPM: none." in blob
        assert "approved DCP Confluence Physical Data Model" in blob

    def test_interface_and_qa_reuse_survive_without_a_wbs(self):
        derivation = derive(load_workspace(FIXTURE_41000))
        reuse = derivation.spec["stories"][0]["reusability"]
        assert reuse["interface"]["level"] != "Not Applicable"
        assert reuse["qa"]["level"] != "Not Applicable"

    def test_no_wbs_flag_forces_the_mode_even_when_a_wbs_exists(self):
        derivation = derive(load_workspace(FIXTURE), use_wbs=False)
        assert derivation.mode == "lld"

    def test_requesting_wbs_without_one_falls_back_and_says_so(self):
        derivation = derive(load_workspace(FIXTURE_41000), use_wbs=True)
        assert derivation.mode == "lld"
        assert any("falling back" in note for note in derivation.notes)
