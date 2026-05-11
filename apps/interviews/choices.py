from django.db import models


class InterviewStage(models.TextChoices):
    SCREENING = "screening", "Screening call"
    TECHNICAL = "technical", "Technical screen"
    FIRST = "first", "First interview"
    FINAL = "final", "Final interview"
    TASK = "task", "Take-home / task"


class InterviewOutcome(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    PASSED = "passed", "Passed"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
