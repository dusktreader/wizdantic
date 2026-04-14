"""Demos for basic scalar field types: strings, integers, floats, and booleans."""

from pydantic import BaseModel, Field

from wizdantic import run_wizard


def demo_1__scalar_types__required_and_defaulted():
    """
    A required field has no default and must be filled in. A defaulted field
    shows its value in brackets. Press Enter to accept the default.
    """

    class Spellbook(BaseModel):
        title: str = Field(description="Spellbook title")
        page_count: int = Field(description="Number of pages", default=300)
        weight_kg: float = Field(description="Weight in kilograms", default=1.2)

    run_wizard(Spellbook)


def demo_2__scalar_types__boolean_confirm():
    """
    Boolean fields use a y/n confirmation prompt. The default (if any)
    is pre-selected.
    """

    class FamiliarSpec(BaseModel):
        name: str = Field(description="Familiar name", default="Cinderpaw")
        can_speak: bool = Field(description="Capable of speech", default=True)
        venomous: bool = Field(description="Produces venom", default=False)

    run_wizard(FamiliarSpec, title="Register a Familiar")
