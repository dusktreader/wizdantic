"""
Rich console subclass with prompt_toolkit input for line editing and history.
"""

from typing import Any

from getpass import getpass
from prompt_toolkit import PromptSession
from rich.console import Console


class WizardConsole(Console):
    """
    Rich Console subclass that uses prompt_toolkit for input.

    Replaces the default `input()` call with a prompt_toolkit `PromptSession`,
    which provides arrow-key line editing, input history via up/down, and
    reverse-i-search (Ctrl+R) out of the box. Rich's `Prompt.ask` and
    `Confirm.ask` call `console.input()` internally, so swapping in this
    subclass gives every wizard prompt proper terminal editing for free.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.prompt_session: PromptSession[str] = PromptSession()
        super().__init__(*args, **kwargs)

    def input(
        self,
        prompt: object = "",
        *,
        markup: bool = True,
        emoji: bool = True,
        password: bool = False,
        stream: Any = None,
    ) -> str:
        """
        Prompt for input using prompt_toolkit instead of builtin `input()`.

        Rich renders the prompt text (with markup and emoji) to the terminal,
        then this method hands off to prompt_toolkit for the actual keystroke
        handling. Password prompts fall back to `getpass` since prompt_toolkit
        prompt with `is_password=True` would conflict with Rich's rendering.

        Parameters:
            prompt:   The prompt text (may contain Rich markup).
            markup:   Whether to interpret Rich markup in the prompt.
            emoji:    Whether to interpret emoji codes in the prompt.
            password: Whether to mask input (delegates to `getpass`).
            stream:   Optional input stream override.
        """
        if prompt:
            self.print(prompt, markup=markup, emoji=emoji, end="")
        if password:
            return getpass("", stream=stream)
        if stream:
            return stream.readline()
        return self.prompt_session.prompt("")
