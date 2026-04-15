"""
Instance-seeding: run the wizard over an already-populated model.

Pass an existing model instance to `run_wizard` (or `Wizard`) via the
`instance` parameter. Each field's current value becomes the prompt default,
so the user only needs to change what they want to update. A fresh model
instance is always returned; the original is never modified.

Run it: `uv run python examples/instance_example.py`
"""

from enum import Enum

from pydantic import BaseModel, Field, SecretStr

from wizdantic import WizardAborted, run_wizard


class Tradition(str, Enum):
    EVOCATION = "evocation"
    CONJURATION = "conjuration"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class Sanctum(BaseModel):
    name: str = Field(description="Sanctum name")
    realm: str = Field(description="Realm it resides in", default="The Twilight Marches")
    wards: int = Field(description="Number of protective wards", default=3)


class WizardProfile(BaseModel):
    name: str = Field(description="Registered wizard name")
    tradition: Tradition = Field(description="Magical tradition", default=Tradition.EVOCATION)
    power_level: int = Field(description="Arcane power level", default=100)
    binding_word: SecretStr | None = Field(description="Binding word (kept private)", default=None)
    known_spells: list[str] = Field(description="Known spells", default_factory=list)
    sanctum: Sanctum = Field(description="Primary sanctum")


if __name__ == "__main__":
    existing = WizardProfile(
        name="Elara Nighthollow",
        tradition=Tradition.CONJURATION,
        power_level=850,
        binding_word=SecretStr("veilstone"),
        known_spells=["Arcane Bolt", "Misty Step"],
        sanctum=Sanctum(name="The Obsidian Spire", realm="Embervault", wards=7),
    )

    print("Existing profile loaded. Running wizard to revise it...")
    print()

    try:
        updated = run_wizard(WizardProfile, instance=existing, title="Update Wizard Profile")
    except WizardAborted:
        pass
    else:

        def _value(v: object) -> object:
            return v.get_secret_value() if isinstance(v, SecretStr) else v

        diffs = [
            field
            for field in WizardProfile.model_fields
            if _value(getattr(existing, field)) != _value(getattr(updated, field))
        ]
        print()
        if diffs:
            print("--- Changed fields ---")
            for field in diffs:
                print(f"  {field}:")
                print(f"    before: {getattr(existing, field)}")
                print(f"    after : {getattr(updated, field)}")
        else:
            print("No fields changed.")
