[![Latest Version](https://img.shields.io/pypi/v/wizdantic?label=pypi-version&logo=python&style=plastic)](https://pypi.org/project/wizdantic/)
[![Python Versions](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fdusktreader%2Fwizdantic%2Fmain%2Fpyproject.toml&style=plastic&logo=python&label=python-versions)](https://www.python.org/)
[![Build Status](https://github.com/dusktreader/wizdantic/actions/workflows/main.yml/badge.svg)](https://github.com/dusktreader/wizdantic/actions/workflows/main.yml)
[![Documentation Status](https://github.com/dusktreader/wizdantic/actions/workflows/docs.yml/badge.svg)](https://dusktreader.github.io/wizdantic/)

# wizdantic

![wizdantic](https://raw.githubusercontent.com/dusktreader/wizdantic/main/docs/source/images/wizdantic-logo.png)

Conjure populated Pydantic models from thin air with an interactive terminal
wizard.

## Super-quick start

Requires Python 3.12+.

```bash
pip install wizdantic
```

## Usage

Define a Pydantic model. Call `run_wizard`. That's it.

```python
from pydantic import BaseModel, Field
from wizdantic import run_wizard

class Spellbook(BaseModel):
    name: str = Field(description="Spellbook title")
    page_count: int = Field(description="Number of pages", default=300)
    ink_weight_kg: float = Field(description="Weight of enchanted ink in kilograms", default=0.4)
    cursed: bool = Field(description="Bound with a curse", default=False)

book = run_wizard(Spellbook, title="Register a Spellbook")
```

The wizard walks the user through each field, validates input inline, insists on
required values, pre-fills defaults, and returns a fully constructed model
instance.

## Documentation

Full documentation at [dusktreader.github.io/wizdantic](https://dusktreader.github.io/wizdantic/).
