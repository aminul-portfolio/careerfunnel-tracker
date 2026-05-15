"""Canonical role-fit scoring constants shared by Job Posting Analyzer and Smart Review."""

TARGET_TITLES = [
    "data analyst",
    "junior data analyst",
    "graduate data analyst",
    "reporting analyst",
    "bi analyst",
    "business intelligence analyst",
    "insights analyst",
    "finance data analyst",
    "operations data analyst",
]

TARGET_TITLES_AE_STRETCH = [
    "analytics engineer",
    "junior analytics engineer",
    "graduate analytics engineer",
    "data engineer",
    "junior data engineer",
    "analytics platform engineer",
]

BAD_TITLE_WORDS = [
    "senior",
    "lead",
    "principal",
    "manager",
    "head of",
    "data scientist",
    "machine learning",
    "quant",
    "director",
]

SENIOR_SIGNALS = [
    "senior",
    "lead",
    "principal",
    "head of",
    "manager",
    "5+ years",
    "minimum 5",
    "3+ years",
    "minimum 3",
]

GOOD_LOCATION_WORDS = [
    "london",
    "croydon",
    "south london",
    "remote uk",
    "hybrid london",
    "purley",
]

GOOD_SKILLS = [
    "python",
    "sql",
    "excel",
    "reporting",
    "dashboard",
    "power bi",
    "analytics",
    "pandas",
    "data analysis",
    "etl",
    "kpi",
    "stakeholder",
    "finance",
    "reconciliation",
]

DEAL_BREAKERS = [
    "sc clearance",
    "dv clearance",
    "security clearance",
    "cima",
    "acca",
    "aca",
    "10+ years",
    "ten years",
    "principal",
    "head of data",
    "director",
]

LEARNING_TARGETS = [
    "dbt",
    "airflow",
    "spark",
    "kafka",
    "snowflake",
    "bigquery",
    "aws redshift",
    "redshift",
    "databricks",
]
