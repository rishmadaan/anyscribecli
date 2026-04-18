"""Onboarding wizard — set up scribe for first use."""

from __future__ import annotations

import os

import typer
from beaupy import confirm as bconfirm, select as bselect
from rich.console import Console
from rich.panel import Panel

from anyscribecli.config.paths import (
    APP_HOME,
    CLAUDE_HOME,
    CONFIG_FILE,
    DEFAULT_WORKSPACE,
    ENV_FILE,
    ensure_app_dirs,
    get_workspace_dir,
)
from anyscribecli.config.settings import Settings, save_config, save_env, load_config, load_env
from anyscribecli.core.deps import check_and_install
from anyscribecli.core.local_setup import run_setup as run_local_setup
from anyscribecli.providers.local_models import (
    MODEL_SIZES,
    MODEL_SPECS,
    RECOMMENDED_MODEL,
)
from anyscribecli.vault.scaffold import create_vault

console = Console()


def _mask_key(value: str) -> str:
    """Mask an API key for display, showing only last 4 chars."""
    if not value:
        return "[dim]not set[/dim]"
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


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
    "deepgram": {
        "label": "Deepgram Nova",
        "description": "Fast, accurate, native diarization + Hindi Latin support",
        "env_var": "DEEPGRAM_API_KEY",
        "key_url": "https://console.deepgram.com/",
    },
    "local": {
        "label": "Local (faster-whisper)",
        "description": "Offline, free, runs on your machine (CPU or GPU)",
        "env_var": None,
        "key_url": None,
    },
}

# Build display options for the selector
PROVIDER_OPTIONS = [
    f"[cyan]{name}[/cyan] — {info['description']}" for name, info in PROVIDER_INFO.items()
]
PROVIDER_NAMES = list(PROVIDER_INFO.keys())

def _offer_local_setup(settings: Settings, make_primary: bool) -> None:
    """Interactive size picker + run_setup. Shared between 'picked local as
    primary provider' and 'opted into offline as a secondary' paths.

    make_primary=True is informational — the caller already set
    settings.provider. Setup itself never touches provider.
    """
    console.print(
        Panel(
            "Offline transcription runs locally via faster-whisper — no API "
            "key, no internet.\n"
            "Pick a model size. Larger is more accurate but slower and bigger "
            "on disk.\n\n"
            f"[dim]Recommended: [bold]{RECOMMENDED_MODEL}[/bold] — good quality, "
            f"small footprint (~{MODEL_SPECS[RECOMMENDED_MODEL]['download_mb']} MB).[/dim]",
            title="Local Transcription",
            border_style="blue",
        )
    )
    size_options = []
    for size in MODEL_SIZES:
        spec = MODEL_SPECS[size]
        marker = " [dim](recommended)[/dim]" if size == RECOMMENDED_MODEL else ""
        size_options.append(
            f"[cyan]{size}[/cyan] — ~{spec['download_mb']} MB, "
            f"{spec['quality']}{marker}"
        )
    default_idx = MODEL_SIZES.index(RECOMMENDED_MODEL)
    console.print(
        "  Use [bold]↑↓ arrow keys[/bold] to navigate, [bold]Enter[/bold] to select:\n"
    )
    selected = bselect(
        size_options, cursor_index=default_idx, cursor="❯ ", cursor_style="cyan"
    )
    chosen = RECOMMENDED_MODEL if selected is None else MODEL_SIZES[size_options.index(selected)]
    console.print(f"\n  [green]Selected:[/green] {chosen}")

    console.print(
        f"  Installing faster-whisper and downloading [bold]{chosen}[/bold] model…"
    )

    def _progress(event: dict) -> None:
        name = event.get("event", "")
        if name == "installing_package":
            console.print(f"    [dim]• Installing faster-whisper via {event.get('method','?')}…[/dim]")
        elif name == "package_installed":
            console.print("    [green]• faster-whisper installed.[/green]")
        elif name == "downloading_model":
            console.print(f"    [dim]• Downloading {event.get('size','?')} model…[/dim]")
        elif name == "model_downloaded":
            mb = int(event.get("bytes", 0)) // (1024 * 1024)
            console.print(f"    [green]• Model downloaded ({mb} MB).[/green]")

    result = run_local_setup(chosen, on_progress=_progress)

    if result.get("status") == "failed":
        phase = result.get("phase", "?")
        console.print(f"\n  [red]Local setup failed during {phase}.[/red]")
        if phase == "install":
            cmd = result["install"].get("command") or []
            console.print(f"  Command: [dim]{' '.join(cmd)}[/dim]")
            stderr = result["install"].get("stderr") or ""
            if stderr:
                console.print(f"  stderr: [dim]{stderr[:400]}[/dim]")
        else:
            console.print(f"  Error: [dim]{result.get('error', '')}[/dim]")
        if make_primary:
            console.print(
                "  [yellow]Primary provider was set to local but setup didn't "
                "complete — run [bold]scribe local setup --model "
                f"{chosen}[/bold] to retry.[/yellow]"
            )
    else:
        console.print(
            f"\n  [green]Local transcription ready.[/green] Default model: "
            f"[bold]{chosen}[/bold]."
        )


LANGUAGE_OPTIONS = [
    "[cyan]auto[/cyan] — auto-detect language from audio",
    "[cyan]en[/cyan] — English",
    "[cyan]es[/cyan] — Spanish",
    "[cyan]fr[/cyan] — French",
    "[cyan]hi[/cyan] — Hindi",
    "[cyan]ar[/cyan] — Arabic",
    "[cyan]zh[/cyan] — Chinese",
    "[cyan]ja[/cyan] — Japanese",
    "[cyan]ko[/cyan] — Korean",
    "[cyan]other[/cyan] — type a language code",
]
LANGUAGE_CODES = ["auto", "en", "es", "fr", "hi", "ar", "zh", "ja", "ko", "other"]


def onboard(
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-run setup even if already configured."
    ),
    skip_deps: bool = typer.Option(False, "--skip-deps", help="Skip dependency checking."),
) -> None:
    """[bold green]Set up scribe[/bold green] — interactive onboarding wizard.

    Checks system dependencies, prompts for API keys, and initializes the Obsidian vault.
    """
    if CONFIG_FILE.exists() and not force:
        console.print(
            Panel(
                f"scribe is already configured at [cyan]{APP_HOME}[/cyan]\n"
                "Run [bold]scribe onboard --force[/bold] to re-run setup.",
                title="Already Configured",
                border_style="yellow",
            )
        )
        raise typer.Exit()

    console.print(
        Panel(
            "Welcome to [bold]scribe[/bold]!\n\n"
            "This wizard will check your system, set up configuration,\n"
            "and initialize your Obsidian workspace.\n\n"
            "[dim]Use arrow keys to navigate, Enter to select.[/dim]",
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
    reconfiguring = CONFIG_FILE.exists() and force

    # Load existing env so we can show what's already set
    if reconfiguring:
        load_env()
        console.print(
            Panel(
                "Existing configuration detected. Each step will show your\n"
                "current settings — choose whether to keep or change them.",
                title="Reconfiguring",
                border_style="yellow",
            )
        )

    # Step 3: Provider selection (arrow-key selector)
    change_provider = True
    if reconfiguring:
        console.print(f"\n  [bold]Provider:[/bold] [cyan]{settings.provider}[/cyan]")
        change_provider = bconfirm("  Change provider?")

    if change_provider:
        console.print(
            Panel(
                "Choose your default transcription provider.\n"
                "You can change this later with [bold]scribe config set provider <name>[/bold]",
                title="Provider",
                border_style="blue",
            )
        )
        console.print(
            "  Use [bold]↑↓ arrow keys[/bold] to navigate, [bold]Enter[/bold] to select:\n"
        )

        # Find current default index
        default_idx = (
            PROVIDER_NAMES.index(settings.provider) if settings.provider in PROVIDER_NAMES else 0
        )
        selected = bselect(
            PROVIDER_OPTIONS, cursor_index=default_idx, cursor="❯ ", cursor_style="cyan"
        )

        if selected is None:
            provider = "openai"
        else:
            provider = PROVIDER_NAMES[PROVIDER_OPTIONS.index(selected)]
        settings.provider = provider
        console.print(f"\n  [green]Selected:[/green] {provider}\n")

    provider = settings.provider

    # Step 4: API key for selected provider
    env_keys: dict[str, str] = {}
    pinfo = PROVIDER_INFO[provider]

    if pinfo["env_var"]:
        existing_key = os.environ.get(pinfo["env_var"], "")
        change_key = True

        if reconfiguring and existing_key:
            console.print(f"\n  [bold]{pinfo['label']} API key:[/bold] {_mask_key(existing_key)}")
            change_key = bconfirm("  Change API key?")

        if change_key:
            console.print(
                Panel(
                    f"Enter your [bold]{pinfo['label']}[/bold] API key.\n"
                    f"Get one at: [link={pinfo['key_url']}]{pinfo['key_url']}[/link]\n\n"
                    "[dim]Your key is stored locally and never shared.[/dim]",
                    title="API Key",
                    border_style="blue",
                )
            )
            console.print("  Paste your key below (hidden as you type):")
            api_key = typer.prompt(f"  {pinfo['label']} API key", hide_input=True)
            if api_key:
                env_keys[pinfo["env_var"]] = api_key
    else:
        # Primary provider is "local" — run the unified setup inline.
        _offer_local_setup(settings, make_primary=True)

    # Step 4b: Offer offline/local transcription as a secondary option when the
    # primary provider is an API provider. Skip if the user already picked
    # local (setup already ran above). Also skip if faster-whisper is already
    # installed AND a model is cached — they're effectively already set up.
    if provider != "local":
        console.print()
        if bconfirm("  Also enable offline/local transcription?"):
            _offer_local_setup(settings, make_primary=False)

    # Step 5: Additional provider keys
    console.print()
    console.print("  Want to configure API keys for other providers too?")
    if bconfirm("  Add additional provider keys?"):
        for name, info in PROVIDER_INFO.items():
            if name == provider or info["env_var"] is None:
                continue
            existing_val = os.environ.get(info["env_var"], "")
            if existing_val:
                console.print(f"  {info['label']}: {_mask_key(existing_val)}")
                if not bconfirm(f"  Change {info['label']} key?"):
                    continue
            elif not bconfirm(f"  Add {info['label']} key?"):
                continue
            key = typer.prompt(f"  {info['label']} API key", hide_input=True)
            if key:
                env_keys[info["env_var"]] = key

    # Step 6: Instagram credentials
    existing_ig_user = settings.instagram.username
    existing_ig_pass = os.environ.get("INSTAGRAM_PASSWORD", "")
    change_ig = True

    if reconfiguring and (existing_ig_user or existing_ig_pass):
        ig_display = existing_ig_user or "[dim]no username[/dim]"
        pw_display = _mask_key(existing_ig_pass)
        console.print(f"\n  [bold]Instagram:[/bold] {ig_display} / password: {pw_display}")
        change_ig = bconfirm("  Change Instagram credentials?")
    else:
        console.print(
            Panel(
                "Instagram downloads require a username and password.\n"
                "A dummy/secondary account is recommended — Instagram may\n"
                "temporarily restrict third-party access.\n\n"
                "[dim]Skip this if you only plan to use YouTube.[/dim]",
                title="Instagram (Optional)",
                border_style="blue",
            )
        )
        change_ig = bconfirm("  Set up Instagram?")

    if change_ig:
        console.print("  Enter your Instagram credentials:")
        settings.instagram.username = typer.prompt("  Username", default=existing_ig_user or "")
        ig_password = typer.prompt("  Password", hide_input=True)
        if ig_password:
            env_keys["INSTAGRAM_PASSWORD"] = ig_password

    # Step 7: Language (arrow-key selector)
    change_lang = True
    if reconfiguring:
        console.print(f"\n  [bold]Language:[/bold] [cyan]{settings.language}[/cyan]")
        change_lang = bconfirm("  Change language?")

    if change_lang:
        console.print(
            Panel(
                "Choose the default language for transcription.\n"
                "You can override per-video with [bold]--language[/bold] flag.",
                title="Default Language",
                border_style="blue",
            )
        )
        console.print(
            "  Use [bold]↑↓ arrow keys[/bold] to navigate, [bold]Enter[/bold] to select:\n"
        )

        lang_default_idx = (
            LANGUAGE_CODES.index(settings.language) if settings.language in LANGUAGE_CODES else 0
        )
        lang_selected = bselect(
            LANGUAGE_OPTIONS, cursor_index=lang_default_idx, cursor="❯ ", cursor_style="cyan"
        )
        if lang_selected is None:
            settings.language = "auto"
        else:
            lang_code = LANGUAGE_CODES[LANGUAGE_OPTIONS.index(lang_selected)]
            if lang_code == "other":
                settings.language = typer.prompt("  Enter language code (e.g., de, pt, ru)")
            else:
                settings.language = lang_code
        console.print(f"\n  [green]Selected:[/green] {settings.language}\n")

    # Step 8: Keep media
    change_media = True
    if reconfiguring:
        media_display = "yes" if settings.keep_media else "no"
        console.print(f"\n  [bold]Keep media:[/bold] [cyan]{media_display}[/cyan]")
        change_media = bconfirm("  Change keep media setting?")

    if change_media:
        console.print(
            Panel(
                "Keep downloaded audio files after transcription?\n"
                "Files are saved to [cyan]~/.anyscribecli/downloads/audio/[/cyan]\n\n"
                "[dim]You can change this later with: scribe config set keep_media true[/dim]",
                title="Media Storage",
                border_style="blue",
            )
        )
        settings.keep_media = bconfirm("  Keep audio files after transcription?")

    # Step 9: Local file media handling
    change_local = True
    if reconfiguring:
        console.print(
            f"\n  [bold]Local file media:[/bold] [cyan]{settings.local_file_media}[/cyan]"
        )
        change_local = bconfirm("  Change local file media setting?")

    if change_local:
        console.print(
            Panel(
                "When transcribing local files (mp3, mp4, wav, etc.),\n"
                "what should scribe do with the original file?\n\n"
                "[bold]skip[/bold]  — leave the file where it is (default)\n"
                "[bold]copy[/bold]  — copy to media dir for organization\n"
                "[bold]move[/bold]  — move to media dir for organization\n"
                "[bold]ask[/bold]   — ask each time",
                title="Local File Handling",
                border_style="blue",
            )
        )
        console.print(
            "  Use [bold]↑↓ arrow keys[/bold] to navigate, [bold]Enter[/bold] to select:\n"
        )
        local_options = [
            "[cyan]skip[/cyan] — leave the original file where it is",
            "[cyan]copy[/cyan] — copy to ~/.anyscribecli/downloads/audio/ for organization",
            "[cyan]move[/cyan] — move to ~/.anyscribecli/downloads/audio/ for organization",
            "[cyan]ask[/cyan] — ask me each time",
        ]
        local_codes = ["skip", "copy", "move", "ask"]
        local_default_idx = (
            local_codes.index(settings.local_file_media)
            if settings.local_file_media in local_codes
            else 0
        )
        local_selected = bselect(
            local_options, cursor_index=local_default_idx, cursor="❯ ", cursor_style="cyan"
        )
        if local_selected is None:
            settings.local_file_media = "skip"
        else:
            settings.local_file_media = local_codes[local_options.index(local_selected)]
        console.print(f"\n  [green]Selected:[/green] {settings.local_file_media}\n")

    # Step 10: Post-transcription download prompt
    change_download = True
    if reconfiguring:
        console.print(
            f"\n  [bold]Post-transcription download:[/bold] [cyan]{settings.prompt_download}[/cyan]"
        )
        change_download = bconfirm("  Change download prompt setting?")

    if change_download:
        console.print(
            Panel(
                "After each transcription, scribe can ask if you want to\n"
                "download the full video or audio file.\n\n"
                "[bold]never[/bold]  — don't ask (default)\n"
                "[bold]ask[/bold]    — ask every time after transcription\n"
                "[bold]always[/bold] — always download video after transcription",
                title="Post-Transcription Download",
                border_style="blue",
            )
        )
        console.print(
            "  Use [bold]↑↓ arrow keys[/bold] to navigate, [bold]Enter[/bold] to select:\n"
        )
        download_options = [
            "[cyan]never[/cyan] — don't ask, just transcribe",
            "[cyan]ask[/cyan] — ask me each time if I want the video/audio too",
            "[cyan]always[/cyan] — always download the full video after transcription",
        ]
        download_codes = ["never", "ask", "always"]
        dl_default_idx = (
            download_codes.index(settings.prompt_download)
            if settings.prompt_download in download_codes
            else 0
        )
        dl_selected = bselect(
            download_options, cursor_index=dl_default_idx, cursor="❯ ", cursor_style="cyan"
        )
        if dl_selected is None:
            settings.prompt_download = "never"
        else:
            settings.prompt_download = download_codes[download_options.index(dl_selected)]
        console.print(f"\n  [green]Selected:[/green] {settings.prompt_download}\n")

    # Step 11: Workspace location
    change_workspace = True
    current_ws = get_workspace_dir() if CONFIG_FILE.exists() else DEFAULT_WORKSPACE
    if reconfiguring:
        console.print(f"\n  [bold]Workspace:[/bold] [cyan]{current_ws}[/cyan]")
        change_workspace = bconfirm("  Change workspace location?")

    if change_workspace:
        console.print(
            Panel(
                "Where should scribe store your transcripts?\n"
                f"Default: [cyan]{DEFAULT_WORKSPACE}[/cyan]\n\n"
                "This is your Obsidian vault — open it in Obsidian to browse transcripts.\n"
                "[dim]You can change this later with: scribe config set workspace_path /your/path[/dim]",
                title="Workspace Location",
                border_style="blue",
            )
        )
        custom_path = typer.prompt(
            "  Workspace path (Enter for default)", default=str(DEFAULT_WORKSPACE)
        )
        custom_path = custom_path.strip()
        if custom_path == str(DEFAULT_WORKSPACE):
            settings.workspace_path = ""  # empty means default
        else:
            settings.workspace_path = custom_path

    # Save config and env
    save_config(settings)
    if env_keys:
        save_env(env_keys)

    # Auto-migrate legacy workspace if needed
    from anyscribecli.core.migrate import maybe_migrate_workspace

    migrated = maybe_migrate_workspace()
    if migrated:
        console.print(f"  [green]✓[/green] Migrated transcripts to [cyan]{migrated}[/cyan]")

    # Create vault
    workspace = create_vault()

    # Step 12: Claude Code skill (auto-installed — AI-first app)
    skill_status = ""
    if CLAUDE_HOME.exists():
        from anyscribecli.cli.skill_cmd import copy_skill_files

        copy_skill_files(quiet=True)
        skill_status = "installed"
        console.print(
            "\n  [green]✓[/green] Claude Code skill installed to ~/.claude/skills/scribe/"
        )

    # Summary
    configured_keys = ", ".join(env_keys.keys()) if env_keys else "none"
    ig_status = (
        f"configured ({settings.instagram.username})"
        if settings.instagram.username
        else "not configured"
    )

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
            f"  Keep media:  {settings.keep_media}\n"
            f"  Local files: {settings.local_file_media}\n"
            + (f"  Claude Code: {skill_status}\n" if skill_status else "")
            + "\n"
            "[bold]Next steps:[/bold]\n"
            "  [bold cyan]scribe transcribe <url>[/bold cyan]  — transcribe a video\n"
            "  [bold cyan]scribe providers list[/bold cyan]    — see available providers\n"
            "  [bold cyan]scribe config show[/bold cyan]       — view your settings\n"
            f"  Open [cyan]{workspace}[/cyan] in Obsidian to browse transcripts",
            title="Ready",
            border_style="green",
        )
    )
