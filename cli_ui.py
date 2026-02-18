"""
CLI UI module: Gemini-style terminal aesthetics using Rich.

Provides a centralized console, themed output helpers, progress bars,
and a styled header banner matching the Gemini CLI look and feel.
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.rule import Rule
from rich import box

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
_STYLE_ACCENT = "bold cyan"
_STYLE_DIM = "dim white"

# ---------------------------------------------------------------------------
# Gemini CLI-inspired theme
# Dark background, cyan/teal info, clean whites, gradient-style accents
# ---------------------------------------------------------------------------
GEMINI_THEME = Theme({
    "info":      "bold cyan",
    "warning":   "bold yellow",
    "error":     "bold red",
    "success":   "bold green",
    "highlight": "bold magenta",
    "dim_text":  "dim white",
    "step":      "bold blue",
    "banner":    "bold",
})

console = Console(theme=GEMINI_THEME, highlight=False)

# ---------------------------------------------------------------------------
# ASCII art banner — Gemini CLI style (pixel/block letters)
# Uses a blue → pink gradient via Rich markup
# ---------------------------------------------------------------------------
_BANNER_LINES = [
    # Row 1: I  N  T  E  L  L  I
    " ██╗███╗  ██╗████████╗███████╗██╗     ██╗     ██╗",
    " ██║████╗ ██║╚══██╔══╝██╔════╝██║     ██║     ██║",
    " ██║██╔██╗██║   ██║   █████╗  ██║     ██║     ██║",
    " ██║██║╚████║   ██║   ██╔══╝  ██║     ██║     ██║",
    " ██║██║ ╚███║   ██║   ███████╗███████╗███████╗██║",
    " ╚═╝╚═╝  ╚══╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝",
    # Spacer
    "",
    # Row 2: B  E  N  C  H  M  A  R  K
    " ██████╗ ███████╗███╗  ██╗ ██████╗██╗  ██╗███╗   ███╗ █████╗ ██████╗ ██╗  ██╗",
    " ██╔══██╗██╔════╝████╗ ██║██╔════╝██║  ██║████╗ ████║██╔══██╗██╔══██╗██║ ██╔╝",
    " ██████╔╝█████╗  ██╔██╗██║██║     ███████║██╔████╔██║███████║██████╔╝█████╔╝ ",
    " ██╔══██╗██╔══╝  ██║╚████║██║     ██╔══██║██║╚██╔╝██║██╔══██║██╔══██╗██╔═██╗ ",
    " ██████╔╝███████╗██║ ╚███║╚██████╗██║  ██║██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██╗",
    " ╚═════╝ ╚══════╝╚═╝  ╚══╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝",
]

# Gradient colors from blue → purple → pink (matching Gemini CLI)
# Covers all 12 non-empty banner lines (6 for INTELLI + 6 for BENCHMARK)
_GRADIENT_COLORS = [
    "#5B8DEF",  # blue         (INTELLI row 1)
    "#6A7EEF",  # blue-indigo  (INTELLI row 2)
    "#7B6FEE",  # indigo       (INTELLI row 3)
    "#8F60EC",  # indigo-violet(INTELLI row 4)
    "#A452E0",  # violet       (INTELLI row 5)
    "#BA47D4",  # violet-pink  (INTELLI row 6)
    "#C944C8",  # magenta      (BENCHMARK row 1)
    "#D441BC",  # magenta-pink (BENCHMARK row 2)
    "#DF3FAF",  # pink-magenta (BENCHMARK row 3)
    "#E83EA0",  # hot pink     (BENCHMARK row 4)
    "#F04090",  # pink         (BENCHMARK row 5)
    "#F06080",  # light pink   (BENCHMARK row 6)
]


def _gradient_banner() -> Text:
    """Build the ASCII banner with a blue-to-pink gradient per line, skipping spacers."""
    text = Text()
    color_idx = 0
    for line in _BANNER_LINES:
        if line == "":
            text.append("\n")
        else:
            color = _GRADIENT_COLORS[min(color_idx, len(_GRADIENT_COLORS) - 1)]
            text.append(line + "\n", style=f"bold {color}")
            color_idx += 1
    return text


def print_banner():
    """Print the full Gemini-style INTELLI-BENCHMARK banner."""
    console.print()
    console.print(_gradient_banner(), justify="left")
    console.print()


def print_header(title: str, subtitle: Optional[str] = None):
    """Print a styled info panel (like the Gemini CLI notification box)."""
    content = Text()
    content.append(title, style=_STYLE_ACCENT)
    if subtitle:
        content.append(f"\n{subtitle}", style=_STYLE_DIM)

    panel = Panel(
        content,
        border_style="cyan",
        padding=(0, 2),
        box=box.ROUNDED,
    )
    console.print(panel)
    console.print()


def print_rule(title: str = ""):
    """Print a horizontal rule with optional title."""
    console.print(Rule(title, style="dim cyan"))


def print_success(message: str):
    console.print(f"[success]✔[/success] {message}")


def print_error(message: str):
    console.print(f"[error]✖[/error] {message}")


def print_warning(message: str):
    console.print(f"[warning]⚠[/warning]  {message}")


def print_info(message: str):
    console.print(f"[info]ℹ[/info]  {message}")


def print_step(message: str):
    console.print(f"[step]→[/step] {message}")


def create_progress() -> Progress:
    """Return a Rich Progress bar styled for Gemini CLI aesthetics."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[progress.description]{task.description}", style="white"),
        BarColumn(bar_width=40, style="blue", complete_style="cyan", finished_style="green"),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )


def create_download_progress() -> Progress:
    """Return a Rich Progress bar for file download/sync operations."""
    return Progress(
        SpinnerColumn(spinner_name="dots2", style="cyan"),
        TextColumn("[progress.description]{task.description}", style="white"),
        BarColumn(bar_width=40, style="blue", complete_style="cyan", finished_style="green"),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )


def print_summary_table(
    duration_sec: float,
    success_count: int,
    fail_count: int,
    concurrency: int,
    mode: str,
    report_path: str,
):
    """Print a styled summary table of the benchmark run."""
    total = success_count + fail_count
    success_rate = (success_count / total * 100) if total > 0 else 0.0

    table = Table(
        title=f"[{_STYLE_ACCENT}]Benchmark Summary[/{_STYLE_ACCENT}]",
        show_header=True,
        header_style=_STYLE_ACCENT,
        border_style="dim cyan",
        box=box.ROUNDED,
        padding=(0, 2),
        min_width=50,
    )
    table.add_column("Metric", style=_STYLE_DIM, no_wrap=True)
    table.add_column("Value", style="bold white", no_wrap=True)

    table.add_row("Duration",     f"{duration_sec:.2f}s")
    table.add_row("Total Tasks",  str(total))
    table.add_row("Successes",    f"[green]{success_count}[/green]")
    table.add_row("Failures",     f"[red]{fail_count}[/red]")
    table.add_row("Success Rate", f"{success_rate:.1f}%")
    table.add_row("Concurrency",  str(concurrency))
    table.add_row("Mode",         mode)
    table.add_row("Report",       report_path)

    console.print()
    console.print(table)
    console.print()
