Feature: wizard interactive model population

  Scenario: collect a simple model with string and integer fields
    Given a model with fields "name" (str) and "power_level" (int, default 9000)
    When the wizard runs with inputs "Elara Nighthollow" and "15000"
    Then the result field "name" is "Elara Nighthollow"
    And the result field "power_level" is 15000

  Scenario: optional fields accept empty input as None
    Given a model with an optional "callsign" field
    When the wizard runs with empty input
    Then the result field "callsign" is None

  Scenario: enum fields accept selection by index
    Given a model with an enum "faction" field
    When the wizard runs with input "1"
    Then the result field "faction" is "arcane"

  Scenario: list fields accept comma-separated values
    Given a model with a list "allies" field
    When the wizard runs with input "Mordain, Elara, Grimshaw"
    Then the result field "allies" is "Mordain, Elara, Grimshaw"

  Scenario: summary table is shown by default
    Given a model with fields "name" (str) and "power_level" (int, default 9000)
    When the wizard runs with inputs "Theron" and "25000" and summary enabled
    Then the output contains "Summary"
    And the output contains "Theron"

  Scenario: nested models prompt recursively
    Given a model with a nested "homeworld" model
    When the wizard runs with inputs "Grimshaw" and "Outer Reach"
    Then the result field "homeworld.name" is "Grimshaw"
    And the result field "homeworld.system" is "Outer Reach"

  Scenario: validation errors trigger re-prompts
    Given a model with fields "name" (str) and "power_level" (int, default 9000)
    When the wizard runs with inputs "Mordain", "not_a_number", and "8000"
    Then the result field "power_level" is 8000
    And the output contains "Invalid"
