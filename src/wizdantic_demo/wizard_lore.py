"""Demos for WizardLore: sections, custom hints, and custom parsers."""

from typing import Annotated

from pydantic import BaseModel, Field

from wizdantic import WizardLore, run_wizard


def demo_1__wizard_lore__sections():
    """
    Annotate fields with `WizardLore(section="...")` to group them under
    named section headings. Sections appear in the order they are first
    encountered. Fields without a section land under "Other" at the end.
    """

    class RitualInscription(BaseModel):
        ritual_name: Annotated[str, WizardLore(section="Ritual")] = Field(
            description="Name of the ritual",
            default="Rite of the Pale Flame",
        )
        tradition: Annotated[str, WizardLore(section="Ritual")] = Field(
            description="Magical tradition",
            default="Umbral Weaving",
        )
        casting_fee: Annotated[int, WizardLore(section="Terms")] = Field(
            description="Casting fee in gold pieces",
            default=50,
        )
        duration_hours: Annotated[int, WizardLore(section="Terms")] = Field(
            description="Duration of the ritual in hours",
            default=1,
        )
        notes: str = Field(description="Additional notes", default="")

    run_wizard(RitualInscription, title="Inscribe a Ritual")


def demo_2__wizard_lore__custom_hints():
    """
    `WizardLore(hint="...")` replaces the auto-generated format hint in
    the prompt. Use it to give the user context about expected input
    format or valid ranges.
    """

    class AetherReading(BaseModel):
        nexus: Annotated[str, WizardLore(hint="e.g. Veilstone-3")] = Field(
            description="Nexus designation",
            default="Veilstone-3",
        )
        flux_intensity: Annotated[float, WizardLore(hint="0.0 to 100.0")] = Field(
            description="Aether flux intensity",
            default=42.7,
        )
        tags: Annotated[list[str], WizardLore(hint="space-separated, e.g. unstable cursed")] = Field(
            description="Classification tags",
            default_factory=list,
        )

    run_wizard(AetherReading, title="Record an Aether Reading")


def demo_3__wizard_lore__custom_parsers():
    """
    `WizardLore(parser=func)` hands the raw string to your function instead of
    `TypeAdapter`. The parser handles format conversion; the wizard then validates
    the result against any type-level constraints on the field (ge, le,
    min_length, etc.) and retries if they fail.

    Here, `gold_parser` strips commas and a "gp" suffix so the user can type
    "1,000 gp" instead of "1000". The `amount` field also has `ge=1, le=50_000`,
    so entering "200,000 gp" parses fine but is immediately rejected with a
    constraint error. `tag_parser` splits on whitespace and lowercases each token.
    """

    def gold_parser(raw: str) -> int:
        return int(raw.replace(",", "").replace(" gp", "").strip())

    def tag_parser(raw: str) -> list[str]:
        return [tag.strip().lower() for tag in raw.split() if tag.strip()]

    class LedgerEntry(BaseModel):
        description: str = Field(description="Transaction description", default="Moonfire candle procurement")
        amount: Annotated[
            int,
            WizardLore(hint="e.g. 1,000 gp (max 50,000)", parser=gold_parser),
        ] = Field(
            description="Amount in gold pieces",
            default=250,
            ge=1,
            le=50_000,
        )
        categories: Annotated[
            list[str],
            WizardLore(hint="space-separated tags", parser=tag_parser),
        ] = Field(
            description="Transaction categories",
            default_factory=list,
        )

    run_wizard(LedgerEntry, title="Balance the Ledger")
