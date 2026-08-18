from app.integrations.enterprise.vertex_model_armor import managed_model_armor_available


def test_managed_model_armor_not_available_in_repo_environment() -> None:
    assert managed_model_armor_available() is False
