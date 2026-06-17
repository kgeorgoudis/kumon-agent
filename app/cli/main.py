"""
Kumon Agent CLI.

Usage examples
--------------
  kumon --help
  kumon generate multiplication-2-5
  kumon generate multiplication-2-5 --exercises 20 --child "Ελένη"
  kumon submit <instance_id>
  kumon submit <instance_id> --answers "2,4,6,8" --time 12:30
  kumon pending
  kumon pending --child "Ελένη"
  kumon list-skills
  kumon explain method
  kumon explain skill multiplication
  kumon explain progression
  kumon explain worksheet-types
  kumon profile create "Ελένη" --age 10 --grade 4
  kumon profile show
  kumon profile list
  kumon history

Constitutional Principles encoded here:
  IX  — CLI and web call the same service layer (app/services/).
  X   — `kumon explain` makes Kumon documentation available from the CLI.
  VII — Greek text is used for all child/parent-facing output.
  VIII — No OCR or vision model required for the core workflow.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import app.config as cfg
from app.domain.knowledge_base import KumonKnowledgeBase
from app.domain.math_engine import supported_micro_skills
from app.domain.models import ChildProfile, ManualEntryMode, MicroSkillId, WorksheetType
from app.persistence.database import default_db
from app.services.submission_service import (
    AnswerCountMismatchError,
    DraftNotFoundError,
    InvalidAnswerFormatError,
    InvalidDurationFormatError,
    SubmissionAlreadyConfirmedError,
    SubmissionServiceError,
    WorksheetNotFoundError,
    cancel_submission,
    confirm_and_score,
    get_review_summary,
    list_pending_worksheets,
    parse_bulk_answers,
    parse_duration_to_seconds,
    resume_draft,
    set_answers_on_draft,
    start_submission,
    update_single_answer,
)
from app.services.worksheet_generator import generate_worksheet

# ── Typer app ─────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="kumon",
    help=(
        "Kumon-style math practice for children.\n\n"
        "Generates printable worksheets, tracks progress, and suggests the next sheet.\n"
        "Run 'kumon explain method' to learn about the Kumon method."
    ),
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

# ── Sub-command groups ────────────────────────────────────────────────────────

profile_app = typer.Typer(help="Manage child profiles.")
explain_app = typer.Typer(
    help=(
        "In-app documentation about the Kumon method.\n\n"
        "[dim]Because you are not a Kumon expert, use these commands to understand "
        "the method, skills, and progression rules.[/dim]"
    )
)

app.add_typer(profile_app, name="profile")
app.add_typer(explain_app, name="explain")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_child(child_name: str | None, child_id: str | None) -> ChildProfile | None:
    """Try to load a child profile from the DB; create a transient one if not found."""
    if child_id:
        profile = default_db.get_child_profile(child_id)
        if profile:
            return profile
        console.print(f"[yellow]Warning: no profile found for child_id={child_id!r}[/yellow]")
    if child_name:
        # Try to find by name (linear scan — acceptable for a few profiles)
        for p in default_db.list_child_profiles():
            if p.display_name.lower() == child_name.lower():
                return p
        # Create a transient profile (not saved) so the worksheet still generates
        return ChildProfile(
            child_id="transient",
            display_name=child_name,
            age=cfg.DEFAULT_CHILD_AGE,
            grade_level=cfg.DEFAULT_CHILD_GRADE,
        )
    # Fall back to default profile
    default_profile = default_db.get_child_profile(cfg.DEFAULT_CHILD_ID)
    return default_profile


def _skill_slug_to_id(slug: str) -> MicroSkillId:
    """
    Accept both the enum value ('multiplication_2_5') and a CLI-friendly slug
    ('multiplication-2-5').
    """
    normalised = slug.replace("-", "_").lower()
    try:
        return MicroSkillId(normalised)
    except ValueError:
        supported = [m.value.replace("_", "-") for m in supported_micro_skills()]
        console.print(
            f"[red]Unknown skill: {slug!r}[/red]\n"
            f"Supported skills:\n" + "\n".join(f"  {s}" for s in supported)
        )
        raise typer.Exit(code=1)


def _open_in_browser(path: Path) -> None:
    """Open an HTML file in the default browser (cross-platform)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=True)
        elif sys.platform == "win32":
            subprocess.run(["start", str(path)], shell=True, check=True)
    except Exception as exc:
        console.print(f"[yellow]Could not open browser: {exc}[/yellow]")


# ── generate command ──────────────────────────────────────────────────────────


@app.command()
def generate(
    skill: Annotated[
        str,
        typer.Argument(
            help=(
                "Micro-skill to practice. Use 'kumon list-skills' to see all options.\n"
                "Example: multiplication-2-5"
            )
        ),
    ],
    exercises: Annotated[
        int,
        typer.Option("--exercises", "-n", help="Number of exercises (default: 15)."),
    ] = cfg.DEFAULT_EXERCISE_COUNT,
    child: Annotated[
        Optional[str],
        typer.Option("--child", "-c", help="Child's display name (must match a saved profile)."),
    ] = None,
    child_id: Annotated[
        Optional[str],
        typer.Option("--child-id", help="Child profile ID (alternative to --child)."),
    ] = None,
    seed: Annotated[
        Optional[int],
        typer.Option("--seed", help="Random seed for reproducible worksheet."),
    ] = None,
    open_browser: Annotated[
        bool,
        typer.Option("--open/--no-open", help="Open worksheet in browser after generating."),
    ] = True,
    worksheet_type: Annotated[
        str,
        typer.Option("--type", help="Worksheet type: drill, mixed-review, timed-fluency."),
    ] = "drill",
) -> None:
    """
    Generate a printable worksheet and its answer key.

    The worksheet is saved as an HTML file you can open in your browser and
    print.  The answer key is saved separately.

    Examples:

      kumon generate multiplication-2-5
      kumon generate addition-with-carrying --exercises 20
      kumon generate multiplication-6-9 --child "Ελένη" --exercises 15
    """
    micro_skill_id = _skill_slug_to_id(skill)
    ws_type = WorksheetType(worksheet_type.replace("-", "_"))

    child_profile = _resolve_child(child, child_id)

    with console.status("[green]Generating worksheet…[/green]"):
        instance = generate_worksheet(
            micro_skill_id=micro_skill_id,
            child=child_profile,
            count=exercises,
            worksheet_type=ws_type,
            seed=seed,
        )

    # Save to DB (non-blocking — failure doesn't abort the workflow)
    try:
        default_db.save_worksheet_instance(instance)
    except Exception as exc:
        console.print(f"[yellow]Warning: could not save to database: {exc}[/yellow]")

    # ── Output summary ────────────────────────────────────────────────────────
    ws_path = Path(instance.html_path)
    key_path = Path(instance.answer_key_path)

    console.print()
    console.print(
        Panel(
            f"[bold green]✅ Φύλλο εργασίας δημιουργήθηκε![/bold green]\n\n"
            f"[bold]Δεξιότητα:[/bold]  {instance.title_el}\n"
            f"[bold]Ασκήσεις:[/bold]   {len(instance.exercises)}\n"
            f"[bold]ID:[/bold]         {instance.instance_id}\n\n"
            f"[bold]Φύλλο:[/bold]      {ws_path}\n"
            f"[bold]Κλειδί:[/bold]     {key_path}",
            title="Kumon Agent",
            border_style="green",
        )
    )

    meta = KumonKnowledgeBase.get_micro_skill(micro_skill_id)
    if meta:
        console.print(
            f"\n[dim]Δεξιότητα: {meta.name_el} (Επίπεδο {meta.difficulty_level}/10)[/dim]"
        )
        console.print(f"[dim]{meta.description_el}[/dim]\n")

    if open_browser:
        console.print("[dim]Άνοιγμα στον περιηγητή…[/dim]")
        _open_in_browser(ws_path)


# ── list-skills command ───────────────────────────────────────────────────────


@app.command(name="list-skills")
def list_skills(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show descriptions for each skill."),
    ] = False,
) -> None:
    """
    List all available micro-skills and their difficulty levels.

    Use a skill name with 'kumon generate <skill>' to create a worksheet.
    """
    skills = KumonKnowledgeBase.get_all_micro_skills()

    table = Table(title="Διαθέσιμες Δεξιότητες", show_header=True, header_style="bold green")
    table.add_column("Skill ID (use with generate)", style="cyan", no_wrap=True)
    table.add_column("Ελληνικό Όνομα", style="white")
    table.add_column("Κατηγορία", style="dim")
    table.add_column("Επίπεδο", justify="center")

    for ms in sorted(skills, key=lambda s: (s.parent_skill_id.value, s.difficulty_level)):
        slug = ms.micro_skill_id.value.replace("_", "-")
        table.add_row(slug, ms.name_el, ms.parent_skill_id.value.replace("_", " ").title(), str(ms.difficulty_level))
        if verbose:
            table.add_row("", f"[dim italic]{ms.description_el}[/dim italic]", "", "")

    console.print(table)
    console.print("\n[dim]Χρήση: kumon generate <skill-id> --exercises 15[/dim]")


# ── history command ───────────────────────────────────────────────────────────


@app.command()
def history(
    child_name: Annotated[
        Optional[str],
        typer.Option("--child", "-c", help="Filter by child name."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of records to show."),
    ] = 10,
) -> None:
    """Show recent worksheets generated."""
    child_profile = _resolve_child(child_name, None)
    child_id = child_profile.child_id if child_profile else None

    sheets = default_db.get_recent_worksheets(child_id=child_id, limit=limit)

    if not sheets:
        console.print("[yellow]Δεν βρέθηκαν φύλλα εργασίας.[/yellow]")
        return

    table = Table(title="Ιστορικό Φύλλων Εργασίας", show_header=True, header_style="bold blue")
    table.add_column("Ημερομηνία", style="dim")
    table.add_column("Δεξιότητα")
    table.add_column("Ασκήσεις", justify="right")
    table.add_column("ID", style="dim cyan")

    for ws in sheets:
        date_str = ws.created_at.strftime("%Y-%m-%d %H:%M")
        table.add_row(
            date_str,
            ws.title_el,
            str(len(ws.exercises)),
            ws.instance_id[:8] + "…",
        )

    console.print(table)


@app.command()
def pending(
    child_name: Annotated[
        Optional[str],
        typer.Option("--child", "-c", help="Filter by child name."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of records to show."),
    ] = 20,
) -> None:
    """List worksheets that are pending manual submission."""
    child_id: str | None = None
    if child_name:
        profile = _resolve_child(child_name, None)
        child_id = profile.child_id if profile else None

    rows = list_pending_worksheets(child_id=child_id, limit=limit, db=default_db)

    if not rows:
        if child_name:
            console.print(
                f"[yellow]Δεν υπάρχουν εκκρεμή φύλλα για υποβολή για το παιδί '{child_name}'.[/yellow]"
            )
        else:
            console.print("[yellow]Δεν υπάρχουν εκκρεμή φύλλα για υποβολή.[/yellow]")
        return

    table = Table(title="Εκκρεμή Φύλλα για Υποβολή", show_header=True, header_style="bold magenta")
    table.add_column("Ημερομηνία", style="dim")
    table.add_column("Δεξιότητα")
    table.add_column("Ασκήσεις", justify="right")
    table.add_column("Πρόχειρο", justify="center")
    table.add_column("Worksheet ID", style="cyan", no_wrap=True, overflow="ignore")

    for row in rows:
        date_str = row.created_at.strftime("%Y-%m-%d %H:%M")
        draft_label = "Ναι" if row.has_draft_submission else "—"
        table.add_row(
            date_str,
            row.title_el,
            str(row.exercise_count),
            draft_label,
            row.instance_id,
        )

    console.print(table)



def _format_duration(seconds: int) -> str:
    """Format integer seconds as MM:SS string."""
    return f"{seconds // 60}:{seconds % 60:02d}"


def _render_review_table(rows) -> None:
    """Render the answer review table for the parent."""
    table = Table(title="Επισκόπηση Απαντήσεων", show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Άσκηση")
    table.add_column("Απάντηση", justify="right")
    table.add_column("✓", justify="center")
    for row in rows:
        valid_marker = "[green]✓[/green]" if row.is_valid else "[red]✗[/red]"
        display_val = row.raw_value if row.raw_value else "[dim]—[/dim]"
        table.add_row(
            str(row.slot_index + 1),
            row.problem_text,
            display_val,
            valid_marker,
        )
    console.print(table)


@app.command()
def submit(
    instance_id: Annotated[
        str,
        typer.Argument(help="Worksheet instance ID to submit answers for."),
    ],
    answers: Annotated[
        Optional[str],
        typer.Option("--answers", "-a", help="Bulk answers as comma-separated list."),
    ] = None,
    time: Annotated[
        Optional[str],
        typer.Option("--time", "-t", help="Completion duration (SS, MM:SS, or 12m)."),
    ] = None,
    resume: Annotated[
        bool,
        typer.Option("--resume/--no-resume", help="Resume latest draft for this worksheet."),
    ] = False,
    no_confirm: Annotated[
        bool,
        typer.Option("--no-confirm/--confirm", help="Skip confirmation prompt (bulk mode only)."),
    ] = False,
) -> None:
    """
    Submit manually transcribed answers for a completed worksheet and score it.

    Interactive mode (default): prompts for each answer one at a time.
    Bulk mode: provide all answers with --answers "1,2,3,...".

    Examples:

      kumon submit <instance_id>
      kumon submit <instance_id> --answers "2,4,6,8,10" --time 12:34
      kumon submit <instance_id> --resume
    """
    # ── Validate duration early ───────────────────────────────────────────────
    duration_seconds: int | None = None
    if time is not None:
        try:
            duration_seconds = parse_duration_to_seconds(time)
        except InvalidDurationFormatError as exc:
            console.print(f"[red]{exc.code}[/red]: {exc}")
            raise typer.Exit(1)

    # ── Start or resume submission ────────────────────────────────────────────
    try:
        if resume:
            submission = resume_draft(instance_id, db=default_db)
            console.print(f"[cyan]Συνέχεια προσχεδίου {submission.submission_id[:8]}…[/cyan]")
        else:
            entry_mode = ManualEntryMode.BULK if answers else ManualEntryMode.SEQUENTIAL
            submission = start_submission(instance_id, entry_mode=entry_mode, db=default_db)
    except WorksheetNotFoundError as exc:
        console.print(f"[red]{exc.code}[/red]: {exc}")
        raise typer.Exit(1)
    except SubmissionAlreadyConfirmedError as exc:
        console.print(f"[red]{exc.code}[/red]: {exc}")
        raise typer.Exit(1)
    except DraftNotFoundError as exc:
        console.print(f"[red]{exc.code}[/red]: {exc}")
        raise typer.Exit(1)

    # ── Load worksheet for context ────────────────────────────────────────────
    worksheet = default_db.get_worksheet_instance(instance_id)
    if worksheet is None:
        console.print("[red]ERR_WORKSHEET_NOT_FOUND[/red]: Worksheet disappeared unexpectedly.")
        raise typer.Exit(1)

    # ── Collect answers ───────────────────────────────────────────────────────
    if answers:
        # Bulk mode
        try:
            raw_list = parse_bulk_answers(answers, expected_count=len(worksheet.exercises))
        except AnswerCountMismatchError as exc:
            cancel_submission(submission.submission_id, db=default_db)
            console.print(f"[red]{exc.code}[/red]: {exc}")
            raise typer.Exit(1)
        set_answers_on_draft(submission.submission_id, raw_list, db=default_db)
    else:
        # Sequential interactive mode
        console.print(
            f"\n[bold]Φύλλο:[/bold] {worksheet.title_el}  "
            f"[dim]({len(worksheet.exercises)} ασκήσεις)[/dim]\n"
        )
        existing = {r.slot_index: r for r in get_review_summary(submission.submission_id, db=default_db)}
        for idx, exercise in enumerate(worksheet.exercises):
            pre = existing.get(idx)
            prompt_hint = f" [dim](ήδη: {pre.raw_value})[/dim]" if pre and pre.raw_value else ""
            raw = typer.prompt(f"  {idx + 1:>2}. {exercise.problem_text}{prompt_hint}")
            try:
                set_answers_on_draft(submission.submission_id, [raw] if idx == 0 else
                    [get_review_summary(submission.submission_id, db=default_db)[i].raw_value
                     for i in range(idx)] + [raw], db=default_db)
            except Exception:
                # Fallback: upsert just this slot directly
                update_single_answer(submission.submission_id, idx, raw, db=default_db)

    # ── Review table ──────────────────────────────────────────────────────────
    review_rows = get_review_summary(submission.submission_id, db=default_db)
    console.print()
    _render_review_table(review_rows)

    # ── Correction loop (US2) ─────────────────────────────────────────────────
    if not no_confirm:
        while True:
            console.print(
                "\n[bold]Επιβεβαίωση:[/bold] [cyan]y[/cyan]=καταχώρηση  "
                "[cyan]n[/cyan]=διόρθωση  [cyan]q[/cyan]=ακύρωση"
            )
            choice = typer.prompt("  Επιλογή").strip().lower()
            if choice in {"y", "yes", "ναι", "ν"}:
                break
            elif choice in {"q", "quit", "ακύρωση"}:
                cancel_submission(submission.submission_id, db=default_db)
                console.print("[yellow]Υποβολή ακυρώθηκε.[/yellow]")
                raise typer.Exit(1)
            else:
                # Correction — ask which slot
                try:
                    slot_str = typer.prompt("  Αριθμός άσκησης για διόρθωση (1-based)")
                    slot_num = int(slot_str.strip()) - 1
                    new_raw = typer.prompt(f"  Νέα απάντηση για #{slot_num + 1}")
                    update_single_answer(submission.submission_id, slot_num, new_raw, db=default_db)
                    review_rows = get_review_summary(submission.submission_id, db=default_db)
                    _render_review_table(review_rows)
                except (ValueError, InvalidAnswerFormatError) as exc:
                    console.print(f"[red]Σφάλμα:[/red] {exc}")

    # ── Confirm and score ─────────────────────────────────────────────────────
    try:
        outcome = confirm_and_score(
            submission.submission_id,
            duration_seconds=duration_seconds,
            db=default_db,
        )
    except SubmissionServiceError as exc:
        code = getattr(exc, "code", "ERR_SUBMIT_FAILED")
        console.print(f"[red]{code}[/red]: {exc}")
        raise typer.Exit(1)

    # ── Display results ───────────────────────────────────────────────────────
    time_line = (
        f"\n[bold]Χρόνος:[/bold]          {_format_duration(outcome.duration_seconds)}"
        if outcome.duration_seconds is not None
        else ""
    )
    console.print()
    console.print(
        Panel(
            f"[bold green]✅ Η υποβολή αποθηκεύτηκε![/bold green]\n\n"
            f"[bold]Φύλλο ID:[/bold]        {outcome.instance_id[:12]}…\n"
            f"[bold]Υποβολή ID:[/bold]       {outcome.submission_id[:12]}…\n"
            f"[bold]Σωστές:[/bold]           {outcome.correct_count}/{outcome.total_count}\n"
            f"[bold]Ακρίβεια:[/bold]         {outcome.accuracy_pct:.1f}%"
            f"{time_line}",
            title="Αποτέλεσμα",
            border_style="green",
        )
    )


# ── profile sub-commands ──────────────────────────────────────────────────────


@profile_app.command("create")
def profile_create(
    name: Annotated[str, typer.Argument(help="Child's display name.")],
    age: Annotated[int, typer.Option("--age", help="Child's age.")] = cfg.DEFAULT_CHILD_AGE,
    grade: Annotated[int, typer.Option("--grade", help="Grade level (1–12).")] = cfg.DEFAULT_CHILD_GRADE,
    exercises: Annotated[int, typer.Option("--exercises", help="Default worksheet length.")] = 15,
) -> None:
    """Create or update a child profile."""
    profile = ChildProfile(
        child_id=name.lower().replace(" ", "_"),
        display_name=name,
        age=age,
        grade_level=grade,
        preferred_sheet_length=exercises,
    )
    default_db.save_child_profile(profile)
    console.print(f"[green]✅ Προφίλ αποθηκεύτηκε για {name!r} (ID: {profile.child_id})[/green]")


@profile_app.command("list")
def profile_list() -> None:
    """List all saved child profiles."""
    profiles = default_db.list_child_profiles()
    if not profiles:
        console.print("[yellow]Δεν βρέθηκαν προφίλ.[/yellow]  Χρήση: kumon profile create <name>")
        return
    table = Table(title="Προφίλ Παιδιών", header_style="bold blue")
    table.add_column("ID", style="cyan")
    table.add_column("Όνομα")
    table.add_column("Ηλικία", justify="center")
    table.add_column("Τάξη", justify="center")
    table.add_column("Ασκήσεις/Φύλλο", justify="center")
    for p in profiles:
        table.add_row(p.child_id, p.display_name, str(p.age), str(p.grade_level), str(p.preferred_sheet_length))
    console.print(table)


@profile_app.command("show")
def profile_show(
    child_id: Annotated[
        Optional[str],
        typer.Argument(help="Child ID to show.  Defaults to the first profile."),
    ] = None,
) -> None:
    """Show details of a child profile."""
    if child_id:
        profile = default_db.get_child_profile(child_id)
    else:
        profiles = default_db.list_child_profiles()
        profile = profiles[0] if profiles else None

    if not profile:
        console.print("[yellow]Δεν βρέθηκε προφίλ.[/yellow]")
        return

    console.print(
        Panel(
            f"[bold]Όνομα:[/bold]          {profile.display_name}\n"
            f"[bold]ID:[/bold]             {profile.child_id}\n"
            f"[bold]Ηλικία:[/bold]         {profile.age}\n"
            f"[bold]Τάξη:[/bold]           {profile.grade_level}\n"
            f"[bold]Ασκήσεις/Φύλλο:[/bold] {profile.preferred_sheet_length}\n"
            f"[bold]Χρόνομέτρηση:[/bold]   {'Ναι' if profile.timing_enabled else 'Όχι'}",
            title=f"Προφίλ: {profile.display_name}",
            border_style="blue",
        )
    )


# ── explain sub-commands ──────────────────────────────────────────────────────


@explain_app.command("method")
def explain_method(
    lang: Annotated[
        str,
        typer.Option("--lang", help="Language: 'en' or 'el'."),
    ] = "en",
) -> None:
    """
    Explain the Kumon method — what it is, why it works, and how to use this app.

    [dim]Constitutional Principle X: in-app documentation for non-expert operators.[/dim]
    """
    text = KumonKnowledgeBase.get_method_overview(lang=lang)
    console.print(Panel(text, title="The Kumon Method", border_style="green"))


@explain_app.command("skill")
def explain_skill(
    skill: Annotated[
        str,
        typer.Argument(
            help="Skill name: addition, subtraction, multiplication, division, number-sense."
        ),
    ],
    lang: Annotated[str, typer.Option("--lang")] = "el",
) -> None:
    """
    Show all micro-skills within a skill category, with descriptions.

    Examples:
      kumon explain skill multiplication
      kumon explain skill addition --lang en
    """
    from app.domain.models import SkillId

    normalised = skill.replace("-", "_").lower()
    try:
        skill_id = SkillId(normalised)
    except ValueError:
        valid = [s.value.replace("_", "-") for s in SkillId]
        console.print(f"[red]Unknown skill: {skill!r}[/red]\nValid: {', '.join(valid)}")
        raise typer.Exit(1)

    text = KumonKnowledgeBase.get_skill_description(skill_id, lang=lang)
    console.print(Panel(text, title=f"Skill: {skill_id.value.replace('_', ' ').title()}", border_style="blue"))


@explain_app.command("progression")
def explain_progression() -> None:
    """
    Explain the progression rules — when the app advances, stays, or steps back.

    [dim]Constitutional Principle III: every progression decision is deterministic
    and inspectable.[/dim]
    """
    text = KumonKnowledgeBase.get_progression_guide()
    console.print(Panel(text, title="Progression Rules", border_style="yellow"))


@explain_app.command("worksheet-types")
def explain_worksheet_types() -> None:
    """Describe each worksheet type (drill, mixed review, correction, etc.)."""
    text = KumonKnowledgeBase.get_worksheet_type_guide()
    console.print(Panel(text, title="Worksheet Types", border_style="cyan"))


# ── Entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    app()
