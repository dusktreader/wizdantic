# wizdantic

![wizdantic](images/wizdantic.png)

_Conjure populated Pydantic models from thin air with an interactive terminal wizard._


## Overview

wizdantic walks your users through every field of a Pydantic model, one prompt
at a time. It validates each value on the spot, insists on required fields,
pre-fills defaults, and hands back a fully constructed model instance when the
spell is complete.

Under the hood it uses [Rich](https://github.com/Textualize/rich) for all
terminal I/O: styled prompts, masked secret input, colorful section headings,
and a summary table at the end.


## Why?

CLI tools that need structured configuration often end up with a maze of
`input()` calls, hand-rolled validation, and forgotten edge cases. If you
already have a Pydantic model describing that configuration, wizdantic turns
it into an interactive wizard with a single function call. You define the shape
of the data once, and the wizard handles the rest.


## Quick taste

```python
from typing import Annotated
from pydantic import BaseModel, Field
from wizdantic import run_wizard

class Spellbook(BaseModel):
    title: Annotated[str, Field(description="Spellbook title")]
    page_count: Annotated[int, Field(description="Number of pages")] = 300
    ink_weight_kg: Annotated[float, Field(description="Weight of enchanted ink in kilograms")] = 0.4
    cursed: Annotated[bool, Field(description="Bound with a curse")] = False

spellbook = run_wizard(Spellbook, title="Register a Spellbook")
```

The wizard prompts for each field, validates the input, and returns a `Spellbook`
instance. See the [Quickstart](quickstart.md) for installation and a complete
walkthrough.


!!! tip "See it in action"
    The fastest way to get a feel for wizdantic is to run the demo:

    ```shell-ps1
    uvx --from=wizdantic[demo] wizdantic-demo
    ```

    No install required. See the [Demo](demo.md) page for a full overview of what it covers.
