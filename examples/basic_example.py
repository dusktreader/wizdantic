"""
Basic wizdantic usage.

A simple model with a few fields, defaults, and a required field.
Run it: `uv run python examples/basic_example.py`
"""

from pydantic import BaseModel, Field

from wizdantic import run_wizard


class Spellbook(BaseModel):
    """
    A basic model describing a spell book.

    This example demonstrates basic wizdantic funcitionality.
    """

    title: str = Field(description="Spellbook title")
    page_count: int = Field(description="Number of pages", default=300)
    ink_weight_kg: float = Field(description="Weight of enchanted ink in kilograms", default=0.4)
    cursed: bool = Field(description="Bound with a curse", default=False)


if __name__ == "__main__":
    run_wizard(Spellbook, title="Register a Spellbook")
