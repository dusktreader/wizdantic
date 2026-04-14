"""Demos for Optional fields and SecretStr masked input."""

from pydantic import BaseModel, Field, SecretStr

from wizdantic import run_wizard


def demo_1__optional_and_secret__optional_fields():
    """
    Optional fields accept empty input, which the wizard interprets as None.
    The prompt shows "(empty for None)" so the user knows they can skip it.
    """

    class HerbalistRecord(BaseModel):
        herb_name: str = Field(description="Herb name", default="Moonwort")
        common_name: str | None = Field(description="Common name", default=None)
        native_region: str | None = Field(description="Native region", default=None)
        potency_rating: int | None = Field(description="Potency rating (1-10)", default=None)

    run_wizard(HerbalistRecord, title="Record an Herb")


def demo_2__optional_and_secret__secret_fields():
    """
    SecretStr fields mask the input (like a password prompt). The value
    is stored securely and shown as "****" in the summary table.

    If the field has a default, the prompt shows "********" as a
    placeholder. Pressing Enter keeps the original default.
    """

    class ArcaneVault(BaseModel):
        keeper_name: str = Field(description="Vault keeper name", default="Mira Stoneclasp")
        binding_word: SecretStr = Field(description="Binding word to open the vault")
        failsafe_phrase: SecretStr | None = Field(description="Emergency failsafe phrase", default=None)

    run_wizard(ArcaneVault, title="Seal an Arcane Vault")
