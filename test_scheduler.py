from datetime import time

import pytest
from pydantic import ValidationError

from models import EnergyWindow, FixedCommitment, FlexibleTask
from scheduler import (
    Window,
    build_schedule,
    compute_free_windows,
    find_uncovered_gaps,
    tag_windows,
)


def test_fixed_commitment_rejects_end_before_start():
    with pytest.raises(ValidationError):
        FixedCommitment(name="Class", start=time(10, 0), end=time(9, 0))


def test_fixed_commitment_rejects_empty_name():
    with pytest.raises(ValidationError):
        FixedCommitment(name="", start=time(9, 0), end=time(10, 0))


def test_flexible_task_rejects_invalid_energy_cost():
    with pytest.raises(ValidationError):
        FlexibleTask(name="Task", duration_minutes=30, energy_cost="Extreme")


def test_flexible_task_rejects_zero_duration():
    with pytest.raises(ValidationError):
        FlexibleTask(name="Task", duration_minutes=0, energy_cost="Low")


def test_energy_window_rejects_end_before_start():
    with pytest.raises(ValidationError):
        EnergyWindow(start=time(14, 0), end=time(10, 0), level="Medium")


def test_compute_free_windows_splits_around_a_commitment():
    commitments = [(1, "Class", "09:00:00", "10:30:00")]
    free = compute_free_windows(commitments, time(8, 0), time(12, 0))
    assert free == [(time(8, 0), time(9, 0)), (time(10, 30), time(12, 0))]


def test_compute_free_windows_handles_no_commitments():
    free = compute_free_windows([], time(8, 0), time(12, 0))
    assert free == [(time(8, 0), time(12, 0))]


def test_compute_free_windows_handles_back_to_back_commitments():
    # back-to-back, not overlapping -- shouldn't leave a gap between them
    commitments = [
        (1, "Class", "09:00:00", "10:00:00"),
        (2, "Gym", "10:00:00", "11:00:00"),
    ]
    free = compute_free_windows(commitments, time(9, 0), time(12, 0))
    assert free == [(time(11, 0), time(12, 0))]


def test_tag_windows_splits_at_energy_boundaries():
    free = [(time(8, 0), time(12, 0))]
    energy_windows = [
        Window(time(6, 0), time(10, 0), "High"),
        Window(time(10, 0), time(14, 0), "Medium"),
    ]
    tagged = tag_windows(free, energy_windows)
    assert [w.level for w in tagged] == ["High", "Medium"]
    assert tagged[0] == Window(time(8, 0), time(10, 0), "High")
    assert tagged[1] == Window(time(10, 0), time(12, 0), "Medium")


def test_find_uncovered_gaps_flags_time_with_no_energy_window():
    free = [(time(8, 0), time(12, 0))]
    energy_windows = [Window(time(9, 0), time(10, 0), "Medium")]
    gaps = find_uncovered_gaps(free, energy_windows)
    assert (time(8, 0), time(9, 0)) in gaps
    assert (time(10, 0), time(12, 0)) in gaps


def test_build_schedule_prefers_exact_energy_match():
    windows = [
        Window(time(8, 0), time(9, 0), "High"),
        Window(time(9, 0), time(10, 0), "Low"),
    ]
    tasks = [(1, "Deep Work", 30, "High")]
    schedule, unscheduled = build_schedule(tasks, windows)
    assert unscheduled == []
    assert schedule[0][3] == "High"


def test_build_schedule_falls_back_to_closest_level_when_no_exact_match():
    # only a Low window exists, so the High task has to take it or go unscheduled
    windows = [Window(time(9, 0), time(10, 0), "Low")]
    tasks = [(1, "Hard Task", 30, "High")]
    schedule, unscheduled = build_schedule(tasks, windows)
    assert unscheduled == []
    assert schedule[0][3] == "Low"


def test_build_schedule_prioritizes_high_energy_tasks_first():
    windows = [
        Window(time(8, 0), time(9, 0), "High"),
        Window(time(9, 0), time(10, 0), "Low"),
    ]
    tasks = [
        (1, "Easy Task", 30, "Low"),
        (2, "Hard Task", 30, "High"),
    ]
    schedule, unscheduled = build_schedule(tasks, windows)
    assert unscheduled == []
    by_name = {name: level for name, _start, _end, level in schedule}
    assert by_name["Hard Task"] == "High"
    assert by_name["Easy Task"] == "Low"


def test_build_schedule_reports_unscheduled_when_nothing_fits():
    windows = [Window(time(9, 0), time(9, 10), "High")]
    tasks = [(1, "Long Task", 60, "High")]
    schedule, unscheduled = build_schedule(tasks, windows)
    assert schedule == []
    assert unscheduled == ["Long Task"]


def test_build_schedule_shrinks_window_after_placing_a_task():
    windows = [Window(time(8, 0), time(9, 0), "High")]
    tasks = [
        (1, "Task A", 30, "High"),
        (2, "Task B", 30, "High"),
    ]
    schedule, unscheduled = build_schedule(tasks, windows)
    assert unscheduled == []
    assert len(schedule) == 2
    starts = sorted(entry[1] for entry in schedule)
    assert starts == [time(8, 0), time(8, 30)]
