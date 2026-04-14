# Testing Standards

Testing practices for wizdantic. Run `make qa/test` (or `make qa/full` for the complete QA suite) before
every commit.


## Coverage

Line coverage must stay **above 90%**. The CI floor is configured at 85% (`--cov-fail-under=85` in
`pyproject.toml`), but the working target is 90%. If a change drops coverage below 90%, add tests to
bring it back up before merging.

Check coverage after every test run. The coverage report prints missing lines; use those to identify
untested branches.


## Test layout

Mirror the source structure:

```text
src/wizdantic/prompts.py     ->  tests/unit/test_prompts.py
src/wizdantic/wizard.py      ->  tests/unit/test_wizard.py
src/wizdantic/type_utils.py  ->  tests/unit/test_type_utils.py
src/wizdantic/lore.py        ->  tests/unit/test_lore.py
src/wizdantic/console.py     ->  tests/unit/test_console.py
src/wizdantic/version.py     ->  tests/unit/test_version.py
```

Unit tests go in `tests/unit/`. Integration tests go in `tests/integration/`.


## Unit tests

Unit tests are fast, isolated, and mock external dependencies. Use `pytest-mock` (`mocker` fixture) for
patching.

Test names describe behavior, not implementation:

```python
# correct
def test_optional_empty_returns_none(self, mocker, console): ...
def test_invalid_int_retries(self, mocker, console): ...

# wrong
def test_prompt(self): ...
def test_value(self): ...
```

Group related tests into classes. Each class tests one unit (a function, a method, or a prompt subclass):

```python
class TestBoolPrompt:
    def test_non_optional_true(self, mocker, console): ...
    def test_non_optional_false(self, mocker, console): ...
    def test_optional_empty_returns_none(self, mocker, console): ...
```

Use Arrange-Act-Assert structure with blank lines between sections when the test is longer than a few
lines:

```python
def test_custom_parser(self, mocker, console):
    mocker.patch("wizdantic.prompts.Prompt.ask", return_value="hello")
    prompt = ValuePrompt(
        console, "Name", PydanticUndefined, True, False,
        annotation=str, parser=str.upper,
    )

    result = prompt.prompt()

    assert result == "HELLO"
```


## Integration tests

Integration tests use `pytest-bdd` with Gherkin feature files. They exercise the real package with no
mocking of internal modules. Only `Prompt.ask` and `Confirm.ask` are patched to simulate user input.

Feature files live in `tests/integration/features/`. Step implementations live in
`tests/integration/steps/`.


## Regression tests

When fixing a bug, add a test that reproduces the bug **before** writing the fix. The test should fail
without the fix and pass with it. Name the test to describe the bug, not the ticket:

```python
def test_secret_default_preserves_original_value(self, mocker, console):
    """Accepting the masked placeholder returns the original default, not the mask string."""
```


## Mocking patterns

`Prompt.ask` and `Confirm.ask` are class methods on Rich's prompt classes. Patch them at the `wizdantic.prompts`
import path:

```python
mocker.patch("wizdantic.prompts.Prompt.ask", return_value="Mordain")
mocker.patch("wizdantic.prompts.Confirm.ask", return_value=True)
```

Because they are class methods, patching at any import location patches them globally. Tests that mock
`wizdantic.prompts.Prompt.ask` will also affect `Confirm.ask` calls elsewhere. Keep this in mind when
setting `side_effect` sequences.


## Test runner configuration

Configured in `pyproject.toml`:

- `--random-order`: Tests run in random order to catch hidden state dependencies
- `--cov=src/wizdantic`: Coverage measured against the library package only (not `wizdantic_demo`)
- `--cov-fail-under=85`: CI floor (working target is 90%)

Run specific test subsets:

```shell
make qa/test/unit           # unit tests only
make qa/test/integration    # integration tests only
uv run pytest tests/unit/test_prompts.py::TestBoolPrompt -x -q  # single class
```
