from .models import SkillEntry


def get_skill_ledger_evidence_summary(user):
    owned_entries = SkillEntry.objects.for_user(user)
    counts = {
        SkillEntry.EvidenceLevel.VERIFIED: 0,
        SkillEntry.EvidenceLevel.LEARNING_TARGET: 0,
        SkillEntry.EvidenceLevel.STUDYING: 0,
        SkillEntry.EvidenceLevel.NO_EVIDENCE: 0,
    }
    rows = owned_entries.values("evidence_level")
    for row in rows:
        evidence_level = row["evidence_level"]
        if evidence_level in counts:
            counts[evidence_level] += 1

    verified_entries = list(
        owned_entries.filter(evidence_level=SkillEntry.EvidenceLevel.VERIFIED).order_by(
            "-last_updated",
            "-pk",
        )[:5],
    )
    return {
        "counts": counts,
        "verified_entries": verified_entries,
        "total_entries": sum(counts.values()),
    }
