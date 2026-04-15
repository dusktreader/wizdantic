# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


## v0.2.0 - 2026-04-14

### Added

- `instance` parameter to `Wizard` and `run_wizard` to seed prompts from an existing model instance; each
  field's current value becomes the prompt default and a fresh instance is always returned.


## v0.1.2 - 2026-04-13

### Fixed

- Fixed example in README.md.


## v0.1.1 - 2026-04-13

### Fixed

- Made image link in README.md use the published image on GitHub so PyPI renders it.


## v0.1.0 - 2026-04-13

Initial public release. Point it at a Pydantic model and get a fully populated instance back.


### Added

- `Wizard` class and `run_wizard()` convenience function for interactive model population
- Scalar prompts for `str`, `int`, `float` with inline validation and re-prompting
- `bool` fields via `Confirm.ask`; optional booleans (`bool | None`) via text prompt with `y/n/blank`
- `Enum` and `Literal` fields with numbered selection menus
- `SecretStr` fields with masked input and masked summary display
- Optional field support (`T | None`): empty input returns `None`
- Collection prompts for `list`, `tuple`, `set`, and `dict` with CSV and JSON input modes
- Homogeneous tuples (`tuple[T, ...]`) and fixed-length tuples (`tuple[str, int]`)
- Duplicate detection for `set` fields (rejects rather than silently collapsing)
- Nested `BaseModel` fields with recursive sub-wizards
- Nested models inside collections with numbered iteration and "Add another?" looping
- `WizardLore` annotation for field-level customization: `section`, `hint`, and `parser`
- Section grouping to organize fields under labeled headings
- Custom parsers for fields where `TypeAdapter` is too strict or too loose
- Passthrough support for `datetime`, `date`, `UUID`, `Path`, `Decimal`, and Pydantic constrained types
- Rich summary table after collection (disable with `show_summary=False`)
- Custom title and custom `Console` support
- `WizardAborted` exception on `Ctrl+C` / `EOFError`
- `UnsupportedFieldType` raised at construction time for multi-type unions and unhashable set models
- `wizdantic_demo` CLI demo app, installable via `wizdantic[demo]`
