from django.core.management.base import BaseCommand

from ...models import SkillEntry

VERIFIED_DEFAULT_NOTES = (
    "Seeded from approved CV tailoring rules. "
    "Verify project-specific evidence before public use."
)
LEARNING_TARGET_NOTES = (
    "Learning target only. Developing skill - "
    "not yet portfolio-evidenced or ready to claim as verified."
)


SEED_ENTRIES = [
    {
        "skill_name": "Python",
        "category": SkillEntry.Category.PROGRAMMING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Pandas",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "NumPy",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "SQL",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Django / Django ORM",
        "category": SkillEntry.Category.PROGRAMMING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "REST APIs",
        "category": SkillEntry.Category.PROGRAMMING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Git / GitHub",
        "category": SkillEntry.Category.PROGRAMMING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "CSV / Excel / JSON ingestion",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "ETL workflows",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "KPI dashboards",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Data visualisation",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "BI-ready CSV exports",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Metric definitions",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Data-quality checks",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Lineage documentation",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "dbt",
        "category": SkillEntry.Category.ANALYTICS_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": (
            "Seeded from approved CV tailoring rules. "
            "DuckDB default local target + optional BigQuery validation target; "
            "not dbt Cloud or production orchestration. "
            "Verify project-specific evidence before public use."
        ),
    },
    {
        "skill_name": "DuckDB",
        "category": SkillEntry.Category.ANALYTICS_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "BigQuery",
        "category": SkillEntry.Category.ANALYTICS_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": (
            "Seeded from approved CV tailoring rules. "
            "Optional dbt validation target only; not production warehouse. "
            "Verify project-specific evidence before public use."
        ),
    },
    {
        "skill_name": "GitHub Actions / CI",
        "category": SkillEntry.Category.PROGRAMMING,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Power BI",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": (
            "Seeded from approved CV tailoring rules. "
            "Desktop authoring, star-schema modelling, DAX, and Service publishing; "
            "not gateway, RLS, or admin. "
            "Verify project-specific evidence before public use."
        ),
    },
    {
        "skill_name": "Excel / Power Query / DAX / VBA / Pivot Tables",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Plotly / Matplotlib / Chart.js / Streamlit",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Docker",
        "category": SkillEntry.Category.CLOUD,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": (
            "Seeded from approved CV tailoring rules. "
            "Local reviewer workflow only; not production deployment or Kubernetes. "
            "Verify project-specific evidence before public use."
        ),
    },
    {
        "skill_name": "FX operations",
        "category": SkillEntry.Category.DOMAIN,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "AML procedures",
        "category": SkillEntry.Category.DOMAIN,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Multi-currency reconciliation",
        "category": SkillEntry.Category.DOMAIN,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Operational reporting",
        "category": SkillEntry.Category.DOMAIN,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "FinTech analytics",
        "category": SkillEntry.Category.DOMAIN,
        "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
        "notes": VERIFIED_DEFAULT_NOTES,
    },
    {
        "skill_name": "Snowflake",
        "category": SkillEntry.Category.CLOUD,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
    {
        "skill_name": "Airflow",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
    {
        "skill_name": "Tableau",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
    {
        "skill_name": "Looker",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
    {
        "skill_name": "Microsoft Fabric",
        "category": SkillEntry.Category.CLOUD,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
    {
        "skill_name": "Azure",
        "category": SkillEntry.Category.CLOUD,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
    {
        "skill_name": "SSRS",
        "category": SkillEntry.Category.BUSINESS_INTELLIGENCE,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
    {
        "skill_name": "Databricks",
        "category": SkillEntry.Category.DATA_ENGINEERING,
        "evidence_level": SkillEntry.EvidenceLevel.LEARNING_TARGET,
        "notes": LEARNING_TARGET_NOTES,
    },
]


class Command(BaseCommand):
    help = "Seed the private Skill Ledger with approved Sprint 70 skill entries."

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0

        for seed_entry in SEED_ENTRIES:
            skill_name = seed_entry["skill_name"]
            entry, created = SkillEntry.objects.get_or_create(
                skill_name=skill_name,
                defaults={
                    "category": seed_entry["category"],
                    "evidence_level": seed_entry["evidence_level"],
                    "sprint_reference": "",
                    "project_link": "",
                    "notes": seed_entry["notes"],
                    "visibility": SkillEntry.Visibility.PRIVATE,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created: {entry.skill_name}")
            else:
                existing_count += 1
                self.stdout.write(f"Existing, skipped: {entry.skill_name}")

        total_processed = created_count + existing_count
        self.stdout.write(f"Created: {created_count}")
        self.stdout.write(f"Existing: {existing_count}")
        self.stdout.write(f"Total processed: {total_processed}")
