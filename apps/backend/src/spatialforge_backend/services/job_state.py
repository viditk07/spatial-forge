"""Formal reconstruction job and stage state transitions."""

from __future__ import annotations

from spatialforge_backend.db.models import JobStatus, StageStatus

JOB_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.PROCESSING, JobStatus.CANCELLED}),
    JobStatus.PROCESSING: frozenset(
        {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.INTERRUPTED}
    ),
    JobStatus.INTERRUPTED: frozenset({JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.CANCELLED}),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.COMPLETED: frozenset(),
}

STAGE_TRANSITIONS: dict[StageStatus, frozenset[StageStatus]] = {
    StageStatus.PENDING: frozenset(
        {StageStatus.RUNNING, StageStatus.CANCELLED, StageStatus.SKIPPED}
    ),
    StageStatus.RUNNING: frozenset(
        {StageStatus.COMPLETED, StageStatus.FAILED, StageStatus.CANCELLED}
    ),
    StageStatus.FAILED: frozenset({StageStatus.RUNNING}),
    StageStatus.CANCELLED: frozenset({StageStatus.RUNNING}),
    StageStatus.COMPLETED: frozenset(),
    StageStatus.SKIPPED: frozenset(),
}


class InvalidTransition(ValueError):
    """Raised when durable state would violate the job lifecycle."""


def validate_job_transition(current: JobStatus, target: JobStatus) -> None:
    if target not in JOB_TRANSITIONS[current]:
        raise InvalidTransition(f"Cannot transition job from {current.value} to {target.value}")


def validate_stage_transition(current: StageStatus, target: StageStatus) -> None:
    if target not in STAGE_TRANSITIONS[current]:
        raise InvalidTransition(f"Cannot transition stage from {current.value} to {target.value}")
