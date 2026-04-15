# Examples

Example scripts showing how to use wizdantic.

## Available examples

- `basic_example.py` -- A simple `Spellbook` model with scalar and boolean fields.
- `advanced_example.py` -- Exercises most supported types: enums, literals,
  secrets, optional fields, lists, tuples, sets, dicts, nested models, section
  grouping, custom hints, and custom parsers.
- `instance_example.py` -- Runs the wizard over an already-populated model,
  pre-filling every prompt from the existing instance's values.

## Running examples

```bash
uv run python examples/basic_example.py
uv run python examples/advanced_example.py
uv run python examples/instance_example.py
```
