from dataclasses import dataclass
from datetime import datetime, time, timedelta

LEVEL_RANK = {"Low": 1, "Medium": 2, "High": 3}


@dataclass
class Window:
    start: time
    end: time
    level: str | None  # None means "no energy window covers this segment"

    @property
    def duration_minutes(self) -> float:
        return (self.end.hour * 60 + self.end.minute) - (
            self.start.hour * 60 + self.start.minute
        )


def compute_free_windows(
    commitments: list[tuple], day_start: time, day_end: time
) -> list[tuple[time, time]]:
    # walk the day, collect whatever's left after carving out commitments
    parsed = sorted(
        (time.fromisoformat(row[2]), time.fromisoformat(row[3])) for row in commitments
    )
    free_windows: list[tuple[time, time]] = []
    cursor = day_start
    for start, end in parsed:
        if start > cursor:
            free_windows.append((cursor, start))
        if end > cursor:
            cursor = end
    if cursor < day_end:
        free_windows.append((cursor, day_end))
    return free_windows


def _energy_level_at(check_time: time, energy_windows: list[Window]) -> str | None:
    for ew in energy_windows:
        if ew.start <= check_time < ew.end:
            return ew.level
    return None


def _segment_free_windows(
    free_windows: list[tuple[time, time]], energy_windows: list[Window]
) -> list[Window]:
    # cut each free window at any energy-window boundary that falls inside it,
    # so every piece ends up with one consistent level
    segments: list[Window] = []
    for free_start, free_end in free_windows:
        boundary_points = {free_start, free_end}
        for ew in energy_windows:
            if free_start < ew.start < free_end:
                boundary_points.add(ew.start)
            if free_start < ew.end < free_end:
                boundary_points.add(ew.end)
        points = sorted(boundary_points)
        for i in range(len(points) - 1):
            seg_start, seg_end = points[i], points[i + 1]
            level = _energy_level_at(seg_start, energy_windows)
            segments.append(Window(seg_start, seg_end, level))
    return segments


def tag_windows(
    free_windows: list[tuple[time, time]], energy_windows: list[Window]
) -> list[Window]:
    # only segments with a level are actually schedulable
    return [w for w in _segment_free_windows(free_windows, energy_windows) if w.level]


def find_uncovered_gaps(
    free_windows: list[tuple[time, time]], energy_windows: list[Window]
) -> list[tuple[time, time]]:
    # the parts of the day we can't reason about because there's no energy label for them
    return [
        (w.start, w.end)
        for w in _segment_free_windows(free_windows, energy_windows)
        if w.level is None
    ]


def build_schedule(
    tasks: list[tuple], windows: list[Window]
) -> tuple[list[tuple], list[str]]:
    # greedy: hardest tasks first (fewest windows they fit), then closest
    # energy match, then smallest leftover as tiebreak (best-fit). falls back
    # to a non-exact level instead of dropping the task if nothing exact fits.
    remaining = [Window(w.start, w.end, w.level) for w in windows]
    tasks_sorted = sorted(tasks, key=lambda row: LEVEL_RANK[row[3]], reverse=True)

    schedule: list[tuple] = []
    unscheduled: list[str] = []

    for _task_id, name, duration, energy_cost in tasks_sorted:
        candidates = [w for w in remaining if w.duration_minutes >= duration]
        if not candidates:
            unscheduled.append(name)
            continue

        def score(w: Window) -> tuple[int, float]:
            level_distance = abs(LEVEL_RANK[w.level] - LEVEL_RANK[energy_cost])
            leftover = w.duration_minutes - duration
            return (level_distance, leftover)

        best_window = min(candidates, key=score)

        task_end_dt = datetime.combine(datetime.today(), best_window.start) + timedelta(
            minutes=duration
        )
        task_end = task_end_dt.time()

        schedule.append((name, best_window.start, task_end, best_window.level))
        best_window.start = task_end

    schedule.sort(key=lambda entry: entry[1])
    return schedule, unscheduled
