import os
from datetime import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import database as db
import scheduler
from models import (
    EnergyWindow,
    FixedCommitment,
    FlexibleTask,
    ScheduledTask,
    ScheduleResult,
)

app = FastAPI(title="Energy-Aware Daily Planner")

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

DAY_START = time(5, 0)
DAY_END = time(23, 59)


@app.post("/commitments")
def create_commitment(commitment: FixedCommitment):
    for row in db.load_commitments():
        existing_start = time.fromisoformat(row[2])
        existing_end = time.fromisoformat(row[3])
        if db.commitments_overlap(commitment.start, commitment.end, existing_start, existing_end):
            raise HTTPException(400, f"Overlaps with existing commitment '{row[1]}'")
    commitment_id = db.save_commitment(commitment.name, str(commitment.start), str(commitment.end))
    return {"id": commitment_id, **commitment.model_dump(mode="json")}


@app.get("/commitments")
def get_commitments():
    return [
        {"id": row[0], "name": row[1], "start": row[2], "end": row[3]}
        for row in db.load_commitments()
    ]


@app.delete("/commitments/{commitment_id}")
def remove_commitment(commitment_id: int):
    db.delete_commitment(commitment_id)
    return {"deleted": commitment_id}


@app.post("/tasks")
def create_task(task: FlexibleTask):
    task_id = db.save_task(task.name, task.duration_minutes, task.energy_cost)
    return {"id": task_id, **task.model_dump(mode="json")}


@app.get("/tasks")
def get_tasks():
    return [
        {"id": row[0], "name": row[1], "duration_minutes": row[2], "energy_cost": row[3]}
        for row in db.load_tasks()
    ]


@app.delete("/tasks/{task_id}")
def remove_task(task_id: int):
    db.delete_task(task_id)
    return {"deleted": task_id}


@app.post("/energy-windows")
def create_energy_window(window: EnergyWindow):
    window_id = db.save_energy_window(str(window.start), str(window.end), window.level)
    return {"id": window_id, **window.model_dump(mode="json")}


@app.get("/energy-windows")
def get_energy_windows():
    return [
        {"id": row[0], "start": row[1], "end": row[2], "level": row[3]}
        for row in db.load_energy_windows()
    ]


@app.delete("/energy-windows/{window_id}")
def remove_energy_window(window_id: int):
    db.delete_energy_window(window_id)
    return {"deleted": window_id}


@app.post("/schedule", response_model=ScheduleResult)
def generate_schedule():
    commitments = db.load_commitments()
    tasks = db.load_tasks()
    energy_window_rows = db.load_energy_windows()

    energy_windows = [
        scheduler.Window(time.fromisoformat(row[1]), time.fromisoformat(row[2]), row[3])
        for row in energy_window_rows
    ]

    free_windows = scheduler.compute_free_windows(commitments, DAY_START, DAY_END)
    tagged_windows = scheduler.tag_windows(free_windows, energy_windows)
    uncovered = scheduler.find_uncovered_gaps(free_windows, energy_windows)

    schedule, unscheduled = scheduler.build_schedule(tasks, tagged_windows)

    return ScheduleResult(
        scheduled=[
            ScheduledTask(name=name, start=start, end=end, level=level)
            for name, start, end, level in schedule
        ],
        unscheduled=unscheduled,
        uncovered_windows=uncovered,
    )
