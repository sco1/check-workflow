import datetime as dt
import re

PND_RE = re.compile(r"P(\d+)D$")


def parse_cooldown(cooldown_spec: str) -> dt.timedelta:
    """
    Parse cooldown string, as `PnD`, into its equivalent timedelta.

    See: https://en.wikipedia.org/wiki/ISO_8601#Durations
    """
    scan = PND_RE.match(cooldown_spec)
    if not scan:
        raise ValueError(f"Unrecognized cooldown specified: '{cooldown_spec}'. Please use 'PnD'.")

    return dt.timedelta(days=int(scan.group(1)))
