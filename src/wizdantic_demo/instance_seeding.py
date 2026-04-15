"""Demos for running the wizard over an already-populated model instance."""

from enum import Enum

from pydantic import BaseModel, Field, SecretStr

from wizdantic import run_wizard


class Tradition(str, Enum):
    EVOCATION = "evocation"
    CONJURATION = "conjuration"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


def demo_1__instance_seeding__scalar_fields():
    """
    Pass an existing model instance to pre-fill every prompt with its current
    value. The user can accept all defaults unchanged, or edit individual fields.
    A new instance is always returned; the original is never modified.

    Here a `WizardProfile` is created up front and passed to `run_wizard`.
    Every prompt opens with the profile's current value as the default.
    """

    class WizardProfile(BaseModel):
        name: str = Field(description="Registered wizard name", default="Elara Nighthollow")
        power_level: int = Field(description="Arcane power level", default=100)
        is_archmagus: bool = Field(description="Holds Archmagus rank", default=False)

    existing = WizardProfile(name="Elara Nighthollow", power_level=850, is_archmagus=True)
    run_wizard(WizardProfile, instance=existing, title="Revise Wizard Profile")


def demo_2__instance_seeding__nested_model():
    """
    Instance values flow into nested sub-wizards too. Each field of the nested
    model is pre-filled from the corresponding value on the existing nested
    instance, so the user only needs to change what has actually changed.
    """

    class Sanctum(BaseModel):
        name: str = Field(description="Sanctum name", default="The Obsidian Spire")
        realm: str = Field(description="Realm it resides in", default="Embervault")
        wards: int = Field(description="Number of protective wards", default=3)

    class Archmage(BaseModel):
        name: str = Field(description="Archmage name", default="Valdris Mourn")
        sanctum: Sanctum = Field(description="Primary sanctum")

    existing = Archmage(
        name="Valdris Mourn",
        sanctum=Sanctum(name="The Ashen Vault", realm="Gloomreach", wards=12),
    )
    run_wizard(Archmage, instance=existing, title="Update Archmage Registry")


def demo_3__instance_seeding__enum_and_secret():
    """
    Enum fields show the instance's current selection as the highlighted default.
    Secret fields show the masked placeholder; accepting it keeps the original
    secret value intact without ever exposing the raw string.
    """

    class Warlock(BaseModel):
        shadow_name: str = Field(description="Shadow title", default="Mordain the Hollow")
        tradition: Tradition = Field(description="Magical tradition", default=Tradition.NECROMANCY)
        true_name: SecretStr = Field(description="True identity (kept private)")

    existing = Warlock(
        shadow_name="Mordain the Hollow",
        tradition=Tradition.NECROMANCY,
        true_name=SecretStr("ashthorn"),
    )
    run_wizard(Warlock, instance=existing, title="Amend Warlock Binding")
