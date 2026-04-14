"""
Field annotation metadata for controlling wizard behavior.

`WizardLore` is attached to a field via `typing.Annotated` to pass
instructions to the wizard -- such as which section to group the field under,
a custom hint string, or a custom parser callable.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic.fields import FieldInfo


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
    """

    section: str | None = None
    hint: str | None = None
    parser: Callable[[str], Any] | None = None


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
