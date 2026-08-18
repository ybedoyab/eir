from eir_agents.access.constants import PROHIBITED_MEMORY_FIELDS, SAFE_MEMORY_KEYS


def memory_payload_is_safe(payload: dict) -> bool:
    blob = " ".join(str(value).lower() for value in payload.values())
    if any(field in blob for field in PROHIBITED_MEMORY_FIELDS):
        return False
    keys = {str(key) for key in payload}
    return keys <= SAFE_MEMORY_KEYS or keys <= SAFE_MEMORY_KEYS | {"user_id"}
