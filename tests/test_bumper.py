import datetime as dt

import pytest

from check_workflow.dep_bumper import parse_cooldown

COOLDOWN_TEST_CASES = (
    ("P0D", dt.timedelta(days=0)),
    ("P7D", dt.timedelta(days=7)),
    ("P14D", dt.timedelta(days=14)),
    ("P180D", dt.timedelta(days=180)),
)


@pytest.mark.parametrize(("cooldown_spec", "truth_out"), COOLDOWN_TEST_CASES)
def test_parse_cooldown(cooldown_spec: str, truth_out: dt.timedelta) -> None:
    assert parse_cooldown(cooldown_spec) == truth_out


BAD_COOLDOWN_CASES = ["p1D", "p1d", "P1d", "P1.5D", "ABCD", "P-5D", "P3Y6M4DT12H30M5S"]


@pytest.mark.parametrize("cooldown_spec", BAD_COOLDOWN_CASES)
def test_parse_cooldown_invalid_raises(cooldown_spec: str) -> None:
    with pytest.raises(ValueError):
        _ = parse_cooldown(cooldown_spec)
