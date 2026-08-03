#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["md2bbcode", "rich", "typer"]
# ///
"""Convert a Markdown README to Nexus Mods-compatible BBCode."""

import re
from pathlib import Path

import typer
from md2bbcode.main import process_readme
from rich.console import Console
from rich.traceback import install


console = Console()
install(console=console)
app = typer.Typer()


def step(message: str) -> None:
    console.print(f"\n[bold blue]>[/bold blue] [bold]{message}[/bold]")


def ok(message: str) -> None:
    console.print(f"[green]OK[/green] {message}", style="green")


def error(message: str) -> None:
    console.print(f"[bold red]ERROR[/bold red] {message}", style="red")


def fix_headings(bbcode: str) -> str:
    bbcode = re.sub(r"\[HEADING=1\](.*?)\[/HEADING\]", r"[size=5]\1[/size]", bbcode)
    bbcode = re.sub(r"\[HEADING=2\](.*?)\[/HEADING\]", r"[size=4]\1[/size]", bbcode)
    return re.sub(r"\[HEADING=3\](.*?)\[/HEADING\]", r"[b]\1[/b]", bbcode)


def fix_image_alt_text(bbcode: str) -> str:
    return re.sub(r'\[img alt=".*?"\](.*?)\[/img\]', r"[img]\1[/img]", bbcode)


def fix_ordered_lists(bbcode: str) -> str:
    preserved: dict[str, str] = {}

    def preserve(match: re.Match[str]) -> str:
        key = f"__LISTBLOCK_{len(preserved)}__"
        preserved[key] = match.group(0)
        return key

    bbcode = re.sub(r"\[list\](.*?)\[/list\]", preserve, bbcode, flags=re.DOTALL)

    def convert_numbered(match: re.Match[str]) -> str:
        lines: list[str] = []
        for count, part in enumerate(re.split(r"\[\*\]", match.group(1))[1:], start=1):
            lines.append(f"{count}. {part.strip()}")
        return "\n".join(lines)

    bbcode = re.sub(r"\[list=1\](.*?)\[/list\]", convert_numbered, bbcode, flags=re.DOTALL)
    for key, value in preserved.items():
        bbcode = bbcode.replace(key, value)
    return bbcode


def close_list_items(bbcode: str) -> str:
    def close_items(match: re.Match[str]) -> str:
        items = [item.strip() for item in re.split(r"\[\*\]", match.group(1), flags=re.IGNORECASE) if item.strip()]
        if not items:
            return match.group(0)
        return "[list]\n" + "\n".join(f"[*]{item}[/*]" for item in items) + "\n[/list]"

    return re.sub(r"\[list\](.*?)\[/list\]", close_items, bbcode, flags=re.DOTALL | re.IGNORECASE)


def color_important_labels(bbcode: str) -> str:
    return re.sub(
        r"(\[size=4\]\[b\])Important:(.*?\[/b\]\[/size\])",
        r"\1[color=#ff0000]Important:[/color]\2",
        bbcode,
        flags=re.IGNORECASE,
    )


def fix_inline_code(bbcode: str) -> str:
    return re.sub(r"\[icode\](.*?)\[/icode\]", r"[i][font=Courier New]\1[/font][/i]", bbcode)


def fix_code_blocks(bbcode: str) -> str:
    return re.sub(r"\[code=.*?\](.*?)\[/code\]", r"[code]\1[/code]", bbcode, flags=re.DOTALL | re.IGNORECASE)


def better_youtube_links(bbcode: str) -> str:
    short_pattern = r"\[url=(https?://(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})[^\]]*)\][^\[]*\[/url\]"
    watch_pattern = r"\[url=(https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})[^\]]*)\][^\[]*\[/url\]"
    bbcode = re.sub(short_pattern, r"[youtube]\2[/youtube]", bbcode)
    return re.sub(watch_pattern, r"[youtube]\2[/youtube]", bbcode)


def fix_tables(bbcode: str) -> str:
    def convert_table(match: re.Match[str]) -> str:
        rows = re.findall(r"\[TR\](.*?)\[/TR\]", match.group(1), flags=re.DOTALL | re.IGNORECASE)
        parsed: list[tuple[bool, list[str]]] = []
        for row in rows:
            cells = []
            header = False
            for cell in re.finditer(r"\[(TH|TD)\](.*?)\[/\1\]", row, flags=re.DOTALL | re.IGNORECASE):
                cells.append(re.sub(r"\s+", " ", cell.group(2).strip()))
                header = header or cell.group(1).upper() == "TH"
            if cells:
                parsed.append((header, cells))
        if not parsed:
            return match.group(0)
        widths = [max(len(cells[index]) if index < len(cells) else 0 for _, cells in parsed) for index in range(max(len(cells) for _, cells in parsed))]
        lines = ["[code]"]
        for header, cells in parsed:
            lines.append("  ".join((cells[index] if index < len(cells) else "").ljust(widths[index]) for index in range(len(widths))).rstrip())
            if header:
                lines.append("  ".join("-" * width for width in widths))
        lines.append("[/code]")
        return "\n".join(lines)

    return re.sub(r"\[TABLE\](.*?)\[/TABLE\]", convert_table, bbcode, flags=re.DOTALL | re.IGNORECASE)


def fix_horizontal_rules(bbcode: str) -> str:
    return re.sub(r"\[hr\]\[/hr\]", "\n\n", bbcode)


def apply_nexusmods_fixes(bbcode: str) -> str:
    for fix in (
        fix_headings,
        fix_image_alt_text,
        fix_ordered_lists,
        close_list_items,
        color_important_labels,
        fix_inline_code,
        fix_code_blocks,
        better_youtube_links,
        fix_tables,
        fix_horizontal_rules,
    ):
        bbcode = fix(bbcode)
    return bbcode


@app.command()
def main(
    readme_path: str = typer.Argument("README.md", help="Input Markdown file."),
    output_path: str = typer.Argument("README.bbcode", help="Output BBCode file."),
) -> None:
    """Convert Markdown to BBCode suitable for Nexus Mods."""
    source = Path(readme_path)
    if not source.exists():
        error(f"Input file '[yellow]{readme_path}[/yellow]' not found.")
        raise typer.Exit(code=1)

    step("Converting README to BBCode")
    bbcode = apply_nexusmods_fixes(process_readme(source.read_text(encoding="utf-8")))
    destination = Path(output_path)
    destination.write_text(bbcode, encoding="utf-8")
    ok(f"Converted [bold yellow]{source}[/bold yellow] to [bold blue]{destination}[/bold blue]")


if __name__ == "__main__":
    app()
