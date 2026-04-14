"""
Interactive wizard for populating Pydantic models with validated user input.

Uses Rich prompts to walk the user through each field, validating as they go
and insisting on values for required fields.
"""

from enum import Enum
from typing import Annotated, Any, Generic, TypeVar

import buzz
import inflection
import snick
from pydantic import BaseModel, SecretStr
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from rich.console import Console
from rich.prompt import Confirm
from rich.rule import Rule
from rich.table import Table

from wizdantic.console import WizardConsole
from wizdantic.exceptions import UnsupportedFieldType, WizardAborted
from wizdantic.lore import extract_hint, extract_parser, extract_section
from wizdantic.prompts import (
    BoolPrompt,
    DictPrompt,
    EnumPrompt,
    ListPrompt,
    LiteralPrompt,
    SecretPrompt,
    SetPrompt,
    TuplePrompt,
    ValuePrompt,
    validated_parser,
)
from wizdantic.type_utils import (
    is_unsupported_union,
    unwrap_dict,
    unwrap_list,
    unwrap_literal,
    unwrap_optional,
    unwrap_set,
    unwrap_tuple,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def run_wizard(
    model_class: type[_ModelT],
    *,
    console: Console | None = None,
    title: str | None = None,
    show_summary: bool = True,
) -> _ModelT:
    """
    Run an interactive wizard and return a populated model instance.

    This is a convenience wrapper around `Wizard(...).run()`.

    Parameters:
        model_class:  The Pydantic model class to populate.
        console:      Rich console for output. A new one is created if omitted.
        title:        Heading displayed at the top of the wizard.
        show_summary: Show a summary table after collection. Defaults to True.
    """
    return Wizard(
        model_class,
        console=console,
        title=title,
        show_summary=show_summary,
    ).run()


class Wizard(Generic[_ModelT]):
    """
    Walks the user through each field of a Pydantic model, collecting and
    validating values interactively via Rich prompts.

    Parameters:
        model_class:  The Pydantic model class to populate.
        console:      Rich console for output. A new one is created if omitted.
        title:        Heading displayed at the top of the wizard.
        show_summary: Show a summary table after collection. Defaults to True.
    """

    def __init__(
        self,
        model_class: type[_ModelT],
        *,
        console: Console | None = None,
        title: str | None = None,
        show_summary: bool = True,
    ):
        self.model_class = model_class
        self.console = console or WizardConsole()
        self.title = title
        self.show_summary = show_summary
        self._validate_fields()

    def _validate_fields(self) -> None:
        """
        Walk every field and reject types that wizdantic cannot prompt for.

        Raises `UnsupportedFieldType` at construction time so the developer
        discovers the problem immediately, not mid-wizard-session.
        """
        for name, field_info in self.model_class.model_fields.items():
            annotation = field_info.annotation
            inner = unwrap_optional(annotation)
            effective = inner if inner is not None else annotation
            UnsupportedFieldType.require_condition(
                not is_unsupported_union(effective),
                snick.dedent(
                    f"""
                    Field '{name}' has unsupported type {annotation}.
                    wizdantic cannot prompt for multi-type unions.
                    Consider using a single concrete type or a custom parser via WizardLore.
                    """
                ),
            )
            set_item_type = unwrap_set(effective)
            if set_item_type is not None and isinstance(set_item_type, type) and issubclass(set_item_type, BaseModel):
                is_frozen = set_item_type.model_config.get("frozen", False)
                UnsupportedFieldType.require_condition(
                    is_frozen,
                    snick.dedent(
                        f"""
                        Field '{name}' is set[{set_item_type.__name__}], but {set_item_type.__name__} is not frozen.
                        BaseModel instances must be hashable to be stored in a set.
                        Add model_config = ConfigDict(frozen=True) to {set_item_type.__name__}.
                        """
                    ),
                )

    def _make_label(self, name: str, description: str | None) -> str:
        if description:
            return f"{description} [dim]([yellow]{name}[/yellow])[/dim]"
        return inflection.titleize(name)

    def _format_display(self, value: Any) -> "str | Table":
        if value is None:
            return "[dim](None)[/dim]"
        if isinstance(value, SecretStr):
            return "[dim]" + "*" * len(value.get_secret_value()) + "[/dim]"
        if isinstance(value, BaseModel):
            return self._make_summary_table(value, title=None)
        if isinstance(value, Enum):
            return str(value.value)
        if isinstance(value, dict):
            if not value:
                return "[dim](empty)[/dim]"
            return ", ".join(f"{k}:{v}" for k, v in value.items())
        if isinstance(value, (list, tuple, set)):
            items = list(value)
            return ", ".join(str(v) for v in items) or "[dim](empty)[/dim]"
        return str(value)

    def _make_summary_table(self, model: BaseModel, title: str | None = "Summary") -> Table:
        """
        Build a Rich `Table` summarizing all field values in `model`.

        When `title` is `None` the table is rendered without a title, which is
        appropriate for nested tables embedded inside a parent summary cell.

        Parameters:
            model: The populated model instance to summarize.
            title: Optional title rendered above the table. Pass `None` for
                   nested tables.
        """
        table = Table(
            title=title,
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 1),
        )
        table.add_column("Field", style="yellow")
        table.add_column("Value")

        for name, field_info in type(model).model_fields.items():
            val = getattr(model, name)
            display_label = field_info.description or inflection.titleize(name)
            table.add_row(display_label, self._format_display(val))

        return table

    def print_title(self, title: str, titleize: bool = False, style: str = "cyan") -> None:
        self.console.print()
        self.console.print(Rule(f"[bold]{inflection.titleize(title) if titleize else title}[/bold]", style=style))
        self.console.print()

    def print_section(self, name: str, style: str = "dim cyan") -> None:
        self.console.print(Rule(f"[bold]{name}[/bold]", style=style))

    def print_summary(self, model: BaseModel) -> None:
        """
        Print a Rich table summarizing all collected field values.
        """
        self.console.print()
        table = self._make_summary_table(model, title="Summary")
        table.header_style = "bold cyan"
        self.console.print(table)
        self.console.print()

    def print_aborted(self, dep: buzz.DoExceptParams) -> None:
        """
        Print a clean abort message when the user interrupts the wizard.
        """
        self.console.print()
        self.console.print(Rule(f"[bold red]Wizard aborted: {dep.final_message}[/bold red]", style="red"))
        self.console.print()

    def run(self) -> _ModelT:
        """
        Execute the wizard and return a validated model instance.

        Raises `WizardAborted` if the user presses Ctrl+C at any point.
        """
        with WizardAborted.handle_errors(
            "Wizard aborted by user",
            handle_exc_class=(Exception, KeyboardInterrupt),
            do_except=self.print_aborted,
        ):
            self.print_title(self.title or self.model_class.__name__, titleize=self.title is None)
            model = self._run()
        if self.show_summary:
            self.print_summary(model)
        return model

    def _sub_wizard(self, model_cls: type[BaseModel]) -> BaseModel:
        """
        Run a sub-wizard for a nested model, sharing the parent's console.
        """
        return Wizard(model_cls, console=self.console, show_summary=False)._run()

    def _run(self) -> _ModelT:
        values: dict[str, Any] = {}
        for section_name, fields in self._group_fields():
            if section_name is not None:
                self.print_section(section_name)
            for name, field_info in fields:
                values[name] = self._prompt_field(name, field_info)

        return self.model_class.model_validate(values)

    def _group_fields(self) -> list[tuple[str | None, list[tuple[str, FieldInfo]]]]:
        """
        Partition model fields by their `WizardLore` section metadata.

        Sections are emitted in the order they first appear. Unsectioned
        fields are collected at the end under an "Other" heading (or with
        no heading if there are no sections at all).
        """
        ordered_sections: list[str] = []
        sectioned: dict[str, list[tuple[str, FieldInfo]]] = {}
        unsectioned: list[tuple[str, FieldInfo]] = []

        for name, field_info in self.model_class.model_fields.items():
            section = extract_section(field_info)
            if section:
                if section not in sectioned:
                    ordered_sections.append(section)
                    sectioned[section] = []
                sectioned[section].append((name, field_info))
            else:
                unsectioned.append((name, field_info))

        result: list[tuple[str | None, list[tuple[str, FieldInfo]]]] = []
        for sec in ordered_sections:
            result.append((sec, sectioned[sec]))
        if unsectioned:
            label = "Other" if ordered_sections else None
            result.append((label, unsectioned))
        return result

    def _prompt_nested_model(
        self,
        name: str,
        description: str | None,
        model_cls: type[BaseModel],
    ) -> BaseModel:
        """
        Print a heading and run a sub-wizard for a single nested BaseModel field.
        """
        if description:
            self.print_title(description, titleize=True, style="magenta")
        else:
            self.print_title(name, style="magenta")
        return self._sub_wizard(model_cls)

    def _prompt_nested_collection(
        self,
        name: str,
        description: str | None,
        model_cls: type[BaseModel],
    ) -> list[BaseModel]:
        """
        Collect a variable-length sequence of nested models via repeated sub-wizards.

        Each iteration prints a numbered heading, runs a sub-wizard, and asks
        whether to continue. Returns the collected items as a plain list so the
        caller can convert to the target collection type.
        """
        items: list[BaseModel] = []
        label = description or name
        while True:
            index = len(items) + 1
            self.print_title(f"{label} #{index}", titleize=False, style="magenta")
            items.append(self._sub_wizard(model_cls))
            if not Confirm.ask(f"Add another {label}?", console=self.console):
                break
        return items

    def _prompt_nested_fixed_tuple(
        self,
        name: str,
        description: str | None,
        item_types: list[Any],
    ) -> tuple[Any, ...]:
        """
        Prompt each position of a fixed-length tuple that contains BaseModel positions.

        BaseModel positions run a sub-wizard. Scalar positions use `ValuePrompt`.
        """
        label = description or name
        self.print_title(label, titleize=bool(description), style="magenta")
        items: list[Any] = []
        for index, item_type in enumerate(item_types, start=1):
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                self.print_title(f"{item_type.__name__} (position {index})", titleize=False, style="magenta")
                items.append(self._sub_wizard(item_type))
            else:
                tn = getattr(item_type, "__name__", str(item_type))
                prompt = ValuePrompt(
                    self.console,
                    f"Position {index} [dim]({tn})[/dim]",
                    PydanticUndefined,
                    True,
                    False,
                    annotation=item_type,
                )
                items.append(prompt.prompt())
        return tuple(items)

    def _prompt_nested_dict(
        self,
        name: str,
        description: str | None,
        model_cls: type[BaseModel],
        key_type: Any,
    ) -> dict[Any, BaseModel]:
        """
        Collect a dict mapping prompted keys to nested model values.

        Each iteration prompts for a key (as a scalar), runs a sub-wizard for
        the value, and asks whether to continue.
        """
        result: dict[Any, BaseModel] = {}
        label = description or name
        key_type_name = getattr(key_type, "__name__", str(key_type))
        while True:
            index = len(result) + 1
            self.print_title(f"{label} #{index}", titleize=False, style="magenta")
            key_prompt = ValuePrompt(
                self.console,
                f"Key [dim]({key_type_name})[/dim]",
                PydanticUndefined,
                True,
                False,
                annotation=key_type,
            )
            key = key_prompt.prompt()
            result[key] = self._sub_wizard(model_cls)
            if not Confirm.ask(f"Add another {label}?", console=self.console):
                break
        return result

    def _prompt_field(self, name: str, field_info: FieldInfo) -> Any:
        """
        Dispatch to the correct prompt strategy based on the field's type.

        For nested BaseModel fields, handles recursion directly. For leaf
        types, constructs the appropriate `WizardPrompt` subclass and calls
        `prompt()`.
        """
        annotation = field_info.annotation
        inner = unwrap_optional(annotation)
        is_opt = inner is not None
        effective_annotation = inner if is_opt else annotation

        default = field_info.get_default(call_default_factory=True)
        label = self._make_label(name, field_info.description)
        required = not is_opt and default is PydanticUndefined

        lore_hint = extract_hint(field_info)
        lore_parser = extract_parser(field_info)
        if lore_parser is not None:
            if field_info.metadata:
                validated_annotation = Annotated.__getitem__((annotation, *field_info.metadata))
            else:
                validated_annotation = annotation
            lore_parser = validated_parser(lore_parser, validated_annotation)

        # list[T]
        list_item_type = unwrap_list(effective_annotation)
        if list_item_type is not None:
            if isinstance(list_item_type, type) and issubclass(list_item_type, BaseModel):
                return self._prompt_nested_collection(name, field_info.description, list_item_type)
            return ListPrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                hint=lore_hint,
                item_type=list_item_type,
                parser=lore_parser,
            ).prompt()

        # tuple[T, ...] or tuple[T1, T2, ...]
        tuple_result = unwrap_tuple(effective_annotation)
        if tuple_result is not None:
            item_types, is_homogeneous = tuple_result
            if is_homogeneous and isinstance(item_types[0], type) and issubclass(item_types[0], BaseModel):
                return tuple(self._prompt_nested_collection(name, field_info.description, item_types[0]))
            if not is_homogeneous and any(isinstance(t, type) and issubclass(t, BaseModel) for t in item_types):
                return self._prompt_nested_fixed_tuple(name, field_info.description, item_types)
            return TuplePrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                hint=lore_hint,
                item_types=item_types,
                is_homogeneous=is_homogeneous,
                parser=lore_parser,
            ).prompt()

        # set[T]
        set_item_type = unwrap_set(effective_annotation)
        if set_item_type is not None:
            if isinstance(set_item_type, type) and issubclass(set_item_type, BaseModel):
                return set(self._prompt_nested_collection(name, field_info.description, set_item_type))
            return SetPrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                hint=lore_hint,
                item_type=set_item_type,
                parser=lore_parser,
            ).prompt()

        # dict[K, V]
        dict_types = unwrap_dict(effective_annotation)
        if dict_types is not None:
            key_type, value_type = dict_types
            if isinstance(value_type, type) and issubclass(value_type, BaseModel):
                return self._prompt_nested_dict(name, field_info.description, value_type, key_type)
            return DictPrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                hint=lore_hint,
                key_type=key_type,
                value_type=value_type,
                parser=lore_parser,
            ).prompt()

        # nested BaseModel
        if isinstance(effective_annotation, type) and issubclass(effective_annotation, BaseModel):
            return self._prompt_nested_model(name, field_info.description, effective_annotation)

        if effective_annotation is bool:
            return BoolPrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                hint=lore_hint,
            ).prompt()

        if isinstance(effective_annotation, type) and issubclass(effective_annotation, Enum):
            return EnumPrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                enum_cls=effective_annotation,
            ).prompt()

        lit_vals = unwrap_literal(effective_annotation)
        if lit_vals is not None:
            return LiteralPrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                values=lit_vals,
            ).prompt()

        if isinstance(effective_annotation, type) and issubclass(effective_annotation, SecretStr):
            return SecretPrompt(
                self.console,
                label,
                default,
                required,
                is_opt,
                hint=lore_hint,
                annotation=annotation,
                parser=lore_parser,
            ).prompt()

        return ValuePrompt(
            self.console,
            label,
            default,
            required,
            is_opt,
            hint=lore_hint,
            annotation=annotation,
            parser=lore_parser,
        ).prompt()
