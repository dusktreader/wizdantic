"""Demos for collection types: lists, tuples, sets, and dicts."""

from pydantic import BaseModel, Field

from wizdantic import run_wizard


def demo_1__collections__list_input():
    """
    List fields accept JSON array syntax or comma-separated values.
    Both `["a", "b"]` and `a, b` work. Each item is validated
    against the list's element type.
    """

    class Coven(BaseModel):
        coven_name: str = Field(description="Coven name", default="The Ashen Circle")
        members: list[str] = Field(description="Member names")
        candle_counts: list[int] = Field(description="Candles per ritual circle", default_factory=list)

    run_wizard(Coven, title="Register a Coven")


def demo_2__collections__tuple_input():
    """
    Homogeneous tuples (`tuple[T, ...]`) accept JSON or CSV, just like
    lists. Fixed-length tuples (`tuple[T1, T2]`) also accept JSON or CSV,
    but reject input that does not have exactly the right number of elements.
    """

    class AstralPath(BaseModel):
        path_name: str = Field(description="Path name", default="The Verdant Meridian")
        ley_line_strengths: tuple[float, ...] = Field(description="Ley line strength readings")
        origin_and_tier: tuple[str, int] = Field(description="Origin realm name and tier number")

    run_wizard(AstralPath, title="Chart an Astral Path")


def demo_3__collections__set_and_dict():
    """
    Set fields accept JSON arrays or comma-separated values. Duplicate
    entries are rejected -- all elements must be unique. Dict fields accept
    JSON objects or `key:value, key:value` notation.
    """

    class OmenReport(BaseModel):
        report_title: str = Field(description="Report title", default="Third Moon Convergence")
        known_portents: set[str] = Field(description="Observed portents", default_factory=set)
        reagent_sources: dict[str, str] = Field(
            description="Reagent name to source location mapping",
            default_factory=dict,
        )

    run_wizard(OmenReport, title="File an Omen Report")
