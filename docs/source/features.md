# Features

![wizdantic logo](images/wizdantic-logo-2.png){ .float-right }

wizdantic inspects your model's type annotations and picks the right prompt
strategy for each field. Here's everything it supports.


## Scalar types (str, int, float)

Plain scalar fields are prompted with a text input. The raw string is passed
through `pydantic.TypeAdapter` for validation and coercion.

```python
class Spellbook(BaseModel):
    title: Annotated[str, Field(description="Spellbook title")]
    page_count: Annotated[int, Field(description="Number of pages")] = 300
    ink_weight_kg: Annotated[float, Field(description="Weight of enchanted ink in kilograms")] = 0.4
```

If validation fails (for example, typing `"three hundred"` for an `int` field),
the wizard prints the error and re-prompts.


## Booleans

Boolean fields use Rich's `Confirm.ask`, which accepts `y/n` input:

```python
cursed: Annotated[bool, Field(description="Bound with a curse")] = False
```

Optional booleans (`bool | None`) use a text prompt instead, accepting `y`, `n`,
or blank input (which returns `None`). A dim hint like `(y/n, leave blank for
none)` guides the user.


## Enums

Enum fields display a numbered menu. The user can select by typing the index
number or the enum value/name directly:

```python
class School(str, Enum):
    ABJURATION = "abjuration"
    EVOCATION = "evocation"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"
```


## Literals

`Literal` types work the same as enums: a numbered list of allowed values with
selection by index or exact match:

```python
rarity: Annotated[
    Literal["common", "uncommon", "rare", "legendary"],
    Field(description="Spell rarity"),
] = "common"
```


## Secrets

`SecretStr` fields are prompted with masked input (Rich's `password=True`).
If the field has a default, the wizard shows a row of asterisks matching the
secret's length as the placeholder. Accepting the placeholder keeps the original
default value.

```python
binding_word: Annotated[SecretStr | None, Field(description="Word of binding for the seal")] = None
```

Secrets are also masked in the summary table.


## Optional fields

Fields annotated as `Optional[T]` or `T | None` accept empty input, which the
wizard interprets as `None`:

```python
inscription: Annotated[str | None, Field(description="Dedication inscription")] = None
```

!!! warning "Empty input behavior"
    How the wizard handles empty input (pressing Enter with no text) depends on
    the field's type and default:

    - **Required, non-optional** (`str` with no default): the wizard rejects
      empty input and re-prompts with "A value is required."
    - **Has a default** (`str` with `= "Merlin"`): empty input accepts the
      default value. The user sees the default in the prompt and pressing Enter
      keeps it.
    - **Optional** (`str | None`): empty input returns `None`. There is currently
      no way to set an intentional empty string `""` on an optional field. This
      is a known limitation that may be revisited in a future release.


## Lists

`list[T]` fields accept JSON array or comma-separated input. Each item is
validated individually through `TypeAdapter`:

```python
known_spells: Annotated[list[str], Field(description="Spells inscribed in this book")] = []
```

Typing `fireball, frostbolt, blink` produces `["fireball", "frostbolt", "blink"]`.
JSON input like `["fireball", "frostbolt"]` also works.

!!! note "Collection parsing (list, tuple, set)
    Each of these share common behavior in that the data may be provided in "CSV"
    mode where each entry is separated by a comma. It may also be provided in "JSON"
    mode where the data must be provided as a JSON array.

    For CSV mode, note that leading and trailing whitespaces from each entry are
    stripped from each entry. Spaces may be included in the entry.


## Tuples

Both homogeneous and fixed-length tuples are supported.

Homogeneous tuples (`tuple[T, ...]`) accept JSON array or comma-separated input,
just like lists:

```python
ritual_components: Annotated[tuple[str, ...], Field(description="Required ritual components")]
```

Fixed-length tuples (`tuple[str, int]`) also accept JSON array or comma-separated
input, but validate that the element count matches exactly. Too few or too many
values are rejected:

```python
reagent_dose: Annotated[tuple[str, int], Field(description="Reagent name and quantity")]
```

Both `["mandrake root", 3]` and `mandrake root, 3` are accepted. Providing only
one value, or three, produces an error.

Each position is validated against its declared type regardless of input format.


## Sets

`set[T]` fields accept JSON array or comma-separated input. Duplicate values are
rejected with an error rather than silently collapsed:

```python
affinities: Annotated[set[str], Field(description="Elemental affinities")] = set()
```

Typing `"fire, water, earth"` produces `{"fire", "water", "earth"}`. JSON input
like `["fire", "water"]` also works. Entering `"fire, fire"` is an error.


## Dicts

`dict[K, V]` fields accept JSON object input or a `key:value, key:value`
shorthand notation:

```python
component_index: Annotated[dict[str, str], Field(description="Reagent catalog")] = {}
```

Typing `eye of newt:dried, toe of frog:fresh` produces
`{"eye of newt": "dried", "toe of frog": "fresh"}`. JSON input like
`{"eye of newt": "dried"}` also works. The colon-separated notation requires
exactly one colon per pair; values containing colons (like URLs) need the JSON
format.


## Nested models

### Single nested model

When a field's type is another `BaseModel`, the wizard recurses into a
sub-wizard with a magenta heading. The nested wizard collects all fields of the
inner model and returns the constructed instance. Any further nesting (a
`BaseModel` field inside a nested `BaseModel`) recurses again, also with a
magenta heading. All sub-wizard levels use the same color regardless of depth.

```python
class Origin(BaseModel):
    realm: Annotated[str, Field(description="Realm of origin")]
    tower: Annotated[str, Field(description="Tower or academy")]
    city: Annotated[str, Field(description="City")] = "Silvermere"

class Spellbook(BaseModel):
    provenance: Annotated[Origin, Field(description="Where this spellbook was scribed")]
```

The heading for the sub-wizard is taken from the field's `description` if one is
provided, falling back to the field name. The sub-wizard shares the same console
as the parent, so output stays in one stream.

### Nested models in collections

When a field's type is a _collection_ of `BaseModel`, the wizard enters a collection loop
to gether the values. Each iteration prints a numbered heading (`"Ingredients #1"`, `"#2"`,
etc.), runs a full sub-wizard for that item, then asks `"Add another <label>?"`. The loop
continues until the user declines.

In this example, the `ingredients` field is a list of a nested model named `Ingredient`.
Thus, a "sub-wizard" will be run for each entry in the list:

```python
class Ingredient(BaseModel):
    name: Annotated[str, Field(description="Ingredient name")]
    quantity: Annotated[int, Field(description="Quantity required")] = 1
    prepared: Annotated[bool, Field(description="Must be prepared in advance")] = False

class Potion(BaseModel):
    title: Annotated[str, Field(description="Potion name")]
    ingredients: Annotated[list[Ingredient], Field(description="Ingredients")]
```

The collected items are returned as a plain `list[Ingredient]` and the parent
wizard continues with the next field.

The same sub-wizard loop is used for `tuple[BaseModel, ...]`, `set[BaseModel]`, and
`dict[K, BaseModel]` as well. For sets the loop behaves identically to the list
case. For dicts, each iteration first prompts for a key (as a scalar), then runs
the sub-wizard for the value.

Fixed-length tuples with one or more `BaseModel` positions work differently: there
is no loop. The wizard prompts each position in order exactly once, running a
sub-wizard for `BaseModel` positions and a scalar prompt for all others:

```python
class Coordinates(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: Annotated[float, Field(description="X coordinate")]
    y: Annotated[float, Field(description="Y coordinate")]

class Waypoint(BaseModel):
    label: Annotated[str, Field(description="Waypoint label")]
    location: Annotated[tuple[str, Coordinates, int], Field(description="Realm, coordinates, and elevation")]
```

Here the wizard prompts position 1 as a scalar (`str`), runs a sub-wizard for
position 2 (`Coordinates`), then prompts position 3 as a scalar (`int`). No
"Add another?" — the tuple length is fixed by the type.

!!! warning "set[BaseModel] requires a frozen model"
    Pydantic models are not hashable by default. To use a `BaseModel` subclass as
    a set item, mark it frozen:

    ```python
    from pydantic import ConfigDict

    class Reagent(BaseModel):
        model_config = ConfigDict(frozen=True)

        name: Annotated[str, Field(description="Reagent name")]
        grade: Annotated[str, Field(description="Purity grade")] = "standard"
    ```

    wizdantic raises an `UnsupportedFieldType` at construction time if the model is not frozen,
    so you'll catch the mistake before any prompting begins.


## Sections

Group related fields under headings using `WizardLore` in a
`typing.Annotated` annotation:

```python
from typing import Annotated
from wizdantic import WizardLore

class Spellbook(BaseModel):
    scribe_name: Annotated[str, Field(description="Name of the scribe"), WizardLore(section="Scribe")]
    guild_seal: Annotated[int, Field(description="Guild seal number"), WizardLore(section="Scribe")]
    title: Annotated[str, Field(description="Title of the spellbook"), WizardLore(section="Contents")]
```

Fields sharing the same section value are grouped together. Sections are
rendered in the order they first appear. Unsectioned fields go at the end under
an "Other" heading (or with no heading if every field has a section).


## Custom hints

By default, each prompt type includes a format hint after the label: lists show
`(JSON array or comma-separated)`, dicts show
`(JSON object or key:value, key:value)`, and so on. You can replace the default
hint with your own via `WizardLore`:

```python
ritual_components: Annotated[
    list[str],
    Field(description="Required ritual components"),
    WizardLore(hint="space-separated list of reagents"),
]
```

The custom hint appears dim after the label, exactly where the auto-generated
hint would have been.


## Custom parsers

For fields where `TypeAdapter` is too strict or too loose, `WizardLore` accepts
a `parser` callable that handles the raw string and returns the parsed value. If
it raises any exception, the wizard shows the error and retries:

```python
def parse_gold(raw: str) -> int:
    return int(raw.replace(",", "").replace(" gp", "").strip())

class RitualInscription(BaseModel):
    casting_fee: Annotated[
        int,
        Field(description="Casting fee in gold pieces"),
        WizardLore(hint="e.g. 10,000 gp", parser=parse_gold),
    ]
```

After the parser returns its value, the wizard validates it through
`pydantic.TypeAdapter` against the field's full annotation -- including any
type-level constraints like `ge`, `le`, `min_length`, and `max_length` from
`Field(...)`. This means the retry loop catches both bad parser input and
constraint violations:

```python
from pydantic import Field
from typing import Annotated

class RitualInscription(BaseModel):
    casting_fee: Annotated[
        int,
        Field(description="Casting fee in gold pieces", ge=1, le=100_000),
        WizardLore(hint="e.g. 10,000 gp", parser=parse_gold),
    ]
```

If the user types `"200,000 gp"`, the parser succeeds (returns `200000`), but
`TypeAdapter` immediately rejects it because `200000 > 100000`, and the wizard
re-prompts with the constraint error.

!!! warning "Field validators don't fire inline"
    `@field_validator` decorators are model-scoped: they run when the whole model
    is constructed, not during per-field prompting. Only type-level constraints
    (those encoded in `Field(ge=..., le=..., min_length=...,)` etc.) are enforced
    inline with retry. If you need custom per-field validation, put the logic in
    your `parser` function itself.

For optional fields, the blank-check runs before the parser, so empty input still
returns `None`.

Hints and parsers combine freely! Use `hint` to describe the expected format and
`parser` to handle the input.


## Passthrough types

Types like `datetime`, `date`, `time`, `UUID`, `Path`, `Decimal`, and Pydantic
constrained types (`PositiveInt`, `HttpUrl`, `constr(max_length=50)`, etc.) all
work through the scalar prompt. `TypeAdapter` handles coercion from the raw
string, so ISO 8601 dates, UUID strings, and filesystem paths are all accepted.

These types don't get specialized format hints by default. If you want the user
to see a reminder like `(YYYY-MM-DD)`, attach one via `WizardLore(hint=...)`.
Constraint violations (like a negative `PositiveInt`) surface as the raw Pydantic
error message and trigger a re-prompt.


## Summary table

After collecting all values, the wizard prints a Rich table summarizing what
was entered. Secrets are masked. Nested models are rendered as nested tables
inside the parent summary cell.

Disable it by passing `show_summary=False`:

```python
spellbook = run_wizard(Spellbook, show_summary=False)
```


## Custom title

Override the wizard heading with the `title` parameter:

```python
spellbook = run_wizard(Spellbook, title="Register a Spellbook")
```

Without a custom title, the wizard derives one from the model class name.


## Custom console

Pass your own `rich.console.Console` instance for full control over output
destination and terminal settings:

```python
from rich.console import Console

console = Console(width=120)
spellbook = run_wizard(Spellbook, console=console)
```


## The Wizard class

For more control, use the `Wizard` class directly instead of the `run_wizard()`
convenience function:

```python
from wizdantic import Wizard

wiz = Wizard(Spellbook, title="Register a Spellbook", show_summary=True)
spellbook = wiz.run()
```

The class is generic: `Wizard[Spellbook]` preserves the return type through
static analysis.


## Unsupported types

Multi-type unions like `str | int` are not supported. The wizard cannot know
which branch to prompt for, so it raises an `UnsupportedFieldType` at construction time with
a message pointing to the offending field. `Optional[T]` (i.e. `T | None`) is
fine since there's only one concrete branch.

If you need a union-typed field, use a custom parser via `WizardLore` to handle
the ambiguity yourself.
