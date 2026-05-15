from typing import Annotated

import pytest
from pydantic import BaseModel

from wizdantic.lore import (
    PickerContext,
    WizardLore,
    extract_echo,
    extract_hint,
    extract_parser,
    extract_picker,
    extract_section,
)


class TestWizardLore:
    def test_frozen(self):
        lore = WizardLore(section="Identity")
        assert lore.section == "Identity"

    def test_default_section_is_none(self):
        lore = WizardLore()
        assert lore.section is None

    def test_hint_field(self):
        lore = WizardLore(hint="enter a planet name")
        assert lore.hint == "enter a planet name"

    def test_default_hint_is_none(self):
        lore = WizardLore()
        assert lore.hint is None

    def test_parser_field(self):
        def my_parser(raw: str) -> int:
            return int(raw)

        lore = WizardLore(parser=my_parser)
        assert lore.parser is my_parser

    def test_default_parser_is_none(self):
        lore = WizardLore()
        assert lore.parser is None

    def test_immutable(self):
        lore = WizardLore(section="Identity", hint="a hint")
        with pytest.raises(Exception):
            lore.hint = "changed"  # type: ignore

    def test_picker_field(self):
        def my_picker(ctx: PickerContext) -> str:
            return "red"

        lore = WizardLore(picker=my_picker)
        assert lore.picker is my_picker

    def test_default_picker_is_none(self):
        lore = WizardLore()
        assert lore.picker is None

    def test_echo_field_true(self):
        lore = WizardLore(echo=True)
        assert lore.echo is True

    def test_echo_field_false(self):
        lore = WizardLore(echo=False)
        assert lore.echo is False

    def test_default_echo_is_none(self):
        lore = WizardLore()
        assert lore.echo is None


class TestExtractSection:
    def test_with_section(self):
        class M(BaseModel):
            name: Annotated[str, WizardLore(section="Identity")] = "x"

        assert extract_section(M.model_fields["name"]) == "Identity"

    def test_without_section(self):
        class M(BaseModel):
            name: str = "x"

        assert extract_section(M.model_fields["name"]) is None

    def test_metadata_without_wizard_lore(self):
        class M(BaseModel):
            name: Annotated[str, "some_other_metadata"] = "x"

        assert extract_section(M.model_fields["name"]) is None

    def test_wizard_lore_with_no_section(self):
        """A WizardLore with section=None is ignored."""

        class M(BaseModel):
            name: Annotated[str, WizardLore()] = "x"

        assert extract_section(M.model_fields["name"]) is None

    def test_section_from_model_field(self):
        """Extract section from a field defined on an actual model."""

        class MyModel(BaseModel):
            name: Annotated[str, WizardLore(section="Details")] = "test"

        fi = MyModel.model_fields["name"]
        assert extract_section(fi) == "Details"


class TestExtractHint:
    def test_with_hint(self):
        class M(BaseModel):
            name: Annotated[str, WizardLore(hint="planet name")] = "x"

        assert extract_hint(M.model_fields["name"]) == "planet name"

    def test_without_hint(self):
        class M(BaseModel):
            name: str = "x"

        assert extract_hint(M.model_fields["name"]) is None

    def test_wizard_lore_with_no_hint(self):
        """A WizardLore with hint=None returns None."""

        class M(BaseModel):
            name: Annotated[str, WizardLore()] = "x"

        assert extract_hint(M.model_fields["name"]) is None

    def test_hint_and_section_together(self):
        class M(BaseModel):
            name: Annotated[str, WizardLore(section="Combat", hint="alchemy skill 1-10")] = "x"

        assert extract_hint(M.model_fields["name"]) == "alchemy skill 1-10"
        assert extract_section(M.model_fields["name"]) == "Combat"

    def test_no_wizard_lore_in_metadata(self):
        class M(BaseModel):
            name: Annotated[str, "unrelated"] = "x"

        assert extract_hint(M.model_fields["name"]) is None


class TestExtractParser:
    def test_with_parser(self):
        def parse_credits(raw: str) -> int:
            return int(raw.replace(",", ""))

        class M(BaseModel):
            credits: Annotated[int, WizardLore(parser=parse_credits)] = 0

        result = extract_parser(M.model_fields["credits"])
        assert result is parse_credits

    def test_without_parser(self):
        class M(BaseModel):
            name: str = "x"

        assert extract_parser(M.model_fields["name"]) is None

    def test_wizard_lore_with_no_parser(self):
        class M(BaseModel):
            name: Annotated[str, WizardLore()] = "x"

        assert extract_parser(M.model_fields["name"]) is None

    def test_no_wizard_lore_in_metadata(self):
        class M(BaseModel):
            name: Annotated[str, "unrelated"] = "x"

        assert extract_parser(M.model_fields["name"]) is None


class TestPickerContext:
    def test_fields_are_accessible(self):
        ctx = PickerContext(name="color", description="A hex color", default="#ff0000", hint="e.g. #aabbcc")
        assert ctx.name == "color"
        assert ctx.description == "A hex color"
        assert ctx.default == "#ff0000"
        assert ctx.hint == "e.g. #aabbcc"

    def test_optional_fields_default_to_none(self):
        ctx = PickerContext(name="color", description=None, default=None, hint=None)
        assert ctx.description is None
        assert ctx.default is None
        assert ctx.hint is None

    def test_immutable(self):
        ctx = PickerContext(name="color", description=None, default=None, hint=None)
        with pytest.raises(Exception):
            ctx.name = "other"  # type: ignore


class TestExtractPicker:
    def test_with_picker(self):
        def my_picker(ctx: PickerContext) -> str:
            return "#000000"

        class M(BaseModel):
            color: Annotated[str, WizardLore(picker=my_picker)] = "#ffffff"

        result = extract_picker(M.model_fields["color"])
        assert result is my_picker

    def test_without_picker(self):
        class M(BaseModel):
            name: str = "x"

        assert extract_picker(M.model_fields["name"]) is None

    def test_wizard_lore_with_no_picker(self):
        class M(BaseModel):
            name: Annotated[str, WizardLore()] = "x"

        assert extract_picker(M.model_fields["name"]) is None

    def test_no_wizard_lore_in_metadata(self):
        class M(BaseModel):
            name: Annotated[str, "unrelated"] = "x"

        assert extract_picker(M.model_fields["name"]) is None


class TestExtractEcho:
    def test_with_echo_true(self):
        class M(BaseModel):
            name: Annotated[str, WizardLore(echo=True)] = "x"

        assert extract_echo(M.model_fields["name"]) is True

    def test_with_echo_false(self):
        class M(BaseModel):
            name: Annotated[str, WizardLore(echo=False)] = "x"

        assert extract_echo(M.model_fields["name"]) is False

    def test_without_echo(self):
        class M(BaseModel):
            name: str = "x"

        assert extract_echo(M.model_fields["name"]) is None

    def test_wizard_lore_with_no_echo(self):
        """WizardLore with echo=None returns None — defers to wizard-level default."""

        class M(BaseModel):
            name: Annotated[str, WizardLore()] = "x"

        assert extract_echo(M.model_fields["name"]) is None

    def test_no_wizard_lore_in_metadata(self):
        class M(BaseModel):
            name: Annotated[str, "unrelated"] = "x"

        assert extract_echo(M.model_fields["name"]) is None
