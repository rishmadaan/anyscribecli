"""Onboarding wizard — set up ascli for first use."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from anyscribecli.config.paths import APP_HOME, CONFIG_FILE, ENV_FILE, ensure_app_dirs
from anyscribecli.config.settings import Settings, save_config, save_env, load_config
from anyscribecli.core.deps import check_and_install
from anyscribecli.vault.scaffold import create_vault

console = Console()


def onboard(
    force: bool = typer.Option(False, "--force", "-f", help="Re-run setup even if already configured."),
    skip_deps: bool = typer.Option(False, "--skip-deps", help="Skip dependency checking."),
) -> None:
    """[bold green]Set up ascli[/bold green] — interactive onboarding wizard.

    Checks system dependencies, prompts for API keys, and initializes the Obsidian vault.
    """
    if CONFIG_FILE.exists() and not force:
        console.print(
            Panel(
                f"ascli is already configured at [cyan]{APP_HOME}[/cyan]\n"
                "Run [bold]ascli onboard --force[/bold] to re-run setup.",
                title="Already Configured",
                border_style="yellow",
            )
        )
        raise typer.Exit()

    console.print(
        Panel(
            "Welcome to [bold]ascli[/bold]!\n\n"
            "This wizard will check your system, set up configuration,\n"
            "and initialize your Obsidian workspace.",
            title="Onboarding",
            border_style="blue",
        )
    )

    # Step 1: Check dependencies
    if not skip_deps:
        deps_ok = check_and_install(interactive=True)
        if not deps_ok:
            raise typer.Exit(code=1)
    else:
        console.print("\n[yellow]Skipping dependency check (--skip-deps).[/yellow]")

    # Step 2: Create directories
    ensure_app_dirs()

    # Load existing settings or defaults
    settings = load_config() if CONFIG_FILE.exists() else Settings()

    # Step 3: Provider selection
    console.print(
        Panel(
            "Choose your transcription provider.\n"
            "You can change this later with [bold]ascli config set provider <name>[/bold].",
            title="Provider",
            border_style="blue",
        )
    )
    console.print("  Available: [bold]openai[/bold] (default)")
    console.print("  Coming soon: openrouter, elevenlabs, sargam, local")
    provider = typer.prompt("Provider", default=settings.provider)
    settings.provider = provider

    # Step 4: API key
    env_keys: dict[str, str] = {}
    if provider == "openai":
        console.print(
            Panel(
                "Enter your OpenAI API key for Whisper transcription.\n"
                "Get one at: [link=https://platform.openai.com/api-keys]platform.openai.com/api-keys[/link]",
                title="API Key",
                border_style="blue",
            )
        )
        api_key = typer.prompt("OpenAI API key", hide_input=True)
        if api_key:
            env_keys["OPENAI_API_KEY"] = api_key

    # Step 5: Language
    console.print(
        Panel(
            "[bold]auto[/bold] = auto-detect language from audio\n"
            "Or specify: en, es, fr, hi, ar, zh, ja, ko, etc.",
            title="Default Language",
            border_style="blue",
        )
    )
    settings.language = typer.prompt("Language", default=settings.language)

    # Step 6: Keep media
    console.print(
        Panel(
            "Keep downloaded audio files alongside transcripts?\n"
            "Files are saved to [cyan]~/.anyscribecli/workspace/media/[/cyan]",
            title="Media Storage",
            border_style="blue",
        )
    )
    settings.keep_media = typer.confirm("Keep media files?", default=settings.keep_media)

    # Save config and env
    save_config(settings)
    if env_keys:
        save_env(env_keys)

    # Create vault
    workspace = create_vault()

    # Summary
    console.print(
        Panel(
            f"[green bold]Setup complete![/green bold]\n\n"
            f"  Config:    [cyan]{CONFIG_FILE}[/cyan]\n"
            f"  API Keys:  [cyan]{ENV_FILE}[/cyan]\n"
            f"  Workspace: [cyan]{workspace}[/cyan]\n\n"
            f"  Provider:  {settings.provider}\n"
            f"  Language:  {settings.language}\n"
            f"  Keep media: {settings.keep_media}\n\n"
            "[bold]Next steps:[/bold]\n"
            "  [bold cyan]ascli transcribe <url>[/bold cyan]  — transcribe a video\n"
            "  Open [cyan]~/.anyscribecli/workspace/[/cyan] in Obsidian to browse transcripts",
            title="Ready",
            border_style="green",
        )
    )
