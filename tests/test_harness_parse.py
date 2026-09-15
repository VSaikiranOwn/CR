"""Parsing the DCP harness artifacts as they are actually filled in."""
import pytest

from cr_harness.parse import (
    load_workspace, parse_hld, parse_lld, parse_requirements, parse_tables, parse_wbs,
)

FIXTURE = "tests/fixtures/batch-42132"


@pytest.fixture(scope="module")
def workspace():
    return load_workspace(FIXTURE)


class TestTables:
    def test_reads_a_table_into_row_dicts(self):
        table = parse_tables("| A | B |\n|---|---|\n| 1 | 2 |")[0]
        assert table == [{"A": "1", "B": "2"}]

    def test_ignores_a_pipe_block_with_no_separator(self):
        assert parse_tables("| not | a table |\n| still | not |") == []

    def test_pads_a_short_row(self):
        table = parse_tables("| A | B | C |\n|---|---|---|\n| 1 |")[0]
        assert table == [{"A": "1", "B": "", "C": ""}]


class TestRequirements:
    def test_extracts_tickets_and_acs(self, workspace):
        tickets = workspace.requirements.tickets
        assert [t.key for t in tickets] == ["SLADCYBQSK-42132"]
        assert [ac.id for ac in tickets[0].acs] == ["AC-1", "AC-2", "AC-3"]

    def test_keeps_the_ac_text_verbatim(self, workspace):
        assert workspace.requirements.tickets[0].acs[0].text.startswith("Given a lodgment is Submitted")

    def test_skips_unfilled_template_placeholders(self):
        template = ("## Acceptance Criteria\n\n### <TICKET-KEY> — <summary>\n"
                    "- **AC-1** — Given <context>, When <action>, Then <outcome>.\n")
        assert parse_requirements(template).tickets == []


class TestWbs:
    def test_parses_task_id_layer_size_and_ac(self, workspace):
        task = next(t for t in workspace.wbs.tasks if t.id.endswith("BE-02"))
        assert task.layer == "BE"
        assert task.size == "L"
        assert task.ac_ids == ["AC-1"]
        assert task.story_key == "SLADCYBQSK-42132"

    def test_absorbs_the_indented_task_fields(self, workspace):
        task = next(t for t in workspace.wbs.tasks if t.id.endswith("BE-03"))
        assert task.reuse_strategy == "EXTEND"
        assert task.repo.startswith("ms-legalinstrument")
        assert task.test_slice == "TS-42132-BE-03"
        assert "Withdrawal update type" in task.what

    def test_maps_layers_to_cr_dimensions(self, workspace):
        by_layer = {t.layer: t.dimension for t in workspace.wbs.tasks}
        assert by_layer["BE"] == "ms"
        assert by_layer["FE"] == "ui"
        assert by_layer["DB"] == "db"
        assert by_layer["DOCS"] is None      # already inside the R&D ratio

    def test_reads_the_api_reuse_register(self, workspace):
        register = workspace.wbs.api_register
        assert len(register) == 4
        assert {e.decision for e in register} == {"REUSE", "NEW", "EXTEND"}
        assert register[0].wbs_ids == ["WBS-SLADCYBQSK-42132-BE-01"]

    def test_ignores_the_unfilled_template(self):
        template = ("- [ ] **WBS-<story-key>-BE-01** - `FR-<story-key>-01` - `AC-1` - [S/M/L]\n")
        # <story-key> has no recognised layer suffix pattern after the placeholder
        assert all(t.size is None for t in parse_wbs(template).tasks)


class TestLld:
    def test_finds_every_ac_section(self, workspace):
        assert [ac.id for ac in workspace.lld.acs] == ["AC-1", "AC-2", "AC-3"]

    def test_reads_the_story_key(self, workspace):
        assert workspace.lld.story_key == "SLADCYBQSK-42132"

    def test_accepts_both_reuse_spellings(self, workspace):
        levels = {c.candidate: c.level for c in workspace.lld.ac("AC-1").reuse}
        assert levels["LodgmentForm"] == 2          # written as "2"
        assert levels["ConfirmDialog"] == 4         # written as "High"
        assert levels["LodgementService.find"] == 1  # written as "Low"
        assert levels["Lodgement.InstrumentWithdrawal"] == 0  # written as "None"

    def test_classifies_candidates_by_location(self, workspace):
        dimensions = {c.candidate: c.dimension() for c in workspace.lld.ac("AC-1").reuse}
        assert dimensions["LodgmentForm"] == "frontend"
        assert dimensions["LodgementService.find"] == "backend"
        assert dimensions["Lodgement.InstrumentWithdrawal"] == "database"

    def test_collects_screens_and_components(self, workspace):
        ac = workspace.lld.ac("AC-1")
        assert ac.screens == ["lodgment-form.png", "withdraw-confirm.png"]
        assert ac.components == ["LodgmentForm", "WithdrawConfirmDialog"]

    def test_detects_an_explicit_no_bpm_statement(self, workspace):
        assert workspace.lld.ac("AC-1").no_bpm is True

    def test_excludes_our_own_services_from_participants(self, workspace):
        # "participant SVC as ms-legalinstrument" is internal, not an integration.
        assert workspace.lld.ac("AC-1").participants == ["ELS"]

    def test_reads_the_summary_rollups(self, workspace):
        assert workspace.lld.blast_radius
        assert workspace.lld.reuse_percentages


class TestHld:
    def test_reads_integrations_as_separate_items(self, workspace):
        assert len(workspace.hld.integrations) == 2

    def test_splits_a_single_prose_line_into_named_systems(self):
        hld = parse_hld("## 8. Integrations\nCPF / IRAS / MyInfo touchpoints only.\n")
        assert set(hld.integrations) == {"CPF", "IRAS", "MyInfo"}


class TestWorkspaceLoading:
    def test_records_missing_artifacts_rather_than_raising(self, tmp_path):
        (tmp_path / "01-requirements").mkdir()
        workspace = load_workspace(tmp_path)
        assert "02-design/wbs.md" in workspace.missing

    def test_rejects_a_path_that_is_not_a_batch(self):
        with pytest.raises(NotADirectoryError):
            load_workspace("tests/fixtures/does-not-exist")

    def test_records_the_graphify_date(self, workspace):
        assert workspace.graphify_generated is not None
