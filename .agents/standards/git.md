# Git Conventions

Branch naming, commit format, and push policy for wizdantic.


## Branch naming

```text
<type>/<short-description>
```

Types:

- **`feat/`**: New feature or capability
- **`fix/`**: Bug fix
- **`refactor/`**: Code restructuring without behavior change
- **`chore/`**: Dependencies, config, tooling
- **`docs/`**: Documentation only
- **`test/`**: Tests only

Use lowercase and hyphens only. Keep descriptions to 3-5 words.

```text
feat/dict-prompt-json-fallback
fix/secret-default-mask-length
refactor/grimoire-to-prompts
chore/update-ruff-config
```

Branch off from `main` unless told otherwise.


## Commit message format

Conventional commits with imperative mood, present tense:

```text
type(scope): brief description

Optional body explaining *why*, not just what.
```

Summary under 72 characters. Scope is optional but recommended when the change is confined to a single
module (e.g. `prompts`, `wizard`, `type_utils`).

Types match branch types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`.

Do **not** use `!` after the type to indicate breaking changes. Describe breaking changes in the commit body.

```text
feat(prompts): add DictPrompt for key:value input

Supports JSON object syntax and k:v,k:v comma notation.
Falls back to kv_string parsing when JSON fails.
```

```text
fix(wizard): preserve original SecretStr default on mask accept

When the user accepts the masked placeholder (e.g. "******"), the
wizard was returning the mask string instead of the original default.
```


## Push policy

**Never push.** Do not run `git push` in any form. Only a human should push changes.


## Branch policy

**Never commit directly to `main`.** If the current branch is `main`, ask the user to create a feature
branch before making any commits.


## Workflow

1. Pull latest `main`
2. Create branch: `git checkout -b feat/my-thing`
3. Make changes in logical increments
4. Run `make qa/full` before committing
5. Commit with a conventional message
6. Ask before pushing
