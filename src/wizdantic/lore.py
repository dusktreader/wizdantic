"""
Field annotation metadata for controlling wizard behavior.

`WizardLore` is attached to a field via `typing.Annotated` to pass
instructions to the wizard -- such as which section to group the field under,
a custom hint string, a custom parser callable, or a custom picker callable.

`PickerContext` is the standardised argument passed to every picker callable,
whether that is the built-in `Prompt.ask` wrapper or a fully custom widget.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic.fields import FieldInfo


@dataclass(frozen=True, slots=True)
class PickerContext:
    """
    Standardised context passed to every picker callable.

    A picker is any callable with the signature `(PickerContext) -> str`.
    It is responsible for collecting a raw string value from the user by
    whatever means it chooses — a `rich.prompt.Prompt`, a Textual TUI, an
    OS file-chooser dialog, a network call, etc.  Wizdantic does not care
    about the implementation; it only calls the picker and feeds the
    returned string through the normal parser → TypeAdapter validation chain.

    Parameters:
        name:        The field name as declared on the model (e.g. `"background"`).
        description: The human-readable description from `Field(description=...)`,
                     or `None` if not provided.
        default:     The current value for this field — either the value from an
                     existing model instance passed to `Wizard(instance=...)`, the
                     field's declared default, or `None` when no default exists.
                     Pickers should use this as the pre-filled / starting value.
        hint:        The optional hint string from `WizardLore(hint=...)`.  Pickers
                     that render text prompts should display this dim after the label.
    """

    name: str
    description: str | None
    default: Any
    hint: str | None


@dataclass(frozen=True, slots=True)
class WizardLore:
    """
    Annotation metadata for controlling wizard behavior on a field.

    Attach to a field via `typing.Annotated` alongside pydantic's `Field`:

        name: Annotated[str, Field(description="Hunter name"), WizardLore(section="Identity")]

    Parameters:
        section: Group this field under a named heading in the wizard.
        hint:    Display text shown dim after the label. When provided, it
                 replaces any auto-generated format hint (e.g. `(comma-separated)`).
        parser:  Custom callable `(str) -> T` used instead of `TypeAdapter`
                 for this field. Any exception raised by the parser is caught,
                 displayed, and the prompt retried.
        picker:  Custom callable `(PickerContext) -> str` used instead of the
                 default `Prompt.ask`-based picker for this field.  The picker
                 is responsible for collecting a raw string value; wizdantic
                 feeds that string through `parser` (if set) and then through
                 `TypeAdapter` validation as normal.  Any exception raised by
                 the picker is treated as an abort.
        echo:    When `True`, wizdantic prints the field label and validated
                 value to the console after the picker returns — useful for
                 pickers like Textual TUI apps that take over the screen and
                 leave no visible record of the selection.  Has no effect on
                 fields using the built-in `prompt_picker`.  Defaults to `None`,
                 which means the wizard-level `echo_picker` setting applies.
                 Explicitly setting `False` suppresses the echo even when the
                 wizard default is `True`.
    """

    section: str | None = None
    hint: str | None = None
    parser: Callable[[str], Any] | None = None
    picker: Callable[[PickerContext], str] | None = None
    echo: bool | None = None


def extract_section(field_info: FieldInfo) -> str | None:
    """
    Find the wizard section for a field by scanning its `Annotated` metadata
    for a `WizardLore` instance.
    """
    for item in field_info.metadata:
        if isinstance(item, WizardLore) and item.section is not None:
            return item.section
    return None


def extract_hint(field_info: FieldInfo) -> str | None:
    """
    Find the user-supplied hint for a field by scanning its `Annotated`
    metadata for a `WizardLore` instance.
    """
    for item in field_info.metadata:
        if isinstance(item, WizardLore) and item.hint is not None:
            return item.hint
    return None


def extract_parser(field_info: FieldInfo) -> Callable[[str], Any] | None:
    """
    Find the custom parser for a field by scanning its `Annotated` metadata
    for a `WizardLore` instance.
    """
    for item in field_info.metadata:
        if isinstance(item, WizardLore) and item.parser is not None:
            return item.parser
    return None


def extract_picker(field_info: FieldInfo) -> Callable[[PickerContext], str] | None:
    """
    Find the custom picker for a field by scanning its `Annotated` metadata
    for a `WizardLore` instance.
    """
    for item in field_info.metadata:
        if isinstance(item, WizardLore) and item.picker is not None:
            return item.picker
    return None


def extract_echo(field_info: FieldInfo) -> bool | None:
    """
    Find the per-field echo override by scanning its `Annotated` metadata
    for a `WizardLore` instance.

    Returns `True` or `False` when the field explicitly sets `echo`; returns
    `None` when no `WizardLore` on the field touches `echo`, meaning the
    wizard-level `echo_picker` default applies.
    """
    for item in field_info.metadata:
        if isinstance(item, WizardLore) and item.echo is not None:
            return item.echo
    return None
