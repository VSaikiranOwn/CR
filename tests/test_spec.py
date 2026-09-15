import json

import pytest

from cr_tool import constants as K
from cr_tool.spec import SpecError, parse, load


def minimal_row(**overrides):
    row = {
        "user_story": "KEY-1",
        "business_requirement": "AC1.1 - something",
        "technical_component": "MS (Medium) - ms-x",
        "ms": [0, 1, 0],
    }
    row.update(overrides)
    return row


class TestRowValidation:
    def test_rejects_an_empty_spec(self):
        with pytest.raises(SpecError, match="no 'rows'"):
            parse({"rows": []})

    def test_rejects_a_row_with_no_flags(self):
        with pytest.raises(SpecError, match="no component flags"):
            parse({"rows": [minimal_row(ms=[0, 0, 0])]})

    def test_rejects_a_wrong_length_count_array(self):
        with pytest.raises(SpecError, match="3-element list"):
            parse({"rows": [minimal_row(ms=[1, 0])]})

    def test_rejects_a_negative_count(self):
        with pytest.raises(SpecError, match="non-negative"):
            parse({"rows": [minimal_row(ms=[-1, 0, 0])]})

    def test_rejects_missing_business_requirement(self):
        with pytest.raises(SpecError, match="business_requirement"):
            parse({"rows": [minimal_row(business_requirement="  ")]})

    def test_accepts_a_dict_form_count(self):
        spec = parse({"rows": [minimal_row(ms={"medium": 1})]})
        assert spec.rows[0].ms == [0, 1, 0]

    def test_rejects_legacy_ratio_overrides(self):
        with pytest.raises(SpecError, match="fixed for this framework"):
            parse({"rows": [minimal_row()], "summary": {"qa_ratio": 0.3}})


class TestGrouping:
    def test_s_no_restarts_per_story_group(self):
        spec = parse({"rows": [
            minimal_row(user_story="KEY-1"),
            minimal_row(user_story="KEY-1"),
            minimal_row(user_story="Shared"),
            minimal_row(user_story="KEY-2"),
            minimal_row(user_story="Shared"),
        ]})
        assert [r.s_no for r in spec.rows] == [1, 2, 3, 1, 2]

    def test_shared_row_joins_the_group_above_it(self):
        spec = parse({"rows": [
            minimal_row(user_story="KEY-1"),
            minimal_row(user_story="Shared"),
        ]})
        assert spec.rows[1].group == "KEY-1"

    def test_explicit_group_overrides_inference(self):
        spec = parse({"rows": [
            minimal_row(user_story="KEY-1"),
            minimal_row(user_story="Shared", group="KEY-9"),
        ]})
        assert spec.rows[1].group == "KEY-9"
        assert spec.rows[1].s_no == 1


class TestStoryNormalisation:
    def base_story(self, **overrides):
        story = {
            "us_id": "KEY-1",
            "scope": {"user_interaction": {"size": "M"}, "pages": {"size": "S"},
                      "integration": {"size": "S"}},
            "reusability": {"frontend": {"level": "1"}, "backend": {"level": "2"},
                            "interface": {"level": "4"}, "database": {"level": "1"},
                            "qa": {"level": "2"}},
        }
        story.update(overrides)
        return story

    def test_shorthand_sizes_expand_to_dropdown_values(self):
        spec = parse({"rows": [minimal_row()], "stories": [self.base_story()]})
        scope = spec.stories[0].scope
        assert scope["user_interaction"].size == "Medium (4-6)"
        assert scope["pages"].size == "Small (1-3)"

    def test_shorthand_levels_expand_to_dropdown_values(self):
        spec = parse({"rows": [minimal_row()], "stories": [self.base_story()]})
        assert spec.stories[0].reusability["frontend"].level == "1 - Low Reusability"
        assert spec.stories[0].reusability["interface"].level == "4 - High Reusability"

    def test_missing_dimension_defaults_to_not_applicable(self):
        story = self.base_story(scope={"pages": {"size": "S"}})
        spec = parse({"rows": [minimal_row()], "stories": [story]})
        assert spec.stories[0].scope["user_interaction"].size == K.NOT_APPLICABLE

    def test_tolerates_the_templates_resuability_typo(self):
        story = self.base_story()
        story["reusability"]["frontend"]["level"] = "0 - No Resuability"
        spec = parse({"rows": [minimal_row()], "stories": [story]})
        assert spec.stories[0].reusability["frontend"].level == "0 - No Reusability"

    def test_rejects_an_invalid_size(self):
        story = self.base_story(scope={"pages": {"size": "Enormous"}})
        with pytest.raises(SpecError, match="not a valid option"):
            parse({"rows": [minimal_row()], "stories": [story]})

    def test_requires_a_story_id(self):
        story = self.base_story()
        del story["us_id"]
        with pytest.raises(SpecError, match="us_id"):
            parse({"rows": [minimal_row()], "stories": [story]})


class TestWarnings:
    def test_warns_when_a_row_exceeds_the_guideline_band(self):
        spec = parse({"rows": [minimal_row(ms=[0, 0, 3])]})
        assert any("above the 10 MD guideline" in w for w in spec.warnings)

    def test_warns_when_a_story_has_no_details_rows(self):
        spec = parse({
            "rows": [minimal_row(user_story="KEY-1")],
            "stories": [{"us_id": "KEY-2", "scope": {}, "reusability": {}}],
        })
        assert any("KEY-2" in w and "no Details row" in w for w in spec.warnings)

    def test_warns_when_the_tsp_sheet_would_be_blank(self):
        spec = parse({"rows": [minimal_row()]})
        assert any("will be left blank" in w for w in spec.warnings)


class TestLoad:
    def test_strips_help_keys_at_any_depth(self, tmp_path):
        path = tmp_path / "s.json"
        path.write_text(json.dumps({
            "//": "help", "rows": [minimal_row()],
            "summary": {"//original_efforts": "help",
                        "original_efforts": {"development": 10}},
        }))
        spec = load(path)
        assert spec.original_efforts == {"development": 10.0}

    def test_reports_bad_json_clearly(self, tmp_path):
        path = tmp_path / "s.json"
        path.write_text("{ not json")
        with pytest.raises(SpecError, match="invalid JSON"):
            load(path)
