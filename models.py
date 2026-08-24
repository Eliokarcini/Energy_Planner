from datetime import time
from typing import Literal, Tuple

from pydantic import BaseModel, Field, model_validator

EnergyLevel = Literal["Low", "Medium", "High"]


class FixedCommitment(BaseModel):
    """Something locked into your day that can't move: class, gym, commute."""

    name: str = Field(min_length=1)
    start: time
    end: time

    @model_validator(mode="after")
    def end_after_start(self) -> "FixedCommitment":
        if self.end <= self.start:
            raise ValueError("End time must be after start time")
        return self


class FlexibleTask(BaseModel):
    """Something you need to get done today, tagged by how much energy it takes."""

    name: str = Field(min_length=1)
    duration_minutes: float = Field(gt=0)
    energy_cost: EnergyLevel


class EnergyWindow(BaseModel):
    """A stretch of your day, labeled by how sharp vs. drained you tend to be."""

    start: time
    end: time
    level: EnergyLevel

    @model_validator(mode="after")
    def end_after_start(self) -> "EnergyWindow":
        if self.end <= self.start:
            raise ValueError("End time must be after start time")
        return self


class ScheduledTask(BaseModel):
    name: str
    start: time
    end: time
    level: EnergyLevel


class ScheduleResult(BaseModel):
    scheduled: list[ScheduledTask]
    unscheduled: list[str]
    uncovered_windows: list[Tuple[time, time]]
