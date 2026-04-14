"""
Advanced wizdantic usage.

Exercises the trickier type support: enums, literals, secrets, optional fields,
lists, tuples, sets, dicts, nested models, section grouping, custom hints, and
custom parsers.

Run it: `uv run python examples/advanced_example.py`
"""

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr

from wizdantic import WizardLore, WizardAborted, run_wizard


class Tradition(str, Enum):
    EVOCATION = "evocation"
    DIVINATION = "divination"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class Sanctum(BaseModel):
    """A wizard's sanctum. Prompted as a nested sub-wizard."""

    name: str = Field(description="Sanctum name")
    realm: str = Field(description="Realm it resides in")
    wards: int = Field(description="Number of protective wards", default=3)


def parse_gold(raw: str) -> int:
    """
    Parse a gold string like '10,000 gp' into an int.

    This is a custom parser provided via `WizardLore`. After parsing, the wizard
    validates the result against any type-level constraints on the field (e.g.
    `ge=1, le=100_000`). Entering `200,000 gp` parses fine but fails the upper
    bound check and re-prompts.
    """
    return int(raw.replace(",", "").replace(" gp", "").strip())


class RitualInscription(BaseModel):
    """
    A complex model for inscribing a ritual.

    This example demonstrates most of wizdantic's features including:
    - most of the supported types
    - sections to group related fields
    - a nested model
    - custom hints
    - custom parsers with inline constraint validation (see `casting_fee`)
    """

    # --- Wizard identity ---
    wizard_name: Annotated[str, WizardLore(section="Wizard")] = Field(
        description="Your registered wizard name",
    )
    registry_id: Annotated[int, WizardLore(section="Wizard")] = Field(
        description="Conclave registry number",
    )
    tradition: Annotated[Tradition, WizardLore(section="Wizard")] = Field(
        description="Magical tradition",
        default=Tradition.EVOCATION,
    )

    # --- Ritual details ---
    ritual_name: Annotated[str, WizardLore(section="Ritual")] = Field(
        description="Name of the ritual",
    )
    casting_fee: Annotated[
        int,
        WizardLore(
            section="Ritual",
            hint="e.g. 10,000 gp",
            parser=parse_gold,
        ),
    ] = Field(
        description="Casting fee in gold pieces",
        ge=1,
        le=100_000,
    )
    urgency: Annotated[
        Literal["low", "moderate", "urgent", "dire"],
        WizardLore(section="Ritual"),
    ] = Field(
        description="Urgency of the ritual",
        default="moderate",
    )
    binding_required: Annotated[bool, WizardLore(section="Ritual")] = Field(
        description="Containment circle required",
        default=True,
    )

    # --- Casting site (nested model) ---
    casting_sanctum: Annotated[Sanctum, WizardLore(section="Casting Site")] = Field(
        description="Sanctum where the ritual will be performed",
    )

    # --- Preparation: collection types ---
    required_reagents: Annotated[
        list[str],
        WizardLore(section="Preparation"),
    ] = Field(
        description="Reagents required for the ritual",
        default_factory=list,
    )
    warded_realms: Annotated[
        set[str],
        WizardLore(section="Preparation"),
    ] = Field(
        description="Realms warded against this ritual",
        default_factory=set,
    )
    prior_attempts: Annotated[
        dict[str, int],
        WizardLore(section="Preparation"),
    ] = Field(
        description="Previous casters and attempt counts",
        default_factory=dict,
    )
    ley_line_coords: Annotated[
        tuple[float, ...],
        WizardLore(section="Preparation"),
    ] = Field(
        description="Ley line intersection coordinates",
        default_factory=tuple,
    )

    # --- Unsectioned fields (goes to "Other") ---
    sealed_incantation: SecretStr | None = Field(
        description="Sealed incantation (kept private)",
        default=None,
    )
    alias: str | None = Field(
        description="Wizard alias for this inscription",
        default=None,
    )


if __name__ == "__main__":
    try:
        run_wizard(RitualInscription, title="New Ritual Inscription")
    except WizardAborted:
        pass
