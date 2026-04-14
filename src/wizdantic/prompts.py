"""
Prompt strategies for each supported field type.

Each `WizardPrompt` subclass knows how to prompt for, parse, and validate
a single field value. The `Wizard` constructs the appropriate subclass and
calls `prompt()` to collect the value.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any

import pydantic
from pydantic import SecretStr
from pydantic_core import PydanticUndefined
from rich.console import Console
from rich.prompt import Confirm, Prompt

from wizdantic.constants import INDENT
from wizdantic.type_utils import (
    parse_csv_fixed_tuple,
    parse_csv_sequence,
    parse_csv_set,
    parse_json_dict,
    parse_json_fixed_tuple,
    parse_json_sequence,
    parse_json_set,
    parse_kv_string,
)


def apply_hint(label: str, hint: str | None, *, is_opt: bool = False) -> str:
    """
    Append a dim hint string to a label.

    When both `hint` is `None` and `is_opt` is `False`, the label is
    returned unchanged. When `is_opt` is `True`, an "empty for None"
    fragment is appended so the user knows they can skip the field.
    If a `hint` is also provided, the two are joined with a comma.

    Examples:

        >>> apply_hint("Spell Name", None)
        'Spell Name'

        >>> apply_hint("Spell Name", "e.g. Arcane Bolt")
        'Spell Name [dim](e.g. Arcane Bolt)[/dim]'

        >>> apply_hint("Spell Name", None, is_opt=True)
        'Spell Name [dim](empty for None)[/dim]'

        >>> apply_hint("Spell Name", "e.g. Arcane Bolt", is_opt=True)
        'Spell Name [dim](e.g. Arcane Bolt, empty for None)[/dim]'

    Parameters:
        label:  The base label string (may already contain Rich markup).
        hint:   The hint text to append, or `None` to skip.
        is_opt: Whether the field accepts `None`.
    """
    parts = [p for p in [hint, "empty for None" if is_opt else None] if p]
    if not parts:
        return label
    return f"{label} [dim]({', '.join(parts)})[/dim]"


def type_name(annotation: Any) -> str:
    """
    Return a short, readable name for a type annotation.
    """
    return getattr(annotation, "__name__", str(annotation))


def validated_parser(
    parser: Callable[[str], Any],
    annotation: Any,
) -> Callable[[str], Any]:
    """
    Wrap a custom parser so its return value is validated through `TypeAdapter`.

    The parser handles string-to-object conversion. `TypeAdapter` then applies
    the full Pydantic validation pipeline for the field's annotation (constraints,
    custom validators, and type coercion), giving custom types the same inline
    validation guarantees as built-in types.

    Parameters:
        parser:     The raw parser callable from `WizardLore`.
        annotation: The full field annotation to validate against.
    """
    adapter = pydantic.TypeAdapter(annotation)

    def _validated(raw: str) -> Any:
        parsed = parser(raw)
        try:
            return adapter.validate_python(parsed)
        except pydantic.ValidationError as exc:
            msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
            raise ValueError(msg) from exc

    return _validated


class WizardPrompt(ABC):
    """
    Base class for all prompt strategies.

    Each subclass prompts for a single field value, handling parsing,
    validation, and retry logic internally.

    Parameters:
        console:  Rich console for all input and output.
        label:    The display label for the prompt.
        default:  The field's default value, or `PydanticUndefined`.
        required: Whether the field requires a non-empty value.
        is_opt:   Whether the field accepts `None`.
        hint:     Optional hint text appended to the label.
    """

    def __init__(
        self,
        console: Console,
        label: str,
        default: Any,
        required: bool,
        is_opt: bool,
        *,
        hint: str | None = None,
    ):
        self.console = console
        self.label = label
        self.default = default
        self.required = required
        self.is_opt = is_opt
        self.hint = hint

    @abstractmethod
    def prompt(self) -> Any:
        """
        Prompt the user and return the validated value.
        """

    def _print(self, message: str, indent: int = 1) -> None:
        self.console.print(f"{INDENT * indent}{message}")

    def _ask(self, prompt: str, indent: int = 1, **kwargs: Any) -> str:
        return Prompt.ask(f"{INDENT * indent}{prompt}", **kwargs)

    def _confirm(self, prompt: str, indent: int = 0, **kwargs: Any) -> bool:
        return Confirm.ask(f"{INDENT * indent}{prompt}", **kwargs)


class BoolPrompt(WizardPrompt):
    """
    Prompt for a boolean using Rich `Confirm`.

    When the field is optional, an empty response returns `None` instead of
    retrying. Non-optional fields use `Confirm.ask` directly, which enforces
    a y/n response.
    """

    def prompt(self) -> bool | None:
        if self.is_opt:
            default_hint = "y/n, leave blank for None"
            applied_hint = self.hint if self.hint is not None else default_hint
            prompt_label = apply_hint(self.label, applied_hint)
            kwargs: dict[str, Any] = {"console": self.console, "default": ""}
            if self.default is not PydanticUndefined and self.default is not None:
                kwargs["default"] = "y" if self.default else "n"
            while True:
                raw = self._ask(prompt_label, **kwargs).strip().lower()
                if raw == "":
                    return None
                if raw in ("y", "yes", "true", "1"):
                    return True
                if raw in ("n", "no", "false", "0"):
                    return False
                self._print("[red]Enter y or n (or leave blank for none).[/red]")
        else:
            applied_label = apply_hint(self.label, self.hint)
            confirm_kwargs: dict[str, Any] = {"console": self.console}
            if self.default is not PydanticUndefined and self.default is not None:
                confirm_kwargs["default"] = self.default
            return self._confirm(applied_label, **confirm_kwargs)


class EnumPrompt(WizardPrompt):
    """
    Show a numbered list of enum members and accept selection by index or name.
    """

    def __init__(self, *args: Any, enum_cls: type[Enum], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.enum_cls = enum_cls

    def prompt(self) -> Enum | None:
        members = list(self.enum_cls)

        self._print(self.label)
        for i, member in enumerate(members, 1):
            tag = (
                " [green](default)[/green]" if self.default is not PydanticUndefined and member == self.default else ""
            )
            self._print(f"[cyan]{i}[/cyan]. {member.value}{tag}", indent=2)

        default_str: str | None = None
        if self.default is not PydanticUndefined and self.default is not None:
            default_str = str(members.index(self.default) + 1)
        elif self.is_opt:
            default_str = ""

        while True:
            prompt_kwargs: dict[str, Any] = {"console": self.console}
            if default_str is not None:
                prompt_kwargs["default"] = default_str
            raw = self._ask("Enter choice", **prompt_kwargs)

            if not raw and self.is_opt:
                return None
            if not raw and self.required:
                self._print("[red]A selection is required.[/red]")
                continue

            try:
                idx = int(raw)
                if 1 <= idx <= len(members):
                    return members[idx - 1]
                self._print(f"[red]Choose between 1 and {len(members)}.[/red]")
                continue
            except (ValueError, TypeError):
                pass

            for member in members:
                if str(raw).lower() in (member.name.lower(), str(member.value).lower()):
                    return member

            self._print("[red]Invalid choice.[/red]")


class LiteralPrompt(WizardPrompt):
    """
    Show a numbered list of literal values and accept selection by index or exact match.
    """

    def __init__(self, *args: Any, values: tuple[Any, ...], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.values = values

    def prompt(self) -> Any:
        self._print(self.label)
        for i, value in enumerate(self.values, 1):
            tag = " [green](default)[/green]" if self.default is not PydanticUndefined and value == self.default else ""
            self._print(f"[cyan]{i}[/cyan]. {value}{tag}", indent=2)

        default_str: str | None = None
        if self.default is not PydanticUndefined and self.default is not None:
            default_str = str(list(self.values).index(self.default) + 1)
        elif self.is_opt:
            default_str = ""

        while True:
            prompt_kwargs: dict[str, Any] = {"console": self.console}
            if default_str is not None:
                prompt_kwargs["default"] = default_str
            raw = self._ask("Enter choice", **prompt_kwargs)

            if not raw and self.is_opt:
                return None
            if not raw and self.required:
                self._print("[red]A selection is required.[/red]")
                continue

            try:
                idx = int(raw)
                if 1 <= idx <= len(self.values):
                    return self.values[idx - 1]
                self._print(f"[red]Choose between 1 and {len(self.values)}.[/red]")
                continue
            except (ValueError, TypeError):
                pass

            for value in self.values:
                if raw == str(value):
                    return value

            self._print("[red]Invalid choice.[/red]")


class SecretPrompt(WizardPrompt):
    """
    Prompt for a secret value with masked input.
    """

    def __init__(
        self,
        *args: Any,
        annotation: Any,
        parser: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.annotation = annotation
        self.parser = parser

    def prompt(self) -> Any:
        prompt_label = apply_hint(self.label, self.hint, is_opt=self.is_opt)
        kwargs: dict[str, Any] = {"console": self.console, "password": True}
        if self.default is not PydanticUndefined and self.default is not None:
            raw_default = self.default.get_secret_value() if isinstance(self.default, SecretStr) else str(self.default)
            kwargs["default"] = "*" * len(raw_default)
        elif self.is_opt:
            kwargs["default"] = ""

        while True:
            raw = Prompt.ask(prompt_label, **kwargs)

            if not raw and self.is_opt:
                return None

            if not raw and self.required:
                self._print("[red]A value is required.[/red]")
                continue

            if self.default is not PydanticUndefined:
                _raw_default = (
                    self.default.get_secret_value() if isinstance(self.default, SecretStr) else str(self.default)
                )
                if raw == "*" * len(_raw_default):
                    return self.default

            if self.parser is not None:
                try:
                    return self.parser(raw)
                except Exception as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
                    continue

            try:
                return pydantic.TypeAdapter(self.annotation).validate_python(raw)
            except pydantic.ValidationError as exc:
                msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
                self._print(f"[red]Invalid: {msg}[/red]")


class ValuePrompt(WizardPrompt):
    """
    Generic prompt with TypeAdapter validation for scalar types.

    Handles str, int, float, and any other type that TypeAdapter can
    coerce from a string.
    """

    def __init__(
        self,
        *args: Any,
        annotation: Any,
        parser: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.annotation = annotation
        self.parser = parser

    def prompt(self) -> Any:
        prompt_label = apply_hint(self.label, self.hint, is_opt=self.is_opt)
        kwargs: dict[str, Any] = {"console": self.console}
        if self.default is not PydanticUndefined and self.default is not None:
            kwargs["default"] = str(self.default)
        elif self.is_opt:
            kwargs["default"] = ""

        while True:
            raw = Prompt.ask(prompt_label, **kwargs)

            if raw == "" and self.is_opt:
                return None

            if raw == "" and self.required:
                self._print("[red]A value is required.[/red]")
                continue

            if self.parser is not None:
                try:
                    return self.parser(raw)
                except Exception as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
                    continue

            try:
                return pydantic.TypeAdapter(self.annotation).validate_python(raw)
            except pydantic.ValidationError as exc:
                msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
                self._print(f"[red]Invalid: {msg}[/red]")


class ListPrompt(WizardPrompt):
    """
    Prompt for a list via JSON array or comma-separated input.

    Tries JSON parsing first. If that fails, falls back to splitting on
    commas and validating each element via `TypeAdapter`.
    """

    def __init__(
        self,
        *args: Any,
        item_type: Any,
        parser: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.item_type = item_type
        self.parser = parser

    def prompt(self) -> list[Any] | None:
        tn = type_name(self.item_type)
        default_hint = f"{tn}, {tn}, ... (JSON array or comma-separated)"
        applied_hint = self.hint if self.hint is not None else default_hint
        prompt_label = apply_hint(self.label, applied_hint, is_opt=self.is_opt)
        kwargs: dict[str, Any] = {"console": self.console}
        if self.default is not PydanticUndefined and self.default is not None and isinstance(self.default, list):
            kwargs["default"] = ", ".join(str(v) for v in self.default) if self.default else ""
        elif self.is_opt:
            kwargs["default"] = ""

        while True:
            raw = Prompt.ask(prompt_label, **kwargs)
            raw = raw.strip()

            has_content = bool([s for s in raw.split(",") if s.strip()])

            if not has_content and self.is_opt:
                return None
            if not has_content and not self.required:
                return []
            if not has_content and self.required:
                self._print("[red]At least one value is required.[/red]")
                continue

            if self.parser is not None:
                try:
                    return self.parser(raw)
                except Exception as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
                    continue

            try:
                return parse_json_sequence(raw, self.item_type)
            except ValueError:
                pass

            try:
                return parse_csv_sequence(raw, self.item_type)
            except ValueError as exc:
                self._print(f"[red]Invalid: {exc}[/red]")


class TuplePrompt(WizardPrompt):
    """
    Prompt for a tuple via JSON array or comma-separated input.

    Both homogeneous and fixed-length tuples accept JSON array or
    comma-separated input. For fixed-length tuples, the element count must
    match exactly.
    """

    def __init__(
        self,
        *args: Any,
        item_types: list[Any],
        is_homogeneous: bool,
        parser: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.item_types = item_types
        self.is_homogeneous = is_homogeneous
        self.parser = parser

    def prompt(self) -> tuple[Any, ...] | None:
        if self.hint is not None:
            prompt_label = apply_hint(self.label, self.hint, is_opt=self.is_opt)
        elif self.is_homogeneous:
            tn = type_name(self.item_types[0])
            default_hint = f"{tn}, {tn}, ... (JSON array or comma-separated)"
            prompt_label = apply_hint(self.label, default_hint, is_opt=self.is_opt)
        else:
            type_names = ", ".join(type_name(t) for t in self.item_types)
            default_hint = f"{type_names} (JSON array or comma-separated)"
            prompt_label = apply_hint(self.label, default_hint, is_opt=self.is_opt)

        kwargs: dict[str, Any] = {"console": self.console}
        if self.default is not PydanticUndefined and self.default is not None:
            kwargs["default"] = str(list(self.default))
        elif self.is_opt:
            kwargs["default"] = ""

        while True:
            raw = Prompt.ask(prompt_label, **kwargs)
            raw = raw.strip()

            if not raw and self.is_opt:
                return None
            if not raw and self.required:
                self._print("[red]A value is required.[/red]")
                continue

            if self.parser is not None:
                try:
                    return self.parser(raw)
                except Exception as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
                    continue

            if self.is_homogeneous:
                item_type = self.item_types[0]
                try:
                    return tuple(parse_json_sequence(raw, item_type))
                except ValueError:
                    pass
                try:
                    return tuple(parse_csv_sequence(raw, item_type))
                except ValueError as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
            else:
                try:
                    return tuple(parse_json_fixed_tuple(raw, self.item_types))
                except ValueError:
                    pass
                try:
                    return tuple(parse_csv_fixed_tuple(raw, self.item_types))
                except ValueError as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")


class SetPrompt(WizardPrompt):
    """
    Prompt for a set via JSON array or comma-separated input.

    Tries JSON parsing first. If that fails, falls back to splitting on
    commas and validating each element via `TypeAdapter`. Rejects duplicate
    values.
    """

    def __init__(
        self,
        *args: Any,
        item_type: Any,
        parser: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.item_type = item_type
        self.parser = parser

    def prompt(self) -> set[Any] | None:
        tn = type_name(self.item_type)
        default_hint = f"{tn}, {tn}, ... (JSON array or comma-separated)"
        applied_hint = self.hint if self.hint is not None else default_hint
        prompt_label = apply_hint(self.label, applied_hint, is_opt=self.is_opt)

        kwargs: dict[str, Any] = {"console": self.console}
        if self.default is not PydanticUndefined and self.default is not None and isinstance(self.default, set):
            kwargs["default"] = ", ".join(sorted(str(v) for v in self.default)) if self.default else ""
        elif self.is_opt:
            kwargs["default"] = ""

        while True:
            raw = Prompt.ask(prompt_label, **kwargs)
            raw = raw.strip()

            has_content = bool([s for s in raw.split(",") if s.strip()])

            if not has_content and self.is_opt:
                return None
            if not has_content and not self.required:
                return set()
            if not has_content and self.required:
                self._print("[red]At least one value is required.[/red]")
                continue

            if self.parser is not None:
                try:
                    return self.parser(raw)
                except Exception as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
                    continue

            if raw.startswith("["):
                try:
                    return parse_json_set(raw, self.item_type)
                except ValueError as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
                    continue

            try:
                return parse_csv_set(raw, self.item_type)
            except ValueError as exc:
                self._print(f"[red]Invalid: {exc}[/red]")


class DictPrompt(WizardPrompt):
    """
    Prompt for a dict via JSON object or `key:value, key:value` notation.

    Tries JSON parsing first. If that fails, falls back to splitting on
    commas then colons, requiring exactly two parts per pair.
    """

    def __init__(
        self,
        *args: Any,
        key_type: Any,
        value_type: Any,
        parser: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.key_type = key_type
        self.value_type = value_type
        self.parser = parser

    def prompt(self) -> dict[Any, Any] | None:
        default_hint = "JSON object or key:value, key:value"
        applied_hint = self.hint if self.hint is not None else default_hint
        prompt_label = apply_hint(self.label, applied_hint, is_opt=self.is_opt)

        kwargs: dict[str, Any] = {"console": self.console}
        if self.default is not PydanticUndefined and self.default is not None and isinstance(self.default, dict):
            if self.default:
                kwargs["default"] = ", ".join(f"{k}:{v}" for k, v in self.default.items())
            else:
                kwargs["default"] = ""
        elif self.is_opt:
            kwargs["default"] = ""

        while True:
            raw = Prompt.ask(prompt_label, **kwargs)
            raw = raw.strip()

            if not raw and self.is_opt:
                return None
            if not raw and not self.required:
                return {}
            if not raw and self.required:
                self._print("[red]At least one entry is required.[/red]")
                continue

            if self.parser is not None:
                try:
                    return self.parser(raw)
                except Exception as exc:
                    self._print(f"[red]Invalid: {exc}[/red]")
                    continue

            try:
                return parse_json_dict(raw, self.key_type, self.value_type)
            except ValueError:
                pass

            try:
                return parse_kv_string(raw, self.key_type, self.value_type)
            except ValueError as exc:
                self._print(f"[red]Invalid: {exc}[/red]")
