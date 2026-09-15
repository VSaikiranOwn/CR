"""The arithmetic must reproduce the reference workbook exactly.

Every expected number here was read out of the cached results Excel itself
stored in CR_Estimation_Framework_Final_ver_2.xlsx.
"""
import pytest

from cr_tool import compute, constants as K
from cr_tool.spec import DetailRow, ReuseEntry, ScopeEntry, Story


def row(ui=(0, 0, 0), ms=(0, 0, 0), db=(0, 0, 0), bpm=(0, 0, 0)):
    return DetailRow(
        user_story="X", business_requirement="b", technical_component="t",
        ui=list(ui), ms=list(ms), db=list(db), bpm=list(bpm),
    )


class TestXlRound:
    @pytest.mark.parametrize("value,expected", [
        (4.5, 5), (2.5, 3), (1.5, 2), (0.75, 1), (0.5, 1), (0.4, 0), (-2.5, -3),
    ])
    def test_rounds_half_away_from_zero(self, value, expected):
        assert compute.xl_round(value) == expected

    def test_differs_from_python_round(self):
        # Python's banker's rounding would give 2 here; Excel gives 3.
        assert round(2.5) == 2
        assert compute.xl_round(2.5) == 3


class TestDetailsEffort:
    @pytest.mark.parametrize("kwargs,expected", [
        ({"ui": (0, 1, 0), "ms": (0, 0, 1)}, 8),    # ver_2 row 3
        ({"ms": (0, 1, 0)}, 3),                      # ver_2 row 4
        ({"ui": (1, 0, 0), "ms": (0, 1, 0)}, 5),     # ver_2 row 5: 4.5 -> 5
        ({"ui": (1, 0, 0), "ms": (1, 0, 0)}, 3),     # ver_2 row 6
        ({"ms": (1, 0, 0), "db": (0, 0, 1)}, 3),     # ver_2 row 7: 2.5 -> 3
        ({"ms": (1, 0, 0)}, 2),                      # ver_2 row 10: 1.5 -> 2
        ({"db": (3, 0, 0)}, 1),                      # ver_2 row 11: 0.75 -> 1
    ])
    def test_matches_reference_rows(self, kwargs, expected):
        assert compute.row_dev_effort(row(**kwargs)) == expected

    def test_complex_weight_is_five_not_four(self):
        # ver_2 raised Complex from 4 to 5. Guard against a silent revert.
        assert K.WEIGHT_COMPLEX == 5
        assert compute.row_dev_effort(row(ms=(0, 0, 1))) == 5

    def test_ms_simple_shares_the_1_5_weight(self):
        # MS Simple is deliberately NOT a separate weight; it shares 1.5
        # with UI Simple and BPM Simple, exactly as the ver_2 formula does.
        assert compute.row_dev_effort_raw(row(ms=(1, 0, 0))) == 1.5
        assert compute.row_dev_effort_raw(row(ui=(1, 0, 0))) == 1.5
        assert compute.row_dev_effort_raw(row(bpm=(1, 0, 0))) == 1.5

    def test_db_uses_the_lighter_weights(self):
        assert compute.row_dev_effort_raw(row(db=(1, 1, 1))) == 1.75


class TestSummary:
    def test_reference_totals(self):
        totals = compute.summary_totals(31)
        assert totals.development == 31
        assert totals.qa == 12          # 40% of 31 = 12.4 -> 12
        assert totals.req_design == 6   # 20% of 31 = 6.2  -> 6
        assert totals.total == 49

    def test_ratios_are_the_agreed_ones(self):
        assert K.SUMMARY_QA_RATIO == 0.4
        assert K.SUMMARY_RND_RATIO == 0.2


def make_story(scope_sizes, reuse_levels):
    return Story(
        epic="E", us_id="KEY-1", us_summary="S",
        scope={d: ScopeEntry(size=s) for d, s in zip(K.SCOPE_DIMENSIONS, scope_sizes)},
        reusability={d: ReuseEntry(level=l) for d, l in zip(K.REUSE_DIMENSIONS, reuse_levels)},
    )


class TestTenderStoryPoints:
    def test_reference_story_42132(self):
        story = make_story(
            ["Medium (4-6)", "Small (1-3)", "Small (1-3)"],
            ["1 - Low Reusability", "2 - Moderate Reusability", "4 - High Reusability",
             "1 - Low Reusability", "2 - Moderate Reusability"],
        )
        points = compute.story_points(story)
        assert points.framework_unit == 22           # 3*4 + 1*2 + 1*8
        assert points.reusability_score == 50        # 10 / (5*4) * 100
        assert points.adjustment_pct == 0.65
        assert points.framework_unit_adjusted == pytest.approx(7.7)
        assert points.req_design_unit == pytest.approx(1.54)
        assert points.tsp == pytest.approx(10.7184)

    def test_reference_story_42528(self):
        story = make_story(
            ["Not Applicable", "Small (1-3)", "Small (1-3)"],
            ["4 - High Reusability", "4 - High Reusability", "2 - Moderate Reusability",
             "2 - Moderate Reusability", "2 - Moderate Reusability"],
        )
        points = compute.story_points(story)
        assert points.framework_unit == 10           # 0 + 1*2 + 1*8
        assert points.reusability_score == 70        # 14 / (5*4) * 100
        assert points.adjustment_pct == 0.65
        assert points.framework_unit_adjusted == pytest.approx(3.5)
        assert points.req_design_unit == pytest.approx(0.7)
        assert points.tsp == pytest.approx(4.872)

    def test_not_applicable_is_excluded_from_both_sides_of_the_mean(self):
        story = make_story(
            ["Small (1-3)", "Not Applicable", "Not Applicable"],
            ["4 - High Reusability", "Not Applicable", "Not Applicable",
             "Not Applicable", "Not Applicable"],
        )
        # One applicable dimension scoring 4 out of 4 -> 100%, not 4/(5*4).
        assert compute.reusability_score(story) == 100

    def test_zero_reusability_still_counts_as_applicable(self):
        story = make_story(
            ["Small (1-3)", "Not Applicable", "Not Applicable"],
            ["0 - No Reusability", "4 - High Reusability", "Not Applicable",
             "Not Applicable", "Not Applicable"],
        )
        assert compute.reusability_score(story) == 50   # (0+4) / (2*4) * 100

    def test_all_dimensions_not_applicable_does_not_divide_by_zero(self):
        story = make_story(
            ["Not Applicable"] * 3, ["Not Applicable"] * 5,
        )
        assert compute.reusability_score(story) == 0
        assert compute.story_points(story).tsp == 0

    @pytest.mark.parametrize("score,expected", [
        (0, 0.0), (24, 0.0), (25, 0.35), (49, 0.35),
        (50, 0.65), (74, 0.65), (75, 0.85), (100, 0.85),
    ])
    def test_adjustment_bands(self, score, expected):
        assert compute.adjustment_pct(score) == expected
