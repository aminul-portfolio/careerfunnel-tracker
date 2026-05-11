from django.db import models


class FunnelDiagnosis(models.TextChoices):
    LOW_ACTIVITY = "low_activity", "Low activity / consistency issue"
    CV_TARGETING = "cv_targeting", "CV / targeting issue"
    MESSAGING_FIT = "messaging_fit", "Messaging / role-fit issue"
    SCREENING = "screening", "Screening-call issue"
    INTERVIEW = "interview", "Interview performance issue"
    STRATEGY_WORKING = "strategy_working", "Strategy working"
    UNKNOWN = "unknown", "Unknown / not enough data"


class WeeklyMood(models.TextChoices):
    STRONG = "strong", "Strong"
    STEADY = "steady", "Steady"
    MIXED = "mixed", "Mixed"
    LOW = "low", "Low"
    BLOCKED = "blocked", "Blocked"
