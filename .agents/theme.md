# Example Data Theme

Wizdantic uses a wizard/sorcery theme for all example data. This overrides the default Star Wars theme
described in the `write-docs` skill.


## Use wizard-flavored names

Reach for classic wizard and sorcery tropes: spell names, potion ingredients, enchanted artifacts, arcane schools,
familiar animals, wizard councils, tower locations, and so on. Think Dungeons & Dragons, Discworld, or
Wheel of Time rather than any single franchise.

Good examples:

- **Names**: `"Mordain"`, `"Elara Nighthollow"`, `"Theron the Ashen"`, `"Grimshaw"`
- **Places**: `"Thornspire Tower"`, `"The Shimmering Isles"`, `"Embervault"`, `"Gloomreach"`
- **Items**: `"Cloak of Shadows"`, `"Staff of Embers"`, `"Runestone of Warding"`
- **Spells**: `"Arcane Bolt"`, `"Misty Step"`, `"Counterspell"`, `"Eldritch Blast"`
- **Schools**: `"Evocation"`, `"Conjuration"`, `"Necromancy"`, `"Transmutation"`
- **Creatures**: `"owlbear"`, `"wyvern"`, `"imp"`, `"basilisk"`, `"griffon"`


## Franchises to avoid

Do **not** use example data from Tolkien (Lord of the Rings, The Hobbit, Silmarillion) or Harry Potter. Neither
franchise should appear in names, places, spells, or any other example values. Generic fantasy and D&D-style
references are fine.


## Where this applies

- Docstring examples
- Test fixtures and model definitions
- Demo code in `wizdantic_demo/`
- Documentation and README snippets
- Variable names where a thematic name is appropriate (e.g. `spell_name` over `jedi_name`)
