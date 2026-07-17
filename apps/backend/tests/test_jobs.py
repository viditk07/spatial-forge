from __future__ import annotations

import pytest

from spatialforge_backend.db.models import JobStatus, StageStatus
from spatialforge_backend.services.job_state import (
    InvalidTransition,
    validate_job_transition,
    validate_stage_transition,
)


def test_valid_job_lifecycle() -> None:
    validate_job_transition(JobStatus.QUEUED, JobStatus.PROCESSING)
    validate_job_transition(JobStatus.PROCESSING, JobStatus.COMPLETED)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (JobStatus.COMPLETED, JobStatus.PROCESSING),
        (JobStatus.CANCELLED, JobStatus.QUEUED),
        (JobStatus.QUEUED, JobStatus.COMPLETED),
    ],
)
def test_invalid_job_transition_is_rejected(current: JobStatus, target: JobStatus) -> None:
    with pytest.raises(InvalidTransition):
        validate_job_transition(current, target)


def test_only_failed_or_cancelled_stage_can_retry() -> None:
    validate_stage_transition(StageStatus.FAILED, StageStatus.RUNNING)
    validate_stage_transition(StageStatus.CANCELLED, StageStatus.RUNNING)
    with pytest.raises(InvalidTransition):
        validate_stage_transition(StageStatus.COMPLETED, StageStatus.RUNNING)
