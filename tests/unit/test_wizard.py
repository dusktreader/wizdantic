from enum import Enum
from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field, SecretStr
from rich.console import Console

from wizdantic.exceptions import UnsupportedFieldType
from wizdantic.lore import WizardLore
from pydantic_core import PydanticUndefined
from wizdantic.wizard import Wizard, WizardAborted, run_wizard


class Faction(str, Enum):
    ARCANE = "arcane"
    SHADOW = "shadow"
    HUTT_CARTEL = "hutt_cartel"


class Realm(BaseModel):
    name: str = Field(description="Realm name")
    system: str = Field(description="Star system", default="Outer Rim")


class MageProfile(BaseModel):
    name: str = Field(description="Mage name")
    mana_reserve: int = Field(description="Mana reserve", default=10000)
    has_familiar: bool = Field(description="Has a familiar", default=True)


class BountyHunter(BaseModel):
    name: str = Field(description="Hunter name")
    faction: Faction = Field(description="Faction allegiance", default=Faction.SHADOW)
    targets: list[str] = Field(description="Current bounty targets", default_factory=list)
    homeworld: Realm = Field(description="Home realm")


class Warlock(BaseModel):
    shadow_name: str = Field(description="Shadow title")
    true_name: SecretStr = Field(description="True identity")
    power_level: float = Field(description="Dark side power level", default=9000.0)


class SectionedCrewMember(BaseModel):
    name: Annotated[str, WizardLore(section="Identity")] = Field(
        description="Crew member name",
    )
    species: Annotated[str, WizardLore(section="Identity")] = Field(
        description="Species",
    )
    alchemy_skill: Annotated[int, WizardLore(section="Combat")] = Field(
        description="Alchemy proficiency",
        default=5,
    )
    ship: str = Field(description="Assigned ship", default="Thornspire Tower")


class SpeedSetting(BaseModel):
    mode: Literal["volatile", "astral", "mundane"] = Field(
        description="Speed mode",
        default="astral",
    )


class OptionalFields(BaseModel):
    nickname: str | None = Field(description="Call sign", default=None)
    bounty: int | None = Field(description="Bounty in credits", default=None)


@pytest.fixture
def console():
    """A console that writes to an in-memory buffer so tests stay silent."""
    import io

    return Console(file=io.StringIO(), force_terminal=True)


class TestWizardSimpleModel:
    def test_collects_string_and_int_with_defaults(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Veyra", "15000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        result = run_wizard(MageProfile, console=console, show_summary=False)

        assert result.name == "Veyra"
        assert result.mana_reserve == 15000
        assert result.has_familiar is True

    def test_accepts_defaults_by_returning_default_str(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Theron", "10000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        result = run_wizard(MageProfile, console=console, show_summary=False)

        assert result.name == "Theron"
        assert result.mana_reserve == 10000
        assert result.has_familiar is True


class TestWizardBoolField:
    def test_bool_default_true(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Aldric", "20000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=False)

        result = run_wizard(MageProfile, console=console, show_summary=False)

        assert result.has_familiar is False


class TestWizardEnumField:
    def test_select_enum_by_index(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Silas Thornward",  # name
                "1",  # faction: arcane (index 1)
                "",  # targets (default empty list)
                "Ashenmoor",  # nested: realm name
                "Outer Rim",  # nested: system (default)
            ],
        )

        result = run_wizard(BountyHunter, console=console, show_summary=False)

        assert result.name == "Silas Thornward"
        assert result.faction == Faction.ARCANE

    def test_select_enum_by_value(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Corvin Ashveil",  # name
                "hutt_cartel",  # faction by value
                "",  # targets
                "Crystalspire",  # nested realm
                "Misthollow",  # nested system
            ],
        )

        result = run_wizard(BountyHunter, console=console, show_summary=False)

        assert result.faction == Faction.HUTT_CARTEL


class TestWizardSecretField:
    def test_secret_collected_and_masked(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Shadow Weaver",  # shadow_name
                "Caelum",  # true_name (password prompt)
                "9001.0",  # power_level
            ],
        )

        result = run_wizard(Warlock, console=console, show_summary=False)

        assert result.shadow_name == "Shadow Weaver"
        assert result.true_name.get_secret_value() == "Caelum"
        assert result.power_level == 9001.0


class TestWizardListField:
    def test_comma_separated_list(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Riven Hollow",  # name
                "2",  # faction: shadow
                "Mordain, Elara, Grimshaw",  # targets
                "Thornwick",  # nested realm
                "Outer Rim",  # nested system
            ],
        )

        result = run_wizard(BountyHunter, console=console, show_summary=False)

        assert result.targets == ["Mordain", "Elara", "Grimshaw"]


class TestWizardNestedModel:
    def test_nested_model_prompted_recursively(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Fenn Ashwood",  # name
                "2",  # faction: shadow
                "Pip",  # targets
                "Irondeep",  # nested: realm name
                "Irondeep",  # nested: system
            ],
        )

        result = run_wizard(BountyHunter, console=console, show_summary=False)

        assert isinstance(result.homeworld, Realm)
        assert result.homeworld.name == "Irondeep"
        assert result.homeworld.system == "Irondeep"


class TestWizardLiteralField:
    def test_select_literal_by_index(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="1")

        result = run_wizard(SpeedSetting, console=console, show_summary=False)

        assert result.mode == "volatile"

    def test_select_literal_by_value(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="mundane")

        result = run_wizard(SpeedSetting, console=console, show_summary=False)

        assert result.mode == "mundane"


class TestWizardOptionalFields:
    def test_optional_returns_none_on_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", ""])

        result = run_wizard(OptionalFields, console=console, show_summary=False)

        assert result.nickname is None
        assert result.bounty is None

    def test_optional_accepts_values(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Crimson Wand", "5000"])

        result = run_wizard(OptionalFields, console=console, show_summary=False)

        assert result.nickname == "Crimson Wand"
        assert result.bounty == 5000


class TestWizardSections:
    def test_fields_grouped_by_section(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Bramble",  # name (Identity section)
                "Owlbear",  # species (Identity section)
                "8",  # alchemy_skill (Combat section)
                "Thornspire Tower",  # ship (Other section)
            ],
        )

        result = run_wizard(SectionedCrewMember, console=console, show_summary=False)

        assert result.name == "Bramble"
        assert result.species == "Owlbear"
        assert result.alchemy_skill == 8
        assert result.ship == "Thornspire Tower"

    def test_section_grouping_structure(self):
        wiz = Wizard(SectionedCrewMember)
        groups = wiz._group_fields()

        section_names = [name for name, _ in groups]
        assert section_names == ["Identity", "Combat", "Other"]

        identity_fields = [name for name, _ in groups[0][1]]
        assert identity_fields == ["name", "species"]

        combat_fields = [name for name, _ in groups[1][1]]
        assert combat_fields == ["alchemy_skill"]

        other_fields = [name for name, _ in groups[2][1]]
        assert other_fields == ["ship"]


class TestWizardSummary:
    def test_summary_shown_by_default(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Orlen Stormrune", "18000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        run_wizard(MageProfile, console=console, show_summary=True)

        output = console.file.getvalue()
        assert "Summary" in output
        assert "Orlen Stormrune" in output

    def test_summary_hidden_when_disabled(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Orlen Stormrune", "18000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        run_wizard(MageProfile, console=console, show_summary=False)

        output = console.file.getvalue()
        assert "Summary" not in output


class TestWizardValidation:
    def test_invalid_then_valid_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Isolde",
                "not_a_number",  # invalid int
                "14000",  # valid retry
            ],
        )
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        result = run_wizard(MageProfile, console=console, show_summary=False)

        assert result.mana_reserve == 14000

        output = console.file.getvalue()
        assert "Invalid" in output


class TestWizardConvenienceFunction:
    def test_wizard_function_returns_model(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Seraphina", "12000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        result = run_wizard(MageProfile, console=console, show_summary=False)

        assert isinstance(result, MageProfile)
        assert result.name == "Seraphina"


class TestWizardRequiredVsDefaulted:
    """FieldInfo.get_default returns PydanticUndefined for required fields."""

    def test_required_field_has_no_default(self):
        fi = MageProfile.model_fields["name"]
        assert fi.get_default(call_default_factory=True) is PydanticUndefined

    def test_defaulted_field_has_default(self):
        fi = MageProfile.model_fields["mana_reserve"]
        assert fi.get_default(call_default_factory=True) == 10000


class OptionalEnum(BaseModel):
    faction: Faction | None = Field(description="Faction allegiance", default=None)


class RequiredEnum(BaseModel):
    faction: Faction = Field(description="Faction allegiance")


class OptionalLiteral(BaseModel):
    mode: Literal["volatile", "astral", "mundane"] | None = Field(
        description="Speed mode",
        default=None,
    )


class RequiredLiteral(BaseModel):
    mode: Literal["volatile", "astral", "mundane"] = Field(
        description="Speed mode",
    )


class OptionalSecret(BaseModel):
    code: SecretStr | None = Field(description="Access code", default=None)


class RequiredList(BaseModel):
    names: list[str] = Field(description="Names")


class RequiredIntList(BaseModel):
    scores: list[int] = Field(description="Scores")


class TestWizardEnumEdgeCases:
    def test_optional_enum_returns_none_on_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(OptionalEnum, console=console, show_summary=False)

        assert result.faction is None

    def test_enum_out_of_range_retries(self, mocker, console):
        """Index outside valid range shows error and re-prompts."""
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["99", "1"],
        )

        result = run_wizard(RequiredEnum, console=console, show_summary=False)

        assert result.faction == Faction.ARCANE
        output = console.file.getvalue()
        assert "Choose between" in output

    def test_enum_invalid_name_retries(self, mocker, console):
        """Unrecognized text shows 'Invalid choice' and re-prompts."""
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["necro_order", "arcane"],
        )

        result = run_wizard(RequiredEnum, console=console, show_summary=False)

        assert result.faction == Faction.ARCANE
        output = console.file.getvalue()
        assert "Invalid choice" in output

    def test_required_enum_empty_input_retries(self, mocker, console):
        """Required enum with no default insists on a selection."""
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["", "2"],
        )

        result = run_wizard(RequiredEnum, console=console, show_summary=False)

        assert result.faction == Faction.SHADOW
        output = console.file.getvalue()
        assert "selection is required" in output


class TestWizardLiteralEdgeCases:
    def test_optional_literal_returns_none_on_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(OptionalLiteral, console=console, show_summary=False)

        assert result.mode is None

    def test_literal_out_of_range_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["99", "1"],
        )

        result = run_wizard(RequiredLiteral, console=console, show_summary=False)

        assert result.mode == "volatile"
        output = console.file.getvalue()
        assert "Choose between" in output

    def test_literal_invalid_value_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["warp_speed", "mundane"],
        )

        result = run_wizard(RequiredLiteral, console=console, show_summary=False)

        assert result.mode == "mundane"
        output = console.file.getvalue()
        assert "Invalid choice" in output

    def test_required_literal_empty_input_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["", "2"],
        )

        result = run_wizard(RequiredLiteral, console=console, show_summary=False)

        assert result.mode == "astral"
        output = console.file.getvalue()
        assert "selection is required" in output


class TestWizardSecretEdgeCases:
    def test_optional_secret_returns_none_on_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(OptionalSecret, console=console, show_summary=False)

        assert result.code is None

    def test_secret_keeps_default_on_masked_placeholder(self, mocker, console):
        """Accepting the length-matched masked placeholder returns the original default."""

        class DefaultedSecret(BaseModel):
            code: SecretStr = Field(description="Access code", default=SecretStr("order66"))

        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="*******")  # len("order66") == 7

        result = run_wizard(DefaultedSecret, console=console, show_summary=False)

        assert result.code.get_secret_value() == "order66"


class TestWizardListEdgeCases:
    def test_list_validation_retry(self, mocker, console):
        """Invalid list items trigger a validation error and re-prompt."""
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["abc, xyz", "10, 20, 30"],
        )

        result = run_wizard(RequiredIntList, console=console, show_summary=False)

        assert result.scores == [10, 20, 30]
        output = console.file.getvalue()
        assert "Invalid" in output

    def test_optional_list_returns_none_on_empty(self, mocker, console):
        class OptionalList(BaseModel):
            items: list[str] | None = Field(description="Items", default=None)

        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(OptionalList, console=console, show_summary=False)

        assert result.items is None

    def test_non_required_list_empty_returns_empty(self, mocker, console):
        """A list with a default that gets empty input returns `[]`."""
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Garrek",  # name
                "2",  # faction: shadow
                "",  # targets (empty, default_factory=list)
                "Bogmere",  # nested realm
                "Outer Rim",  # nested system
            ],
        )

        result = run_wizard(BountyHunter, console=console, show_summary=False)

        assert result.targets == []


class TestWizardCustomTitle:
    def test_custom_title_shown(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Mordain", "25000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        run_wizard(MageProfile, console=console, show_summary=False, title="Mage Registration")

        output = console.file.getvalue()
        assert "Mage Registration" in output

    def test_default_title_from_model_name(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Elara", "14000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        run_wizard(MageProfile, console=console, show_summary=False)

        output = console.file.getvalue()
        assert "Mage Profile" in output


class TestWizardClassDirect:
    def test_wizard_class_returns_correct_type(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Caelum", "27000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        wiz = Wizard(MageProfile, console=console, show_summary=False)
        result = wiz.run()

        assert isinstance(result, MageProfile)
        assert result.name == "Caelum"

    def test_no_sections_no_other_heading(self):
        """Models without any sections produce no section headings at all."""
        wiz = Wizard(MageProfile)
        groups = wiz._group_fields()

        assert len(groups) == 1
        section_name, fields = groups[0]
        assert section_name is None
        assert len(fields) == 3


class OptionalBool(BaseModel):
    armed: bool | None = Field(description="Carries weapons", default=None)


class RequiredString(BaseModel):
    callsign: str = Field(description="Call sign")


class RequiredSecret(BaseModel):
    code: SecretStr = Field(description="Access code")


class DefaultedList(BaseModel):
    targets: list[str] = Field(description="Targets", default_factory=list)


class TestWizardOptionalBool:
    def test_optional_bool_returns_true_on_y(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="y")

        result = run_wizard(OptionalBool, console=console, show_summary=False)

        assert result.armed is True

    def test_optional_bool_returns_false_on_n(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="n")

        result = run_wizard(OptionalBool, console=console, show_summary=False)

        assert result.armed is False

    def test_optional_bool_returns_none_on_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(OptionalBool, console=console, show_summary=False)

        assert result.armed is None

    def test_optional_bool_invalid_then_valid(self, mocker, console):
        """Unrecognized input shows an error and re-prompts."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["maybe", "y"])

        result = run_wizard(OptionalBool, console=console, show_summary=False)

        assert result.armed is True
        output = console.file.getvalue()
        assert "Enter y or n" in output


class TestWizardRequiredValueMessage:
    def test_required_string_empty_then_valid(self, mocker, console):
        """Empty input on a required field shows 'A value is required' and re-prompts."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", "Crimson Wand"])

        result = run_wizard(RequiredString, console=console, show_summary=False)

        assert result.callsign == "Crimson Wand"
        output = console.file.getvalue()
        assert "value is required" in output

    def test_required_secret_empty_then_valid(self, mocker, console):
        """Empty input on a required secret field shows 'A value is required'."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", "order66"])

        result = run_wizard(RequiredSecret, console=console, show_summary=False)

        assert result.code.get_secret_value() == "order66"
        output = console.file.getvalue()
        assert "value is required" in output


class TestWizardListWhitespaceInput:
    def test_whitespace_only_input_treated_as_empty(self, mocker, console):
        """Whitespace-only input is treated the same as empty input for non-required lists."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="   ")

        result = run_wizard(DefaultedList, console=console, show_summary=False)

        assert result.targets == []

    def test_whitespace_with_commas_treated_as_empty(self, mocker, console):
        """Input of only commas and spaces produces an empty list, not a required error."""
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value=" , , ")

        result = run_wizard(DefaultedList, console=console, show_summary=False)

        assert result.targets == []


# ---------------------------------------------------------------------------
# New collection type models
# ---------------------------------------------------------------------------


class ShipManifest(BaseModel):
    crew: list[str] = Field(description="Crew members", default_factory=list)


class WaypointLog(BaseModel):
    coordinates: tuple[float, ...] = Field(description="Waypoint coordinates", default_factory=tuple)


class FixedCoord(BaseModel):
    point: tuple[str, int] = Field(description="Named coordinate point")


class AllianceSet(BaseModel):
    factions: set[str] = Field(description="Allied factions", default_factory=set)


class GrimoireIndex(BaseModel):
    entries: dict[str, str] = Field(description="Grimoire index entries", default_factory=dict)


class IntKeyMap(BaseModel):
    scores: dict[str, int] = Field(description="Score map", default_factory=dict)


class FleetRoster(BaseModel):
    name: str = Field(description="Fleet name")
    ships: list[Realm] = Field(description="Ships in fleet")


class TestWizardListJsonInput:
    def test_list_accepts_json_array(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value='["Mordain", "Elara", "Grimshaw"]')

        result = run_wizard(ShipManifest, console=console, show_summary=False)

        assert result.crew == ["Mordain", "Elara", "Grimshaw"]

    def test_list_falls_back_to_csv(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="Mordain, Elara, Grimshaw")

        result = run_wizard(ShipManifest, console=console, show_summary=False)

        assert result.crew == ["Mordain", "Elara", "Grimshaw"]

    def test_list_csv_strips_whitespace(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="  Mordain  ,  Elara  ")

        result = run_wizard(ShipManifest, console=console, show_summary=False)

        assert result.crew == ["Mordain", "Elara"]

    def test_list_invalid_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["not valid json and not csv int", "1, 2, 3"],
        )

        class IntList(BaseModel):
            values: list[int] = Field(description="Values")

        result = run_wizard(IntList, console=console, show_summary=False)

        assert result.values == [1, 2, 3]
        assert "Invalid" in console.file.getvalue()

    def test_list_empty_non_required_returns_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(ShipManifest, console=console, show_summary=False)

        assert result.crew == []


class TestWizardTupleInput:
    def test_homogeneous_tuple_json(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="[1.5, 2.5, 3.5]")

        result = run_wizard(WaypointLog, console=console, show_summary=False)

        assert result.coordinates == pytest.approx((1.5, 2.5, 3.5))

    def test_homogeneous_tuple_csv(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="1.5, 2.5, 3.5")

        result = run_wizard(WaypointLog, console=console, show_summary=False)

        assert result.coordinates == pytest.approx((1.5, 2.5, 3.5))

    def test_fixed_tuple_json(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value='["Sector 7", 42]')

        result = run_wizard(FixedCoord, console=console, show_summary=False)

        assert result.point == ("Sector 7", 42)

    def test_fixed_tuple_wrong_length_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=['["only_one"]', '["Sector 7", 42]'],
        )

        result = run_wizard(FixedCoord, console=console, show_summary=False)

        assert result.point == ("Sector 7", 42)
        assert "Expected" in console.file.getvalue()

    def test_fixed_tuple_invalid_element_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=['["Sector 7", "not_an_int"]', '["Sector 8", 99]'],
        )

        result = run_wizard(FixedCoord, console=console, show_summary=False)

        assert result.point == ("Sector 8", 99)

    def test_fixed_tuple_invalid_json_retries(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["not json at all", '["Sector 9", 7]'],
        )

        result = run_wizard(FixedCoord, console=console, show_summary=False)

        assert result.point == ("Sector 9", 7)


class TestWizardSetInput:
    def test_set_json_array(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value='["arcane", "mage"]')

        result = run_wizard(AllianceSet, console=console, show_summary=False)

        assert result.factions == {"arcane", "mage"}

    def test_set_csv_input(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="arcane, mage")

        result = run_wizard(AllianceSet, console=console, show_summary=False)

        assert result.factions == {"arcane", "mage"}

    def test_set_duplicates_error_and_retry(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=['["arcane", "arcane", "mage"]', '["arcane", "mage"]'],
        )

        result = run_wizard(AllianceSet, console=console, show_summary=False)

        assert result.factions == {"arcane", "mage"}
        assert "Duplicate" in console.file.getvalue()

    def test_set_csv_duplicates_error_and_retry(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["arcane, arcane, mage", "arcane, mage"],
        )

        result = run_wizard(AllianceSet, console=console, show_summary=False)

        assert result.factions == {"arcane", "mage"}
        assert "Duplicate" in console.file.getvalue()

    def test_set_empty_non_required_returns_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(AllianceSet, console=console, show_summary=False)

        assert result.factions == set()

    def test_set_invalid_input_retries(self, mocker, console):
        class IntSet(BaseModel):
            scores: set[int] = Field(description="Scores", default_factory=set)

        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["not_a_number, also_not", "1, 2, 3"],
        )

        result = run_wizard(IntSet, console=console, show_summary=False)

        assert result.scores == {1, 2, 3}
        assert "Invalid" in console.file.getvalue()

    def test_set_required_empty_retries(self, mocker, console):
        class RequiredSet(BaseModel):
            tags: set[str] = Field(description="Tags")

        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["", '["shadow"]'],
        )

        result = run_wizard(RequiredSet, console=console, show_summary=False)

        assert result.tags == {"shadow"}
        assert "required" in console.file.getvalue()


class TestWizardDictInput:
    def test_dict_json_object(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            return_value='{"realm": "embervault", "domain": "shadowfell"}',
        )

        result = run_wizard(GrimoireIndex, console=console, show_summary=False)

        assert result.entries == {"realm": "embervault", "domain": "shadowfell"}

    def test_dict_kv_notation(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            return_value="realm:embervault, domain:shadowfell",
        )

        result = run_wizard(GrimoireIndex, console=console, show_summary=False)

        assert result.entries == {"realm": "embervault", "domain": "shadowfell"}

    def test_dict_kv_strips_whitespace(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            return_value=" realm : embervault , domain : shadowfell ",
        )

        result = run_wizard(GrimoireIndex, console=console, show_summary=False)

        assert result.entries == {"realm": "embervault", "domain": "shadowfell"}

    def test_dict_int_values(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            return_value="grimshaw:100, elara:95, mordain:88",
        )

        result = run_wizard(IntKeyMap, console=console, show_summary=False)

        assert result.scores == {"grimshaw": 100, "elara": 95, "mordain": 88}

    def test_dict_empty_non_required_returns_empty(self, mocker, console):
        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(GrimoireIndex, console=console, show_summary=False)

        assert result.entries == {}

    def test_dict_bad_kv_retries(self, mocker, console):
        """A value with multiple colons is rejected, then valid input is accepted."""
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["url:https://example.com", "site:sanctum"],
        )

        result = run_wizard(GrimoireIndex, console=console, show_summary=False)

        assert result.entries == {"site": "sanctum"}
        assert "Invalid" in console.file.getvalue()

    def test_dict_required_empty_retries(self, mocker, console):
        class RequiredDict(BaseModel):
            index: dict[str, str] = Field(description="Index")

        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["", "key:value"],
        )

        result = run_wizard(RequiredDict, console=console, show_summary=False)

        assert result.index == {"key": "value"}
        assert "required" in console.file.getvalue()


class TestWizardListOfModels:
    def test_list_of_models_via_sub_wizard(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Shadow Conclave",  # fleet name
                "Nighthaven",  # ship 1: name
                "Deep Core",  # ship 1: system
                "Duskward",  # ship 2: name
                "Outer Rim",  # ship 2: system
            ],
        )
        # First confirm: add another? yes. Second confirm: add another? no.
        mocker.patch("wizdantic.prompts.Confirm.ask", side_effect=[True, False])

        result = run_wizard(FleetRoster, console=console, show_summary=False)

        assert result.name == "Shadow Conclave"
        assert len(result.ships) == 2
        assert result.ships[0].name == "Nighthaven"
        assert result.ships[1].name == "Duskward"

    def test_list_of_models_single_item(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=[
                "Arcane Order",
                "Starfall Keep",
                "Everdeep",
            ],
        )
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=False)

        result = run_wizard(FleetRoster, console=console, show_summary=False)

        assert len(result.ships) == 1
        assert result.ships[0].name == "Starfall Keep"


class TestWizardLoreHint:
    """WizardLore hint replaces auto-generated format hints in the prompt."""

    def test_custom_hint_shown_for_str_field(self, mocker, console):
        """A user-supplied hint appears in the prompt label for a scalar field."""

        class HintedModel(BaseModel):
            code: Annotated[str, Field(description="Access code"), WizardLore(hint="e.g. ORD-1138")]

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="ORD-1138")

        result = run_wizard(HintedModel, console=console, show_summary=False)

        assert result.code == "ORD-1138"
        label_arg = mock_ask.call_args_list[0][0][0]
        assert "e.g. ORD-1138" in label_arg

    def test_custom_hint_for_list_field_replaces_default(self, mocker, console):
        """A user-supplied hint replaces `(JSON array or comma-separated)` for list fields."""

        class HintedList(BaseModel):
            realms: Annotated[
                list[str],
                Field(description="Realm list"),
                WizardLore(hint="one per line or comma-separated"),
            ] = []

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="embervault, frostholm")

        result = run_wizard(HintedList, console=console, show_summary=False)

        assert result.realms == ["embervault", "frostholm"]
        label_arg = mock_ask.call_args_list[0][0][0]
        assert "one per line or comma-separated" in label_arg

    def test_hint_appears_in_prompt_label_for_value_field(self, mocker, console):
        """The label passed to Prompt.ask contains the custom hint text."""

        class HintedValue(BaseModel):
            mana_reserve: Annotated[
                int,
                Field(description="Mana reserve"),
                WizardLore(hint="typical range 5000-20000"),
            ] = 10000

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="12000")

        run_wizard(HintedValue, console=console, show_summary=False)

        label_arg = mock_ask.call_args[0][0]
        assert "typical range 5000-20000" in label_arg

    def test_hint_appears_for_optional_bool(self, mocker, console):
        """A user-supplied hint replaces the default `(y/n, leave blank for none)` hint."""

        class HintedBool(BaseModel):
            arcane_sensitive: Annotated[
                bool | None,
                Field(description="Arcane sensitive"),
                WizardLore(hint="yes or no"),
            ] = None

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="yes")

        result = run_wizard(HintedBool, console=console, show_summary=False)

        assert result.arcane_sensitive is True
        label_arg = mock_ask.call_args[0][0]
        assert "yes or no" in label_arg

    def test_hint_appears_for_dict_field(self, mocker, console):
        """A user-supplied hint replaces the default dict hint."""

        class HintedDict(BaseModel):
            registry: Annotated[
                dict[str, str],
                Field(description="Ship registry"),
                WizardLore(hint="format: name=class"),
            ] = {}

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value='{"wyvern": "familiar"}')

        result = run_wizard(HintedDict, console=console, show_summary=False)

        assert result.registry == {"wyvern": "familiar"}
        label_arg = mock_ask.call_args[0][0]
        assert "format: name=class" in label_arg

    def test_hint_appears_for_set_field(self, mocker, console):
        """A user-supplied hint replaces the default set hint."""

        class HintedSet(BaseModel):
            allegiances: Annotated[
                set[str],
                Field(description="Allegiances"),
                WizardLore(hint="JSON list of factions"),
            ] = set()

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value='["arcane", "mage"]')

        result = run_wizard(HintedSet, console=console, show_summary=False)

        assert result.allegiances == {"arcane", "mage"}
        label_arg = mock_ask.call_args[0][0]
        assert "JSON list of factions" in label_arg

    def test_default_hint_for_set_field(self, mocker, console):
        """The default set hint includes the item type name and CSV notation."""

        class BareSet(BaseModel):
            allegiances: set[str] = set()

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="arcane, mage")

        run_wizard(BareSet, console=console, show_summary=False)

        label_arg = mock_ask.call_args[0][0]
        assert "str" in label_arg
        assert "comma-separated" in label_arg


class TestWizardLoreParser:
    """WizardLore parser replaces TypeAdapter validation for a field."""

    def test_custom_parser_for_str_field(self, mocker, console):
        """A custom parser transforms raw input before storing on the model."""

        def upper_parser(raw: str) -> str:
            return raw.upper()

        class ParsedModel(BaseModel):
            code: Annotated[str, Field(description="Code"), WizardLore(parser=upper_parser)]

        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="ord-1138")

        result = run_wizard(ParsedModel, console=console, show_summary=False)

        assert result.code == "ORD-1138"

    def test_custom_parser_for_int_field(self, mocker, console):
        """A custom parser can parse a formatted number string into an int."""

        def credits_parser(raw: str) -> int:
            return int(raw.replace(",", "").replace(" credits", ""))

        class CreditsModel(BaseModel):
            bounty: Annotated[int, Field(description="Bounty"), WizardLore(parser=credits_parser)]

        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="1,000,000 credits")

        result = run_wizard(CreditsModel, console=console, show_summary=False)

        assert result.bounty == 1_000_000

    def test_custom_parser_retries_on_exception(self, mocker, console):
        """When the parser raises, an error is shown and the prompt retries."""

        call_count = 0

        def strict_parser(raw: str) -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("bad input")
            return int(raw)

        class RetryModel(BaseModel):
            level: Annotated[int, Field(description="Level"), WizardLore(parser=strict_parser)]

        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["bad", "42"])

        result = run_wizard(RetryModel, console=console, show_summary=False)

        assert result.level == 42
        assert "Invalid" in console.file.getvalue()

    def test_custom_parser_for_list_field(self, mocker, console):
        """A custom parser on a list field replaces all built-in parse logic."""

        def pipe_parser(raw: str) -> list[str]:
            return [item.strip() for item in raw.split("|") if item.strip()]

        class PipedList(BaseModel):
            targets: Annotated[
                list[str],
                Field(description="Targets"),
                WizardLore(parser=pipe_parser),
            ]

        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="grimshaw | elara | bramble")

        result = run_wizard(PipedList, console=console, show_summary=False)

        assert result.targets == ["grimshaw", "elara", "bramble"]

    def test_custom_parser_for_optional_field_blank_returns_none(self, mocker, console):
        """Optional blank-check runs before the parser; blank returns None."""

        def loud_parser(raw: str) -> str:
            return raw.upper()

        class OptionalParsed(BaseModel):
            callsign: Annotated[str | None, Field(description="Callsign"), WizardLore(parser=loud_parser)] = None

        mocker.patch("wizdantic.prompts.Prompt.ask", return_value="")

        result = run_wizard(OptionalParsed, console=console, show_summary=False)

        assert result.callsign is None

    def test_custom_parser_with_hint(self, mocker, console):
        """hint and parser can be used together; both are applied correctly."""

        def dash_parser(raw: str) -> list[str]:
            return [item.strip() for item in raw.split("-") if item.strip()]

        class Combined(BaseModel):
            items: Annotated[
                list[str],
                Field(description="Items"),
                WizardLore(hint="dash-separated", parser=dash_parser),
            ]

        mock_ask = mocker.patch("wizdantic.prompts.Prompt.ask", return_value="alpha-beta-gamma")

        result = run_wizard(Combined, console=console, show_summary=False)

        assert result.items == ["alpha", "beta", "gamma"]
        label_arg = mock_ask.call_args_list[0][0][0]
        assert "dash-separated" in label_arg

    def test_parser_result_validated_against_field_constraints(self, mocker, console):
        """After the parser runs, TypeAdapter validates the result against field constraints."""

        def lenient_parser(raw: str) -> int:
            return int(raw.strip())

        class ConstrainedModel(BaseModel):
            power_level: Annotated[
                int,
                Field(description="Power level", ge=1, le=100),
                WizardLore(parser=lenient_parser),
            ]

        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["0", "50"],
        )

        result = run_wizard(ConstrainedModel, console=console, show_summary=False)

        assert result.power_level == 50
        assert "Invalid" in console.file.getvalue()


class TestWizardUnsupportedUnion:
    """Multi-type unions are rejected at Wizard construction time."""

    def test_str_int_union_raises(self):
        class BadModel(BaseModel):
            value: str | int = Field(description="Ambiguous field")

        with pytest.raises(UnsupportedFieldType, match="unsupported type"):
            Wizard(BadModel)

    def test_three_way_union_raises(self):
        class TripleModel(BaseModel):
            value: str | int | float = Field(description="Triple union")

        with pytest.raises(UnsupportedFieldType, match="unsupported type"):
            Wizard(TripleModel)

    def test_optional_is_fine(self):
        """Optional[str] should not trigger the fast-fail."""

        class OkModel(BaseModel):
            value: str | None = Field(description="Optional field", default=None)

        # Should not raise
        Wizard(OkModel)

    def test_run_wizard_also_raises(self, console):
        """The convenience function surfaces the same error."""

        class BadModel(BaseModel):
            value: str | int = Field(description="Ambiguous field")

        with pytest.raises(UnsupportedFieldType, match="unsupported type"):
            run_wizard(BadModel, console=console)

    def test_error_message_includes_field_name(self):
        class BadModel(BaseModel):
            arcane_catalyst: str | int = Field(description="Catalyst type")

        with pytest.raises(UnsupportedFieldType, match="arcane_catalyst"):
            Wizard(BadModel)


class TestWizardAborted:
    """KeyboardInterrupt during a wizard run raises WizardAborted."""

    def test_keyboard_interrupt_raises_wizard_aborted(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=KeyboardInterrupt,
        )

        class SimpleModel(BaseModel):
            name: str = Field(description="Name")

        with pytest.raises(WizardAborted, match="aborted"):
            run_wizard(SimpleModel, console=console, show_summary=False)

    def test_aborted_message_printed_to_console(self, mocker, console):
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=KeyboardInterrupt,
        )

        class SimpleModel(BaseModel):
            name: str = Field(description="Name")

        with pytest.raises(WizardAborted):
            run_wizard(SimpleModel, console=console, show_summary=False)

        assert "aborted" in console.file.getvalue().lower()

    def test_wizard_aborted_is_buzz(self):
        import buzz

        assert issubclass(WizardAborted, buzz.Buzz)


class _MinimalModel(BaseModel):
    name: str = Field(description="Mage name")


class TestMakeLabel:
    def test_with_description(self):
        wiz = Wizard(_MinimalModel)
        label = wiz._make_label("mage_name", "Mage name")
        assert "Mage name" in label
        assert "mage_name" in label

    def test_without_description(self):
        wiz = Wizard(_MinimalModel)
        label = wiz._make_label("mage_name", None)
        assert label == "Mage Name"

    def test_rich_markup_present(self):
        """When description is set, the label includes Rich dim/yellow tags."""
        wiz = Wizard(_MinimalModel)
        label = wiz._make_label("field_name", "My field")
        assert "[dim]" in label
        assert "[yellow]" in label


class TestFormatDisplay:
    def _wiz(self) -> Wizard:
        return Wizard(_MinimalModel)

    def test_none(self):
        result = self._wiz()._format_display(None)
        assert isinstance(result, str)
        assert "(None)" in result

    def test_secret(self):
        result = self._wiz()._format_display(SecretStr("order66"))
        assert isinstance(result, str)
        assert "*" * len("order66") in result

    def test_enum(self):
        class Side(str, Enum):
            LIGHT = "light"
            DARK = "dark"

        assert self._wiz()._format_display(Side.DARK) == "dark"

    def test_list(self):
        assert self._wiz()._format_display(["mordain", "elara"]) == "mordain, elara"

    def test_empty_list(self):
        result = self._wiz()._format_display([])
        assert isinstance(result, str)
        assert "(empty)" in result

    def test_plain(self):
        assert self._wiz()._format_display(42) == "42"

    def test_nested_model(self):
        from rich.table import Table

        class Realm(BaseModel):
            name: str

        p = Realm(name="gloomhaven")
        result = self._wiz()._format_display(p)
        assert isinstance(result, Table)
        assert result.row_count == 1

    def test_nested_model_with_secret(self):
        from rich.table import Table

        class Vault(BaseModel):
            code: SecretStr

        v = Vault(code=SecretStr("hunter2"))
        result = self._wiz()._format_display(v)
        assert isinstance(result, Table)
        assert result.row_count == 1

    def test_string_value(self):
        assert self._wiz()._format_display("hello") == "hello"

    def test_float_value(self):
        assert self._wiz()._format_display(3.14) == "3.14"

    def test_bool_value(self):
        assert self._wiz()._format_display(True) == "True"


class TestWizardInstance:
    """Wizard pre-fills prompts from an existing model instance."""

    def test_scalar_fields_use_instance_values_as_defaults(self, mocker, console):
        existing = MageProfile(name="Elara Nighthollow", mana_reserve=5000, has_familiar=False)
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Elara Nighthollow", "5000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=False)

        result = run_wizard(MageProfile, instance=existing, console=console, show_summary=False)

        assert result.name == "Elara Nighthollow"
        assert result.mana_reserve == 5000
        assert result.has_familiar is False

    def test_instance_value_overrides_field_declared_default(self, mocker, console):
        """Instance value wins over the field's declared default when both exist."""
        existing = MageProfile(name="Grimshaw", mana_reserve=1, has_familiar=False)
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Grimshaw", "1"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=False)

        result = run_wizard(MageProfile, instance=existing, console=console, show_summary=False)

        assert result.mana_reserve == 1
        assert result.has_familiar is False

    def test_user_can_override_instance_value(self, mocker, console):
        """The user can still type a different value even when an instance default is set."""
        existing = MageProfile(name="Elara Nighthollow", mana_reserve=5000, has_familiar=False)
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Theron the Ashen", "9999"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        result = run_wizard(MageProfile, instance=existing, console=console, show_summary=False)

        assert result.name == "Theron the Ashen"
        assert result.mana_reserve == 9999
        assert result.has_familiar is True

    def test_nested_model_instance_seeds_sub_wizard(self, mocker, console):
        """Instance values on a nested BaseModel field flow into the sub-wizard."""

        class Realm(BaseModel):
            name: str = Field(description="Realm name")
            region: str = Field(description="Region", default="Embervault")

        class Mage(BaseModel):
            title: str = Field(description="Title")
            homeworld: Realm = Field(description="Home realm")

        existing = Mage(title="Archmage", homeworld=Realm(name="Thornspire", region="Gloomreach"))
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["Archmage", "Thornspire", "Gloomreach"],
        )

        result = run_wizard(Mage, instance=existing, console=console, show_summary=False)

        assert result.title == "Archmage"
        assert result.homeworld.name == "Thornspire"
        assert result.homeworld.region == "Gloomreach"

    def test_no_instance_behaves_as_before(self, mocker, console):
        """When instance is omitted, the wizard uses declared field defaults as usual."""
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Veyra", "10000"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        result = run_wizard(MageProfile, console=console, show_summary=False)

        assert result.name == "Veyra"
        assert result.mana_reserve == 10000
        assert result.has_familiar is True

    def test_returns_new_instance_not_mutated_original(self, mocker, console):
        """The wizard always returns a fresh model; the input instance is untouched."""
        existing = MageProfile(name="Elara Nighthollow", mana_reserve=5000, has_familiar=False)
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Grimshaw", "1"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        result = run_wizard(MageProfile, instance=existing, console=console, show_summary=False)

        assert result is not existing
        assert existing.name == "Elara Nighthollow"
        assert existing.mana_reserve == 5000

    def test_enum_field_uses_instance_value_as_default(self, mocker, console):
        """Instance enum values are passed as defaults to EnumPrompt."""
        existing = BountyHunter(
            name="Grimshaw",
            faction=Faction.ARCANE,
            targets=[],
            homeworld=Realm(name="Thornspire Tower"),
        )
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["Grimshaw", "1", "", "Thornspire Tower", "Outer Rim"],
        )

        result = run_wizard(BountyHunter, instance=existing, console=console, show_summary=False)

        assert result.faction == Faction.ARCANE

    def test_optional_field_with_instance_value(self, mocker, console):
        """Instance values for optional fields are passed as defaults."""
        existing = OptionalFields(nickname="Ashbrand", bounty=750)
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Ashbrand", "750"])

        result = run_wizard(OptionalFields, instance=existing, console=console, show_summary=False)

        assert result.nickname == "Ashbrand"
        assert result.bounty == 750

    def test_optional_field_with_instance_none_value(self, mocker, console):
        """An instance value of None on an optional field still shows None as default."""
        existing = OptionalFields(nickname=None, bounty=None)
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["", ""])

        result = run_wizard(OptionalFields, instance=existing, console=console, show_summary=False)

        assert result.nickname is None
        assert result.bounty is None

    def test_secret_field_uses_instance_value_as_default(self, mocker, console):
        """Instance SecretStr values surface as the masked placeholder default."""
        existing = Warlock(shadow_name="Mordain the Hollow", true_name=SecretStr("ashthorn"), power_level=8500.0)
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["Mordain the Hollow", "*" * len("ashthorn"), "8500.0"],
        )

        result = run_wizard(Warlock, instance=existing, console=console, show_summary=False)

        assert result.true_name.get_secret_value() == "ashthorn"

    def test_list_field_uses_instance_value_as_default(self, mocker, console):
        """Instance list values are serialised as the comma-separated default."""
        existing = BountyHunter(
            name="Grimshaw",
            faction=Faction.SHADOW,
            targets=["Veyra", "Elara"],
            homeworld=Realm(name="Thornspire Tower"),
        )
        mocker.patch(
            "wizdantic.prompts.Prompt.ask",
            side_effect=["Grimshaw", "2", "Veyra, Elara", "Thornspire Tower", "Outer Rim"],
        )

        result = run_wizard(BountyHunter, instance=existing, console=console, show_summary=False)

        assert result.targets == ["Veyra", "Elara"]

    def test_literal_field_uses_instance_value_as_default(self, mocker, console):
        """Instance Literal values are passed as defaults to LiteralPrompt."""
        existing = SpeedSetting(mode="volatile")
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["1"])

        result = run_wizard(SpeedSetting, instance=existing, console=console, show_summary=False)

        assert result.mode == "volatile"

    def test_wizard_class_accepts_instance_parameter(self, mocker, console):
        """Wizard(..., instance=...) wires through correctly without run_wizard."""
        existing = MageProfile(name="Elara Nighthollow", mana_reserve=200, has_familiar=True)
        mocker.patch("wizdantic.prompts.Prompt.ask", side_effect=["Elara Nighthollow", "200"])
        mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)

        wiz = Wizard(MageProfile, instance=existing, console=console, show_summary=False)
        result = wiz.run()

        assert result.name == "Elara Nighthollow"
        assert result.mana_reserve == 200
        assert result.has_familiar is True
