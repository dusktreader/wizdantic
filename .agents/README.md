# Wizdantic Agent Instructions

Project-level instructions for agents developing the wizdantic codebase. These supplement any
system-wide agent instructions that may be installed on the developer's machine.


## What wizdantic is

Wizdantic is a Python library that collects values for a Pydantic model via an interactive terminal wizard.
It supports scalar types, enums, literals, secrets, collections, nested models, and custom parsers. The public
API is small: `Wizard`, `run_wizard`, `WizardLore`, `WizardAborted`, and `UnsupportedFieldType`.

The repo also contains `wizdantic_demo`, a CLI demo application installed via `wizdantic[demo]`. It is a
separate package that is never imported as a library.


## What to read

Read all files in `standards/` before writing any code, commits, or documentation.
Read `theme.md` before writing any example data, test fixtures, or documentation snippets.

| File                        | Topic                                                |
|-----------------------------|------------------------------------------------------|
| `standards/code-style.md`   | Python conventions, imports, naming, error handling  |
| `standards/testing.md`      | Test structure, coverage, integration and regression |
| `standards/git.md`          | Branch naming and commit format                      |
| `standards/markdown.md`     | Markdown style for `.agents/` and documentation      |
| `theme.md`                  | Example data theme (wizard, not Star Wars)           |


## Task-to-doc lookup

| Task                                  | Read first                                              |
|---------------------------------------|---------------------------------------------------------|
| Writing or editing Python code        | `standards/code-style.md`, `theme.md`                   |
| Writing or editing tests              | `standards/testing.md`, `standards/code-style.md`       |
| Writing docstrings, docs, or prose    | `write-docs` skill, `theme.md`                          |
| Creating a branch or commit           | `standards/git.md`                                      |
| Editing any `.agents/*.md` file       | `standards/markdown.md`                                 |


## Project layout

```text
src/
  wizdantic/           # Library package
    __init__.py         # Public API exports
    prompts.py          # WizardPrompt base + 9 subclasses (Strategy pattern)
    wizard.py           # Wizard orchestrator, display methods, nested model handling
    lore.py             # WizardLore annotation metadata
    type_utils.py       # Type introspection + parsing helpers
    console.py          # WizardConsole (Rich + prompt_toolkit)
    constants.py        # Shared constants (INDENT)
    exceptions.py       # WizardAborted, UnsupportedFieldType
    version.py          # Version detection from metadata / pyproject.toml
  wizdantic_demo/      # Demo CLI (separate package, never imported as library)
tests/
  unit/                # Fast tests, external dependencies mocked
  integration/         # BDD-style tests exercising real package behavior
docs/
  source/              # MkDocs Material documentation
examples/              # Standalone example scripts
```


## Toolchain

| Command              | Purpose                                      |
|----------------------|----------------------------------------------|
| `make qa/full`       | Run all quality checks (test + lint + types) |
| `make qa/test`       | Run all tests (unit + integration)           |
| `make qa/test/unit`  | Run unit tests only                          |
| `make qa/lint`       | Run ruff + typos                             |
| `make qa/types`      | Run ty type checker                          |
| `make qa/format`     | Auto-format with ruff                        |
| `make docs/serve`    | Local docs preview                           |
| `make demo/run`      | Run the demo CLI                             |

Run `make qa/full` before every commit.


## Changelog

The project follows [Keep a Changelog](https://keepachangelog.com/). The changelog lives at `CHANGELOG.md` in
the repo root.

Maintain an `## Unreleased` section at the top of the changelog. Add entries there as work is done. When a
version is ready to publish, rename the `Unreleased` heading to the version number and date, then add a fresh
`## Unreleased` heading above it.

```markdown
## Unreleased

- Added support for frozenset fields

## v0.1.0 -- 2025-06-01

- Initial release
```

Entries are terse, past-tense bullets. One line per change. Personality is welcome in parenthetical asides.
