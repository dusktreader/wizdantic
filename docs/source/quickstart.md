# Quickstart

## Requirements

* Python 3.12 or later


## Installation

Install from PyPI:

```shell-ps1
pip install wizdantic
```

Or with `uv`:

```shell-ps1
uv add wizdantic
```


## Your first wizard

```python title="wizard.py"
from typing import Annotated
from pydantic import BaseModel, Field
from wizdantic import run_wizard


class Spellbook(BaseModel):
    title: Annotated[str, Field(description="Spellbook title")]
    page_count: Annotated[int, Field(description="Number of pages")] = 300
    ink_weight_kg: Annotated[float, Field(description="Weight of enchanted ink in kilograms")] = 0.4
    cursed: Annotated[bool, Field(description="Bound with a curse")] = False


if __name__ == "__main__":
    spellbook = run_wizard(Spellbook, title="Register a Spellbook")
    print(f"Registered: {spellbook.title} ({spellbook.page_count} pages)")
```

Then run it:

```shell-ps1
python wizard.py
```

When you run this, the wizard walks through each field in order:

1. **`title`** is required (no default), so the wizard insists on a value.
2. **`page_count`** shows `300` as the default. Press Enter to accept it or type a
   new number.
3. **`ink_weight_kg`** and **`cursed`** work the same way, with `0.4` and
   `False` as defaults.

After the last field, a summary table is printed and you get back a validated
`Spellbook` instance.


## Validation

Every value is validated inline using Pydantic's `TypeAdapter`. If you type
`"twelve"` for `page_count`, the wizard shows an error and re-prompts
immediately. No partial models, no deferred validation.


## What's next?

- [Features](features.md): all supported field types (enums, literals, secrets, optional fields, lists, nested models, and section grouping).
- [Demo](demo.md): see wizdantic in action before writing any code.
