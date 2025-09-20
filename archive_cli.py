# archive_cli.py
import os
import json
from pathlib import Path

import typer
from rich import print, box
from rich.table import Table

from tools.text_read import read_text_any
from tools.rclone_io import list_folders, ensure_path, move_local_to_remote
from tools.util import slugify, today

app = typer.Typer(add_completion=False)


def call_llm(system_prompt: str, user_payload: dict) -> dict:
    import os, json, requests
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    prompt = f"""[SYSTEM]
{system_prompt}
Return ONLY strict JSON.

[USER]
{json.dumps(user_payload, ensure_ascii=False)}
"""

    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",            # force valid JSON content
        "options": {"temperature": 0},
        "stream": False              # <-- critical: disable streaming
    }
    r = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    # Ollama returns: {"model": "...", "created_at": "...", "response": "{...json...}", "done": true}
    txt = data.get("response", "").strip()
    return json.loads(txt)


def smart_filename(inferred: dict, orig_name: str, date_str: str) -> str:
    stem, ext = os.path.splitext(orig_name)
    doc_type = inferred.get("type") or "doc"
    vendor_or_subject = inferred.get("vendor") or inferred.get("subject") or ""
    fn = f"{date_str}_{slugify(doc_type)}_{slugify(vendor_or_subject)}_{slugify(stem)}{ext.lower()}"
    fn = fn.replace("__", "_").strip("_")
    return fn


@app.command()
def route(
    path: str,
    auto: bool = typer.Option(False, "--auto", help="Automatically move to a chosen or top folder."),
    chosen: str = typer.Option(None, "--chosen", help="Explicit folder path to use (overrides auto selection)."),
    allow_create: bool = typer.Option(False, "--allow-create", help="Create missing folders if needed."),
    max_text_chars: int = typer.Option(4000, help="Truncate extracted text."),
    json_out: bool = typer.Option(False, "--json", help="Print strict JSON only (for automation).")
):

    p = Path(path).resolve()
    if not p.exists():
        typer.secho(f"File not found: {p}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Extract text
    print(f"[bold]Reading text[/bold] from: {p.name}")
    text = read_text_any(str(p), max_chars=max_text_chars)
    if len(text.strip()) < 30:
        print("[yellow]Warning:[/yellow] very little text extracted (scan? quality low). Proceeding anyway.")

    # List OneDrive folders (cached)
    print("[bold]Listing OneDrive folders[/bold] (cached)…")
    folders = list_folders(use_cache=True)

    # System prompt with scoring rules
    system_prompt = """You are ARCHIVE, a pragmatic filing assistant. Given a document's extracted text and a list of OneDrive folders (relative paths), infer:
- doc type (invoice|contract|memo|other),
- year (int or null),
- up to 8 keywords.
Score folders by:
+2 if path implies type (contains 'invoice', 'contracts', 'memos' etc. as path segments),
+1 if year appears as a path segment,
+2 per keyword overlap (cap 3).
Return strict JSON:
{
 "inferred": { "type": "...", "vendor": "...", "subject": "...", "year": 2025, "keywords": [] },
 "candidates": [{"path": "...", "score": 0, "why": "..."}, {"path": "...", "score": 0, "why": "..."}, {"path": "...", "score": 0, "why": "..."}],
 "chosen_folder": "..." | null,
 "proposed_filename": "YYYY-MM-DD_<type|doc>_<vendor|subject>_<orig>.ext"
}
If auto=false, chosen_folder must be null. Do not invent folders; use only provided list.
If vendor or year are unknown, set them to null.
Return candidates sorted by descending score (best first).
"""

    # Build user payload
    user_payload = {
        "auto": auto,
        "original_filename": p.name,
        "original_path": str(p),
        "extracted_text": text,
        "folders": folders[:500]# cap to keep prompt size reasonable
    }

    # Call LLM
    print("[bold]Asking the LLM for candidates…[/bold]")
    result = call_llm(system_prompt, user_payload)

    # Normalize response
    resp = {
        "inferred": result.get("inferred", {}) or {},
        "candidates": result.get("candidates", []) or [],
        "proposed_filename": result.get("proposed_filename"),
        "chosen_folder": result.get("chosen_folder")
    }

    # ensure scores are ints and sort descending
    for c in resp["candidates"]:
        try:
            c["score"] = int(c.get("score", 0))
        except Exception:
            c["score"] = 0

    resp["candidates"] = sorted(resp["candidates"], key=lambda x: x.get("score", 0), reverse=True)


    # If just suggesting (no move), either print JSON or table
    if not auto and not chosen:
        if json_out:
            print(json.dumps(resp, ensure_ascii=False))
            return

        print("\n[bold]Inferred[/bold]:", json.dumps(resp["inferred"], indent=2, ensure_ascii=False))
        cands = resp["candidates"]
        if cands:
            table = Table(title="Top Folders", show_header=True, header_style="bold", box=box.SIMPLE_HEAVY)
            table.add_column("Rank", style="bold")
            table.add_column("Path")
            table.add_column("Score", justify="right")
            table.add_column("Why")
            for i, c in enumerate(cands, start=1):
                table.add_row(str(i), c.get("path",""), str(c.get("score","")), c.get("why",""))
            print(table)

        # Filename proposal
        date_str = today()
        inferred = resp["inferred"]
        proposed = resp["proposed_filename"] or smart_filename(inferred, p.name, date_str)
        print(f"[bold]Proposed filename:[/bold] {proposed}")
        print("\nNext: run with --auto to move to the top candidate, or pass a folder with --chosen.")
        return

    # Decide destination
    dest_folder = chosen or resp["chosen_folder"]
    if not dest_folder:
        dest_folder = (resp["candidates"][0]["path"] if resp["candidates"] else None)
    if not dest_folder:
        typer.secho("No candidate folder available.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Filename
    date_str = today()
    inferred = resp["inferred"]
    proposed = resp["proposed_filename"] or smart_filename(inferred, p.name, date_str)


    if allow_create:
        print(f"[bold]Ensuring path[/bold]: {dest_folder}")
        ensure_path(dest_folder)

    # Move the file
    print(f"[bold]Moving[/bold] → {dest_folder}/{proposed}")
    final_remote = move_local_to_remote(str(p), dest_folder, proposed)

    resp.update({
        "final_remote_path": final_remote,
        "renamed": proposed,
        "chosen_folder": dest_folder
    })

    if json_out:
        print(json.dumps(resp, ensure_ascii=False))
    else:
        print(f"[green]Done![/green] Remote path: {final_remote}")


if __name__ == "__main__":
    app()
