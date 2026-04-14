import io
from enum import Enum
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field
from pytest_bdd import given, parsers, scenarios, then, when
from rich.console import Console

from wizdantic.wizard import run_wizard

scenarios("../wizard.feature")

pytestmark = pytest.mark.integration


class SimpleSpellcaster(BaseModel):
    name: str = Field(description="Spellcaster name")
    power_level: int = Field(description="Power level", default=9000)


class OptionalCallsign(BaseModel):
    callsign: str | None = Field(description="Call sign", default=None)


class Faction(str, Enum):
    ARCANE = "arcane"
    SHADOW = "shadow"


class FactionModel(BaseModel):
    faction: Faction = Field(description="Faction allegiance")


class AllyList(BaseModel):
    allies: list[str] = Field(description="Allies")


class Planet(BaseModel):
    name: str = Field(description="Planet name")
    system: str = Field(description="Star system", default="Outer Rim")


class NestedModel(BaseModel):
    homeworld: Planet = Field(description="Home planet")


def _make_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=True)


def _run_wizard(
    model_cls: type[BaseModel],
    inputs: list[str],
    *,
    show_summary: bool = False,
) -> tuple[Any, str]:
    """Run the wizard with mocked Prompt/Confirm inputs, return (model, output)."""
    console = _make_console()

    with (
        patch("wizdantic.prompts.Prompt.ask", side_effect=inputs),
        patch("wizdantic.prompts.Confirm.ask", return_value=True),
    ):
        result = run_wizard(model_cls, console=console, show_summary=show_summary)

    output = console.file.getvalue()  # ty: ignore[unresolved-attribute]
    return result, output


@given(parsers.parse('a model with fields "name" (str) and "power_level" (int, default 9000)'))
def given_simple_model(bdd_context: dict) -> None:
    bdd_context["model_cls"] = SimpleSpellcaster


@given('a model with an optional "callsign" field')
def given_optional_model(bdd_context: dict) -> None:
    bdd_context["model_cls"] = OptionalCallsign


@given('a model with an enum "faction" field')
def given_enum_model(bdd_context: dict) -> None:
    bdd_context["model_cls"] = FactionModel


@given('a model with a list "allies" field')
def given_list_model(bdd_context: dict) -> None:
    bdd_context["model_cls"] = AllyList


@given('a model with a nested "homeworld" model')
def given_nested_model(bdd_context: dict) -> None:
    bdd_context["model_cls"] = NestedModel


@when(parsers.parse('the wizard runs with inputs "{input1}" and "{input2}"'))
def when_two_inputs(input1: str, input2: str, bdd_context: dict) -> None:
    result, output = _run_wizard(
        bdd_context["model_cls"],
        [input1, input2],
    )
    bdd_context["result"] = result
    bdd_context["output"] = output


@when("the wizard runs with empty input")
def when_empty_input(bdd_context: dict) -> None:
    result, output = _run_wizard(bdd_context["model_cls"], [""])
    bdd_context["result"] = result
    bdd_context["output"] = output


@when(parsers.parse('the wizard runs with input "{value}"'))
def when_single_input(value: str, bdd_context: dict) -> None:
    result, output = _run_wizard(bdd_context["model_cls"], [value])
    bdd_context["result"] = result
    bdd_context["output"] = output


@when(parsers.parse('the wizard runs with inputs "{input1}" and "{input2}" and summary enabled'))
def when_two_inputs_summary(input1: str, input2: str, bdd_context: dict) -> None:
    result, output = _run_wizard(
        bdd_context["model_cls"],
        [input1, input2],
        show_summary=True,
    )
    bdd_context["result"] = result
    bdd_context["output"] = output


@when(parsers.parse('the wizard runs with inputs "{input1}", "{input2}", and "{input3}"'))
def when_three_inputs(input1: str, input2: str, input3: str, bdd_context: dict) -> None:
    result, output = _run_wizard(
        bdd_context["model_cls"],
        [input1, input2, input3],
    )
    bdd_context["result"] = result
    bdd_context["output"] = output


@then(parsers.parse('the result field "{field}" is "{expected}"'))
def result_field_str(field: str, expected: str, bdd_context: dict) -> None:
    result = bdd_context["result"]

    obj = result
    for part in field.split("."):
        obj = getattr(obj, part)

    if isinstance(obj, Enum):
        assert str(obj.value) == expected, f"{obj.value!r} != {expected!r}"
    elif isinstance(obj, list):
        actual = ", ".join(str(v) for v in obj)
        assert actual == expected, f"{actual!r} != {expected!r}"
    else:
        assert str(obj) == expected, f"{obj!r} != {expected!r}"


@then(parsers.parse('the result field "{field}" is {expected:d}'))
def result_field_int(field: str, expected: int, bdd_context: dict) -> None:
    result = bdd_context["result"]
    obj = result
    for part in field.split("."):
        obj = getattr(obj, part)
    assert obj == expected, f"{obj!r} != {expected!r}"


@then(parsers.parse('the result field "{field}" is None'))
def result_field_none(field: str, bdd_context: dict) -> None:
    result = bdd_context["result"]
    obj = result
    for part in field.split("."):
        obj = getattr(obj, part)
    assert obj is None, f"Expected None, got {obj!r}"
