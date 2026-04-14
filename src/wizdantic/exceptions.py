import buzz


class WizardAborted(buzz.Buzz):
    """
    Raised when the user aborts the wizard with a keyboard interrupt.

    Callers that need to distinguish a clean abort from other errors can
    catch this exception specifically. The message is always a short,
    human-readable explanation suitable for display in a terminal.
    """


class UnsupportedFieldType(buzz.Buzz, TypeError):
    """
    Raised at `Wizard` construction time when a field's type cannot be prompted for.

    This covers multi-type unions (e.g. `str | int`) and non-frozen BaseModel
    items in sets. Inherits from `TypeError` for backward compatibility with
    code that catches `TypeError` from field validation.
    """
