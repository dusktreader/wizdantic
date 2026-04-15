"""
Entry point for the wizdantic interactive demo.

Run with `wizdantic-demo` or `uv run wizdantic-demo` to walk through
each feature of wizdantic interactively. Pass `--feature` to jump
straight to a single chapter.
"""

from typing import Annotated

import snick
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

try:
    import typer
    from auto_name_enum import AutoNameEnum, LowerCaseMixin, autodoc
except ImportError:
    print("The demo requires extra dependencies. Install them with: wizdantic[demo]")
    raise SystemExit(1)

from wizdantic_demo.helpers import get_demo_functions, run_demo


class Feature(AutoNameEnum, LowerCaseMixin):
    SCALAR_TYPES = autodoc(description="Strings, integers, floats, and booleans")
    CHOICES = autodoc(description="Enum and Literal field selection")
    OPTIONAL_AND_SECRET = autodoc(description="Optional fields and masked secrets")
    COLLECTIONS = autodoc(description="Lists, tuples, sets, and dicts")
    NESTED_MODELS = autodoc(description="Nested BaseModel and list[BaseModel]")
    WIZARD_LORE = autodoc(description="Sections, custom hints, and custom parsers")
    INSTANCE_SEEDING = autodoc(description="Pre-filling prompts from an existing model instance")


def start(
    feature: Annotated[
        Feature | None,
        typer.Option(help="The chapter to demo. If not provided, all chapters run in order."),
    ] = None,
) -> None:
    """
    Run the wizdantic interactive demo.

    Each chapter demonstrates a different feature of the wizard toolkit.
    Pass `--feature` to jump straight to a single chapter.
    """
    console = Console()

    features = [feature] if feature else list(Feature)

    all_demos: list[tuple[Feature, list]] = []
    for selected_feature in features:
        demos = get_demo_functions(selected_feature.value)
        if demos:
            all_demos.append((selected_feature, demos))

    chapters_table = Table(show_header=False, box=None, padding=(0, 2))
    chapters_table.add_column(style="cyan")
    chapters_table.add_column()
    for feat, _ in all_demos:
        chapters_table.add_row(feat.value, feat.description)

    console.print()
    console.print(
        Panel(
            Group(
                snick.dedent(
                    """
                    [bold]Welcome to the wizdantic spellbook.[/bold]

                    This demo walks you through the arcane arts of interactive
                    model population. Each spell demonstrates a different feature
                    of the wizard toolkit.

                    [dim]You can skip any spell or quit at any time.[/dim]

                    [bold yellow]Chapters:[/bold yellow]
                    """
                ),
                chapters_table,
            ),
            title="[bold magenta]The Wizdantic Spellbook[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )
    console.print()

    if not Confirm.ask("[bold]Open the spellbook?[/bold]", console=console, default=True):
        console.print("[dim]The spellbook remains sealed. Perhaps another time.[/dim]")
        return

    for feat, demos in all_demos:
        console.print()
        console.print(
            Panel(
                snick.dedent(
                    f"""
                    [bold]{feat.description}[/bold]

                    [dim]{len(demos)} spell{"s" if len(demos) != 1 else ""} in this chapter.[/dim]
                    """
                ),
                title=f"[bold cyan]Chapter: {feat.value}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

        for demo in demos:
            if not run_demo(demo, console):
                console.print("[dim]Closing the spellbook.[/dim]")
                return

    console.print()
    console.print(
        Panel(
            snick.dedent(
                """
                [bold]You have completed the wizdantic spellbook.[/bold]

                You are now ready to build your own wizards.
                May your incantations always validate.
                """
            ),
            title="[bold magenta]Spellbook Complete[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )


def main() -> None:
    """CLI entry point."""
    typer.run(start)
