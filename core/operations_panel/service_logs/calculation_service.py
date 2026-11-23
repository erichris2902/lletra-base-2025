from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from core.operations_panel.models.service_log import ServiceLog, ServiceLogActivityType


def _midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _day_end(dt: datetime) -> datetime:
    return _midnight(dt) + timedelta(days=1)


def split_interval_by_day(start: datetime, end: datetime):
    cur_start = start
    while cur_start < end:
        cur_end = min(_day_end(cur_start), end)
        yield cur_start, cur_end
        cur_start = cur_end


def minutes_between(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def _merge_union_minutes(pairs: List[Tuple[datetime, datetime]]) -> int:
    """Given a list of (start,end) pairs within the same day, return total covered minutes (union)."""
    if not pairs:
        return 0
    pairs = sorted(pairs, key=lambda x: (x[0], x[1]))
    total = 0
    cur_s, cur_e = pairs[0]
    for s, e in pairs[1:]:
        if s <= cur_e:
            if e > cur_e:
                cur_e = e
        else:
            total += minutes_between(cur_s, cur_e)
            cur_s, cur_e = s, e
    total += minutes_between(cur_s, cur_e)
    return total


def calculate_totals(log: ServiceLog) -> Dict:
    per_day: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    overall: Dict[str, float] = defaultdict(float)
    day_segments: Dict[str, List[Tuple[datetime, datetime]]] = defaultdict(list)

    qs = log.activities.all().order_by("started_at")
    for act in qs:
        for s, e in split_interval_by_day(act.started_at, act.ended_at):
            mins = minutes_between(s, e)
            hours = mins / 60.0
            day_key = _midnight(s).date().isoformat()
            # Per-category sums (can exceed union if overlaps)
            per_day[day_key][act.activity_type] += hours
            overall[act.activity_type] += hours
            # Accumulate raw segments for union TOTAL
            day_segments[day_key].append((s, e))

    # Compute union-based TOTAL per day and overall
    overall_union_hours = 0.0
    for day_key, segs in day_segments.items():
        union_mins = _merge_union_minutes(segs)
        union_hours = union_mins / 60.0
        per_day[day_key]["TOTAL"] = union_hours
        overall_union_hours += union_hours

    cats = [
        ServiceLogActivityType.DRIVING,
        ServiceLogActivityType.PAUSE,
        ServiceLogActivityType.AUXILIARY,
        ServiceLogActivityType.EXCEPTION,
        ServiceLogActivityType.REST,
    ]

    per_day_out = []
    for day in sorted(per_day.keys()):
        row = {"date": day}
        for c in cats:
            row[c] = round(per_day[day].get(c, 0.0), 2)
        row["TOTAL"] = round(per_day[day].get("TOTAL", 0.0), 2)
        per_day_out.append(row)

    overall_out = {c: round(overall.get(c, 0.0), 2) for c in cats}
    overall_out["TOTAL"] = round(overall_union_hours, 2)

    return {
        "per_day": per_day_out,
        "overall": overall_out,
    }
