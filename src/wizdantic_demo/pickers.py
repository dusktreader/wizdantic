"""Demos for custom pickers: default_picker and a Textual TUI picker."""

from typing import Annotated

from pydantic import BaseModel, Field

from wizdantic import PickerContext, WizardLore, run_wizard


# ---------------------------------------------------------------------------
# Spell 1 — default_picker
# ---------------------------------------------------------------------------


def demo_1__pickers__default_picker():
    """
    Replace the built-in `Prompt.ask` input for every field by passing
    `default_picker` to `run_wizard` or `Wizard`.

    A picker is any callable with the signature `(PickerContext) -> str`.
    wizdantic calls it instead of its own prompt logic, then feeds the
    returned string through the normal parser → TypeAdapter validation chain.

    Here a `plain_input_picker` uses Python's built-in `input()` instead
    of Rich's `Prompt.ask` — no markup, no retry helpers, just a bare
    readline prompt. This illustrates that the picker protocol is
    completely implementation-agnostic: any blocking call that returns a
    string works.
    """

    def plain_input_picker(ctx: PickerContext) -> str:
        from pydantic_core import PydanticUndefined
        label = ctx.description or ctx.name
        if ctx.hint:
            label = f"{label} ({ctx.hint})"
        has_default = ctx.default is not None and ctx.default is not PydanticUndefined
        if has_default:
            label = f"{label} [{ctx.default}]"
        raw = input(f"  {label}: ")
        return raw if raw.strip() else (str(ctx.default) if has_default else "")

    class HeraldryRecord(BaseModel):
        house_name: str = Field(description="Name of the noble house")
        motto: str = Field(description="House motto", default="Strength and Honour")
        sigil: str = Field(description="Sigil description", default="A silver wolf on black")

    run_wizard(
        HeraldryRecord,
        title="Register a House",
        default_picker=plain_input_picker,
    )


# ---------------------------------------------------------------------------
# Spell 2 — per-field Textual TUI picker
# ---------------------------------------------------------------------------


def demo_2__pickers__textual_picker():
    """
    Use a Textual TUI app as the picker for a specific field via
    `WizardLore(picker=..., echo=True)`.

    Field-level pickers take priority over `default_picker`. The rest of
    the fields in the model use the standard `Prompt.ask` path unchanged.

    Here `TraditionPicker` is a small Textual app that presents the magical
    traditions as a scrollable option list. Arrow keys navigate; Enter
    selects. Escape cancels and keeps the default value. Only the
    `tradition` field is annotated with this picker — all other fields
    prompt normally.

    Because the Textual app takes over the full screen and leaves no visible
    record of the selection, `echo=True` is set on the `WizardLore` so
    wizdantic prints the label and chosen value back to the console after
    the TUI exits.
    """
    from auto_name_enum import AutoNameEnum, TitleCaseMixin, autodoc
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Vertical
    from textual.css.query import NoMatches
    from textual.widgets import Footer, Header, Label, OptionList, Static
    from textual.widgets.option_list import Option

    class Tradition(AutoNameEnum, TitleCaseMixin):
        ABJURATION    = autodoc("Protective wards, barriers, and banishments")
        CONJURATION   = autodoc("Summoning creatures and objects from other planes")
        DIVINATION    = autodoc("Gleaning knowledge and revealing secrets")
        ENCHANTMENT   = autodoc("Bending minds and compelling behaviour")
        EVOCATION     = autodoc("Raw energy shaped into destructive or healing force")
        ILLUSION      = autodoc("Crafting false perceptions and phantasmal images")
        NECROMANCY    = autodoc("Channelling life, death, and the forces between")
        TRANSMUTATION = autodoc("Altering matter, energy, and living forms")

    class TraditionPicker(App[str]):
        CSS = """
        Screen { align: center middle; }
        #frame {
            width: 60;
            border: round $primary;
            padding: 1 2;
        }
        #description { color: $text-muted; margin-bottom: 1; }
        #hint        { color: $text-muted; margin-top: 1; }
        """
        BINDINGS = [
            Binding("escape", "cancel", "Cancel", show=True),
        ]

        def __init__(self, default: str) -> None:
            super().__init__()
            self._default = default

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            with Vertical(id="frame"):
                yield Label("Choose a magical tradition", id="description")
                options = [
                    Option(f"[bold]{t.value}[/bold]  [dim]{t.description}[/dim]", id=t.value)
                    for t in Tradition
                ]
                yield OptionList(*options, id="tradition-list")
                yield Static("[dim]Enter to confirm · Esc to cancel[/dim]", id="hint")
            yield Footer()

        def on_mount(self) -> None:
            try:
                names = [t.value for t in Tradition]
                idx = names.index(self._default) if self._default in names else 0
                self.query_one("#tradition-list", OptionList).highlighted = idx
            except NoMatches:
                pass

        def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
            self.exit(str(event.option.id))

        def action_cancel(self) -> None:
            self.exit(self._default)

    def tradition_picker(ctx: PickerContext) -> str:
        default = str(ctx.default) if ctx.default else Tradition.EVOCATION.value
        result = TraditionPicker(default=default).run()
        return result if isinstance(result, str) else default

    class WizardRegistration(BaseModel):
        wizard_name: str = Field(description="Registered wizard name")
        tradition: Annotated[
            str,
            Field(description="Magical tradition"),
            WizardLore(picker=tradition_picker, echo=True),
        ] = Field(default=Tradition.EVOCATION.value)
        registry_id: int = Field(description="Conclave registry number", default=1001)

    run_wizard(WizardRegistration, title="Register a Wizard")
