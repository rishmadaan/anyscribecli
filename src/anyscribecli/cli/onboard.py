"""Onboarding wizard — set up ascli for first use."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from anyscribecli.config.paths import APP_HOME, CONFIG_FILE, ENV_FILE, ensure_app_dirs
from anyscribecli.config.settings import Settings, save_config, save_env, load_config
from anyscribecli.core.deps import check_and_install
from anyscribecli.vault.scaffold import create_vault

console = Console()

# Provider metadata for the wizard
PROVIDER_INFO = {
    "openai": {
        "label": "OpenAI Whisper",
        "description": "General purpose, multilingual, segment timestamps",
        "env_var": "OPENAI_API_KEY",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "openrouter": {
        "label": "OpenRouter",
        "description": "Access various models via unified API (uses audio-in-chat)",
        "env_var": "OPENROUTER_API_KEY",
        "key_url": "https://openrouter.ai/keys",
    },
    "elevenlabs": {
        "label": "ElevenLabs Scribe",
        "description": "High accuracy, 99 languages, word-level timestamps",
        "env_var": "ELEVENLABS_API_KEY",
        "key_url": "https://elevenlabs.io/app/settings/api-keys",
    },
    "sargam": {
        "label": "Sarvam AI",
        "description": "Optimized for Indic languages (Hindi, Tamil, Telugu, etc.)",
        "env_var": "SARGAM_API_KEY",
        "key_url": "https://dashboard.sarvam.ai",
    },
    "local": {
        "label": "Local (faster-whisper)",
        "description": "Offline, free, runs on your machine (CPU or GPU)",
        "env_var": None,
        "key_url": None,
    },
}


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
            "Choose your default transcription provider.\n"
            "You can change this later with [bold]ascli config set provider <name>[/bold]\n"
            "or override per-transcription with [bold]ascli transcribe <url> --provider <name>[/bold].",
            title="Provider",
            border_style="blue",
        )
    )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for name, info in PROVIDER_INFO.items():
        default_marker = " (default)" if name == "openai" else ""
        table.add_row(name + default_marker, info["description"])
    console.print(table)

    provider = typer.prompt("\nProvider", default=settings.provider)
    if provider not in PROVIDER_INFO:
        console.print(f"[yellow]Unknown provider '{provider}', using openai.[/yellow]")
        provider = "openai"
    settings.provider = provider

    # Step 4: API key for selected provider
    env_keys: dict[str, str] = {}
    pinfo = PROVIDER_INFO[provider]

    if pinfo["env_var"]:
        console.print(
            Panel(
                f"Enter your [bold]{pinfo['label']}[/bold] API key.\n"
                f"Get one at: [link={pinfo['key_url']}]{pinfo['key_url']}[/link]",
                title="API Key",
                border_style="blue",
            )
        )
        api_key = typer.prompt(f"{pinfo['label']} API key", hide_input=True)
        if api_key:
            env_keys[pinfo["env_var"]] = api_key
    else:
        console.print(
            Panel(
                "Local provider selected — no API key needed.\n"
                "Models will be downloaded automatically on first use.\n\n"
                "Requires [bold]faster-whisper[/bold]: pip install faster-whisper",
                title="Local Provider",
                border_style="blue",
            )
        )

    # Step 5: Ask if user wants to add more provider keys
    if typer.confirm("\nConfigure additional provider API keys?", default=False):
        for name, info in PROVIDER_INFO.items():
            if name == provider or info["env_var"] is None:
                continue
            if typer.confirm(f"  Add {info['label']} API key?", default=False):
                key = typer.prompt(f"  {info['label']} API key", hide_input=True)
                if key:
                    env_keys[info["env_var"]] = key

    # Step 6: Instagram credentials
    console.print(
        Panel(
            "Instagram downloads require a username and password.\n"
            "A dummy/secondary account is recommended — Instagram may\n"
            "temporarily restrict third-party access.\n\n"
            "Skip this if you only plan to use YouTube.",
            title="Instagram (Optional)",
            border_style="blue",
        )
    )
    if typer.confirm("Configure Instagram?", default=False):
        settings.instagram.username = typer.prompt("  Instagram username")
        settings.instagram.password = typer.prompt("  Instagram password", hide_input=True)

    # Step 7: Language
    console.print(
        Panel(
            "[bold]auto[/bold] = auto-detect language from audio\n"
            "Or specify: en, es, fr, hi, ar, zh, ja, ko, etc.",
            title="Default Language",
            border_style="blue",
        )
    )
    settings.language = typer.prompt("Language", default=settings.language)

    # Step 8: Keep media
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
    configured_keys = ", ".join(env_keys.keys()) if env_keys else "none"
    ig_status = f"configured ({settings.instagram.username})" if settings.instagram.username else "not configured"

    console.print(
        Panel(
            f"[green bold]Setup complete![/green bold]\n\n"
            f"  Config:      [cyan]{CONFIG_FILE}[/cyan]\n"
            f"  API Keys:    [cyan]{ENV_FILE}[/cyan]\n"
            f"  Workspace:   [cyan]{workspace}[/cyan]\n\n"
            f"  Provider:    {settings.provider}\n"
            f"  API keys:    {configured_keys}\n"
            f"  Instagram:   {ig_status}\n"
            f"  Language:    {settings.language}\n"
            f"  Keep media:  {settings.keep_media}\n\n"
            "[bold]Next steps:[/bold]\n"
            "  [bold cyan]ascli transcribe <url>[/bold cyan]  — transcribe a video\n"
            "  [bold cyan]ascli providers list[/bold cyan]    — see available providers\n"
            "  [bold cyan]ascli config show[/bold cyan]       — view your settings\n"
            "  Open [cyan]~/.anyscribecli/workspace/[/cyan] in Obsidian to browse transcripts",
            title="Ready",
            border_style="green",
        )
    )
