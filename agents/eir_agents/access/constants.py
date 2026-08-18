"""Managed Patient Access constants. No credentials."""

SYNTHETIC_USER_ID = "patient-synthetic-001"
ALLOWED_SYNTHETIC_USERS = frozenset({SYNTHETIC_USER_ID})
DEFAULT_API_BASE_URL = "https://eir-api-658898892127.us-central1.run.app"
GEMINI_MODEL = "gemini-3.5-flash"
RUNTIME_DISPLAY_NAME = "eir-patient-access"
PREFERRED_CLINIC_KEY = "preferred_clinic"
PREFERRED_TIME_KEY = "preferred_time_of_day"
SAFE_MEMORY_KEYS = frozenset({PREFERRED_CLINIC_KEY, PREFERRED_TIME_KEY})
PROHIBITED_MEMORY_FIELDS = frozenset(
    {
        "transcript",
        "phone",
        "symptom",
        "symptoms",
        "medication",
        "fhir",
        "password",
        "secret",
        "prompt",
    }
)
