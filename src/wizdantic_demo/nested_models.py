"""Demos for nested BaseModel fields and list[BaseModel] sub-wizards."""

from pydantic import BaseModel, Field

from wizdantic import run_wizard


def demo_1__nested_models__single_nested():
    """
    When a field's type is another BaseModel, the wizard launches a
    sub-wizard for that model. A magenta section rule marks the nesting.
    """

    class Sanctum(BaseModel):
        name: str = Field(description="Sanctum name", default="The Obsidian Spire")
        realm: str = Field(description="Realm it resides in", default="The Twilight Marches")
        wards: int = Field(description="Number of protective wards", default=0)

    class Archmage(BaseModel):
        name: str = Field(description="Archmage name", default="Valdris Mourn")
        sanctum: Sanctum = Field(description="Personal sanctum")

    run_wizard(Archmage, title="Register an Archmage")


def demo_2__nested_models__list_of_models():
    """
    When a field is `list[BaseModel]`, the wizard runs a sub-wizard
    for each item and asks "Add another?" after each one. This is how
    you build up a list of complex objects interactively.
    """

    class Apprentice(BaseModel):
        name: str = Field(description="Apprentice name", default="Lyra Duskfen")
        specialty: str = Field(description="Area of magical study", default="Abjuration")

    class Conclave(BaseModel):
        conclave_name: str = Field(description="Conclave name", default="The Ember Council")
        apprentices: list[Apprentice] = Field(description="Enrolled apprentices")

    run_wizard(Conclave, title="Convene a Conclave")
