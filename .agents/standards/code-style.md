# Python Code Style

Python coding standards for all code in `src/`, `tests/`, and `examples/`.

**Core principle:** Consistency within a module matters more than strict rule adherence. When in doubt, match
the surrounding code.


## Docstrings, comments, and tone

These are governed by the `write-docs` skill (`~/.config/opencode/skills/write-docs/SKILL.md`). Load it before
writing any docstrings, documentation, or prose. Key points summarized here for quick reference:

- Google-style docstrings with `Parameters:` blocks (not `Args:`)
- Opening `"""` on its own line
- No type information in docstrings; types belong in the signature
- All parameter descriptions start at the same column (aligned to the longest parameter name)
- Continuation lines align with the first character of the description text
- Comment only when the "why" is not obvious from the code
- No em dashes, no emoji, no sycophantic language


## Type hints

Use **Python 3.12+ syntax** throughout. No `typing.Optional`, `typing.Union`, `typing.Dict`, `typing.List`.

```python
# correct
def process(data: dict[str, Any]) -> list[str]: ...
value: str | None = None

# wrong
from typing import Dict, List, Optional, Union
def process(data: Dict[str, Any]) -> List[str]: ...
value: Optional[str] = None
```

Annotate all public functions and methods. Private helpers should also be annotated when the types are not
obvious from context.


## Imports

Three groups, blank line between each:

```python
# 1. stdlib
import json
from collections.abc import Callable
from typing import Any

# 2. third-party
import pydantic
from rich.console import Console

# 3. local
from wizdantic.constants import INDENT
from wizdantic.type_utils import unwrap_optional
```

- Alphabetical within each group
- `from X import Y` for specific symbols; `import X` for full modules
- No wildcard imports (`from X import *`)
- Let ruff handle import sorting (`make qa/format` runs `ruff check --select I --fix`)


## Naming

| Kind              | Convention            | Example                                     |
|-------------------|-----------------------|---------------------------------------------|
| Classes           | `PascalCase`          | `WizardPrompt`, `BoolPrompt`                |
| Functions/methods | `snake_case`          | `apply_hint`, `_validate_fields`            |
| Variables         | `snake_case`          | `field_info`, `prompt_label`                |
| Constants         | `UPPER_CASE`          | `INDENT`                                    |
| Private           | `_leading_underscore` | `_make_label`, `_format_display`            |
| Modules           | `snake_case`          | `type_utils.py`, `prompts.py`               |

Boolean variables: use `is_`, `has_`, `should_` prefixes (`is_opt`, `is_frozen`, `has_content`).

Acceptable abbreviations: `exc`, `cls`, `msg`, `idx`.


## Error handling

Use [`py-buzz`](https://github.com/dusktreader/py-buzz) exception tools. Custom exceptions derive from
`buzz.Buzz`, which gives them `require_condition`, `handle_errors`, and `enforce_defined` for free.

```python
# Prefer this
UnsupportedFieldType.require_condition(
    not is_unsupported_union(effective),
    "Field has unsupported type",
)

# Over this
if is_unsupported_union(effective):
    raise UnsupportedFieldType("Field has unsupported type")
```

Always chain exceptions with `from`:

```python
try:
    return adapter.validate_python(parsed)
except pydantic.ValidationError as exc:
    msg = exc.errors()[0]["msg"] if exc.errors() else str(exc)
    raise ValueError(msg) from exc
```

Never swallow exceptions silently. Catch specific exception types.


## Line length

120 characters, enforced by ruff. Configured in `pyproject.toml`.


## Module layout

Standard ordering within a module:

1. Module docstring (brief, only if the module's purpose is not obvious from its name)
2. Imports (stdlib, third-party, local)
3. Module-level functions
4. Classes
5. No section-divider comments (`# ---- Section ----`); they get stale

Keep functions focused. If a function exceeds ~50 lines, consider extracting helpers.

No `if __name__ == "__main__":` blocks in library code. Use entry points for CLI scripts.


## Triple-quoted strings

Use `snick.dedent()` for any triple-quoted string that spans multiple lines and needs clean indentation. This
avoids ugly leading whitespace in error messages and display output without breaking code indentation.

```python
# correct
import snick

msg = snick.dedent(
    """
    Field {field_name!r} has an unsupported type.
    Consider using a custom parser to handle this case.
    """
)

# wrong -- breaks indentation
msg = """Field {field_name!r} has an unsupported type.
Consider using a custom parser to handle this case."""

# wrong -- implicit string concatenation is noisy and fragile
msg = (
    "Field {field_name!r} has an unsupported type.\n"
    "Consider using a custom parser to handle this case.\n"
)

# wrong -- "\n".join() obscures the shape of the text
msg = "\n".join([
    f"Field {field_name!r} has an unsupported type.",
    "Consider using a custom parser to handle this case.",
])
```

Prefer `snick.dedent()` over `textwrap.dedent()`. The `snick` package is already a project dependency.


## Formatting

Run `make qa/format` to auto-format. This runs:

- `ruff check --select I --fix` (import sorting)
- `ruff format` (code formatting)

Do not fight the formatter. If ruff reformats something, accept it.
