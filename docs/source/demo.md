# Demo

wizdantic ships with an interactive demo that walks through each supported field
type, one spell at a time. It's the fastest way to see what the wizard can do
before writing any code of your own.


## Installation

The demo depends on `typer` and `auto-name-enum`, which aren't pulled in by a
plain `wizdantic` install. Add them with the `demo` extra:

```shell-ps1
uv add wizdantic[demo]
```

To try it without touching your current environment:

```shell-ps1
uvx --from=wizdantic[demo] wizdantic-demo
```


## Running the demo

```shell-ps1
wizdantic-demo
```

The demo opens with a chapter listing and asks whether to open the spellbook.
Each chapter covers a different category of field type:

| Chapter               | What it covers                              |
|-----------------------|---------------------------------------------|
| `scalar-types`        | Strings, integers, floats, and booleans     |
| `choices`             | Enum and Literal field selection            |
| `optional-and-secret` | Optional fields and masked secrets          |
| `collections`         | Lists, tuples, sets, and dicts              |
| `nested-models`       | Nested `BaseModel` and `list[BaseModel]`    |
| `wizard-lore`         | Sections, custom hints, and custom parsers  |

Within each chapter, individual spells show the model definition and a plain-
English description of what's being demonstrated, then drop you straight into
a live wizard. You can skip any spell or quit at any time.

To jump straight to one chapter, pass `--feature`:

```shell-ps1
wizdantic-demo --feature=collections
```

For the full list of options:

```shell-ps1
wizdantic-demo --help
```


## Check out the source

The demo source is worth a look if you want concrete examples of how to structure
models for use with wizdantic.

[Browse it on GitHub](https://github.com/dusktreader/wizdantic/tree/main/src/wizdantic_demo)
