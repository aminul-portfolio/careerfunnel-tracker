from django.db import models


class NoteType(models.TextChoices):
    STRATEGY = "strategy", "Strategy decision"
    RECRUITER = "recruiter", "Recruiter comment"
    INTERVIEW = "interview", "Interview learning"
    CV_CHANGE = "cv_change", "CV / profile change"
    ROLE_TARGETING = "role_targeting", "Role targeting"
    BLOCKER = "blocker", "Blocker"
    LESSON = "lesson", "Lesson learned"
    GENERAL = "general", "General note"
