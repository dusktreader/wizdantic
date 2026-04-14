"""
Demo infrastructure for wizdantic.

Extracts source code and docstrings from demo functions, presents them in
Rich panels, runs the wizard interactively, and prompts to continue.
"""

import inspect
import textwrap
import types
from dataclasses import dataclass
from importlib import import_module

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule
from rich.syntax import Syntax

_BLANK_LINE = Rule(characters=" ")


def pseudo_clear(console: Console) -> None:
    """
    Scroll previous content off the visible viewport.

    Prints blank lines equal to the terminal height so earlier output
    is pushed off-screen without being erased. The user can still
    scroll up to review it.

    Parameters:
        console: Rich console to print to.
    """
    for _ in range(console.size.height):
        console.print(_BLANK_LINE)


@dataclass
class Decomposed:
    """
    Extracted metadata from a demo function.
    """

    module: str
    name: str
    docstring: str
    source: str


def get_demo_functions(module_name: str) -> list[types.FunctionType]:
    """
    Discover all demo functions in a demo module.

    Functions whose name starts with `demo` are collected and sorted
    alphabetically. The naming convention `demo_N__feature__variant`
    ensures predictable ordering.

    Parameters:
        module_name: The module name under `wizdantic_demo` to import.
    """
    module = import_module(f"wizdantic_demo.{module_name}")
    demo_functions: list[types.FunctionType] = []
    for _, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and obj.__name__.startswith("demo"):
            demo_functions.append(obj)
    return sorted(demo_functions, key=lambda f: f.__name__)


def decompose(func: types.FunctionType) -> Decomposed:
    """
    Extract the docstring and body source code from a demo function.

    Strips the function signature, docstring delimiters, and any
    type-ignore comments from the source so only the meaningful
    body is shown to the user.

    Parameters:
        func: The demo function to decompose.
    """
    source_lines, _ = inspect.getsourcelines(func)
    raw_source = textwrap.dedent("".join(source_lines))

    lines = raw_source.splitlines(keepends=True)

    # Skip the function signature (def line and any continuation lines)
    body_start = 0
    for i, line in enumerate(lines):
        if line.rstrip().endswith(":"):
            body_start = i + 1
            break

    body_lines = lines[body_start:]
    body = textwrap.dedent("".join(body_lines))

    # Strip docstring from body
    stripped = body.strip()
    if stripped.startswith('"""'):
        end = stripped.find('"""', 3)
        if end != -1:
            body = stripped[end + 3 :].strip("\n")

    # Filter noise
    clean_lines = [
        line
        for line in body.splitlines(keepends=True)
        if not line.strip().startswith("# ty:")
        and not line.strip().startswith("# type:")
        and not line.strip().startswith("# pyright:")
    ]
    body = "".join(clean_lines).strip()

    docstring = inspect.getdoc(func) or ""
    module_name = func.__module__.split(".")[-1]

    return Decomposed(
        module=module_name,
        name=func.__name__,
        docstring=docstring,
        source=body,
    )


def run_demo(demo_func: types.FunctionType, console: Console) -> bool:
    """
    Present and execute a single demo function.

    Shows a Rich panel with the explanation and model source code, then
    runs the wizard interactively. After the wizard completes, prompts
    the user to continue.

    Parameters:
        demo_func: The demo function to run.
        console:   Rich console for output.

    Returns `True` to continue to the next demo, `False` to quit.
    """
    decomposed = decompose(demo_func)

    pseudo_clear(console)

    spell_name = decomposed.name.split("__", 2)[-1].replace("_", " ").title()
    subtitle = f"[dim]{decomposed.module}::{decomposed.name}[/dim]"

    source_panel = Syntax(decomposed.source, "python", theme="monokai", line_numbers=False)

    content_parts = []
    if decomposed.docstring:
        content_parts.append(decomposed.docstring)
    content_parts.append("")

    console.print()
    console.print(
        Panel(
            "\n".join(content_parts),
            title=f"[bold cyan]{spell_name}[/bold cyan]",
            subtitle=subtitle,
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()
    console.print(
        Panel(source_panel, title="[bold yellow]Incantation[/bold yellow]", border_style="yellow", padding=(1, 2))
    )
    console.print()

    if not Confirm.ask("[bold]Cast this spell?[/bold]", console=console, default=True):
        return Confirm.ask("[bold]Skip to next spell?[/bold]", console=console, default=True)

    console.print()
    demo_func()
    console.print()

    return Confirm.ask("[bold]Continue to next spell?[/bold]", console=console, default=True)
