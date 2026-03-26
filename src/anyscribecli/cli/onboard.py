"""Onboarding wizard — set up ascli for first use."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from anyscribecli.config.paths import APP_HOME, CONFIG_FILE, ENV_FILE, ensure_app_dirs
from anyscribecli.config.settings import Settings, save_config, save_env, load_config
from anyscribecli.vault.scaffold import create_vault

console = Console()


def onboard(
    force: bool = typer.Option(False, "--force", "-f", help="Re-run setup even if already configured."),
) -> None:
    """[bold green]Set up ascli[/bold green] — interactive onboarding wizard.

    Creates the app directory, prompts for API keys, and initializes the Obsidian vault.
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
            "This wizard will set up your configuration and Obsidian workspace.",
            title="Onboarding",
            border_style="blue",
        )
    )

    # Create directories
    ensure_app_dirs()

    # Load existing settings or defaults
    settings = load_config() if CONFIG_FILE.exists() else Settings()

    # Provider selection
    console.print("\n[bold]Transcription Provider[/bold]")
    console.print("  Available: openai (default)")
    provider = typer.prompt("Provider", default=settings.provider)
    settings.provider = provider

    # API key
    env_keys: dict[str, str] = {}
    if provider == "openai":
        console.print("\n[bold]OpenAI API Key[/bold]")
        console.print("  Get yours at: https://platform.openai.com/api-keys")
        api_key = typer.prompt("OpenAI API key", hide_input=True)
        if api_key:
            env_keys["OPENAI_API_KEY"] = api_key

    # Language
    console.print("\n[bold]Default Language[/bold]")
    console.print("  'auto' = auto-detect, or use language codes like 'en', 'es', 'hi'")
    settings.language = typer.prompt("Language", default=settings.language)

    # Keep media
    console.print("\n[bold]Keep Downloaded Media?[/bold]")
    console.print("  If yes, audio/video files are saved alongside transcripts")
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
            f"[green]Setup complete![/green]\n\n"
            f"  Config:    [cyan]{CONFIG_FILE}[/cyan]\n"
            f"  API Keys:  [cyan]{ENV_FILE}[/cyan]\n"
            f"  Workspace: [cyan]{workspace}[/cyan]\n\n"
            f"  Provider:  {settings.provider}\n"
            f"  Language:  {settings.language}\n"
            f"  Keep media: {settings.keep_media}\n\n"
            "Next steps:\n"
            "  [bold]ascli transcribe <url>[/bold]  — transcribe a video\n"
            "  [bold]ascli config show[/bold]       — view settings\n"
            "  Open the workspace in Obsidian to browse transcripts.",
            title="Ready",
            border_style="green",
        )
    )
