"""Demos for Enum and Literal field selection."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from wizdantic import run_wizard


def demo_1__choices__enum_selection():
    """
    Enum fields display a numbered list. Select by index or by typing the
    value name directly.
    """

    class MagicSchool(str, Enum):
        EVOCATION = "evocation"
        DIVINATION = "divination"
        NECROMANCY = "necromancy"
        ILLUSION = "illusion"

    class Apprentice(BaseModel):
        name: str = Field(description="Apprentice name", default="Serafine Ashveil")
        school: MagicSchool = Field(description="School of magic", default=MagicSchool.DIVINATION)

    run_wizard(Apprentice, title="Enroll an Apprentice")


def demo_2__choices__literal_selection():
    """
    Literal fields work the same way as enums: a numbered list of allowed
    values. Select by index or exact match.
    """

    class RitualCasting(BaseModel):
        ritual_name: str = Field(description="Name of the ritual", default="Veil of Unseeing")
        potency: Literal["minor", "moderate", "greater", "supreme"] = Field(
            description="Ritual potency",
            default="moderate",
        )

    run_wizard(RitualCasting, title="Prepare a Ritual Casting")
