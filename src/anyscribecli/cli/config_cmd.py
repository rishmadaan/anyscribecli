"""Config and providers CLI commands."""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from anyscribecli.config.paths import CONFIG_FILE
from anyscribecli.config.settings import load_config, save_config, load_env, save_env
from anyscribecli.providers import list_providers, get_provider

# API key names that should be stored in .env, not config.yaml
_API_KEY_MAP = {
    "openai_api_key": "OPENAI_API_KEY",
    "openrouter_api_key": "OPENROUTER_API_KEY",
    "elevenlabs_api_key": "ELEVENLABS_API_KEY",
    "sargam_api_key": "SARGAM_API_KEY",
    "deepgram_api_key": "DEEPGRAM_API_KEY",
}

console = Console()
err_console = Console(stderr=True)

# ── Config subcommands ────────────────────────────────────────

config_app = typer.Typer(
    name="config",
    help="View and change scribe settings.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@config_app.command("show")
def config_show(
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Show[/bold] current configuration."""
    settings = load_config()
    data = settings.to_dict()

    if output_json:
        from anyscribecli.config.paths import get_workspace_dir

        data["_resolved_workspace"] = str(get_workspace_dir())
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        from anyscribecli.config.paths import get_workspace_dir

        console.print(f"[dim]Config file: {CONFIG_FILE}[/dim]\n")
        console.print(yaml.dump(data, default_flow_style=False, sort_keys=False).strip())
        console.print(f"\n[dim]Workspace: {get_workspace_dir()}[/dim]")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(
        ..., help="Setting key (e.g., 'provider', 'language', 'instagram.username')."
    ),
    value: str = typer.Argument(..., help="New value."),
) -> None:
    """[bold]Change[/bold] a configuration setting.

    Use dot-notation for nested keys: `scribe config set instagram.username myuser`
    """
    # Handle API keys — store in .env, not config.yaml
    key_lower = key.lower().replace("-", "_")
    if key_lower in _API_KEY_MAP:
        env_var = _API_KEY_MAP[key_lower]
        save_env({env_var: value})
        console.print(f"[green]Saved[/green] {env_var} to ~/.anyscribecli/.env")
        return

    settings = load_config()
    data = settings.to_dict()

    # Handle dot-notation (e.g., instagram.username)
    keys = key.split(".")
    target = data
    for k in keys[:-1]:
        if k not in target or not isinstance(target[k], dict):
            err_console.print(f"[red]Invalid key: {key}[/red]")
            raise typer.Exit(code=1)
        target = target[k]

    final_key = keys[-1]
    if final_key not in target:
        err_console.print(f"[red]Unknown key: {key}[/red]")
        err_console.print(f"Available: {', '.join(_flat_keys(settings.to_dict()))}")
        raise typer.Exit(code=1)

    # Type coercion
    old_value = target[final_key]
    if isinstance(old_value, bool):
        value_typed = value.lower() in ("true", "1", "yes")
    elif isinstance(old_value, int):
        value_typed = int(value)
    else:
        value_typed = value

    target[final_key] = value_typed

    from anyscribecli.config.settings import Settings

    new_settings = Settings.from_dict(data)
    save_config(new_settings)
    console.print(f"[green]Set[/green] {key} = {value_typed}")


@config_app.command("path")
def config_path() -> None:
    """[bold]Print[/bold] the config file location."""
    console.print(str(CONFIG_FILE))


def _flat_keys(d: dict, prefix: str = "") -> list[str]:
    """Flatten a dict into dot-notation keys."""
    keys = []
    for k, v in d.items():
        full = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            keys.extend(_flat_keys(v, full))
        else:
            keys.append(full)
    return keys


def _flat_items(d: dict, prefix: str = "") -> list[tuple[str, str, str]]:
    """Flatten a dict into (key, type_name, value) tuples."""
    items = []
    for k, v in d.items():
        full = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            items.extend(_flat_items(v, full))
        else:
            items.append((full, type(v).__name__, str(v)))
    return items


@config_app.command("list-keys")
def config_list_keys(
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]List[/bold] all settable configuration keys with types and current values."""
    load_env()
    settings = load_config()
    items = _flat_items(settings.to_dict())

    # Add API key entries
    api_keys = []
    for key_name, env_var in _API_KEY_MAP.items():
        val = os.environ.get(env_var, "")
        masked = f"{val[:4]}...{val[-4:]}" if len(val) > 8 else ("(set)" if val else "(not set)")
        api_keys.append((key_name, "secret", masked))

    all_items = items + api_keys

    if output_json:
        result = [{"key": k, "type": t, "value": v} for k, t, v in all_items]
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        table = Table(title="All Settable Keys")
        table.add_column("Key", style="bold cyan")
        table.add_column("Type", style="dim")
        table.add_column("Current Value")
        for key, type_name, value in all_items:
            table.add_row(key, type_name, value)
        console.print(table)


# ── Providers subcommands ─────────────────────────────────────

providers_app = typer.Typer(
    name="providers",
    help="Manage transcription providers.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@providers_app.command("list")
def providers_list(
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]List[/bold] available transcription providers."""
    settings = load_config()
    active = settings.provider
    providers = list_providers()

    if output_json:
        result = [{"name": p, "active": p == active} for p in providers]
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        table = Table(title="Transcription Providers")
        table.add_column("Provider", style="bold")
        table.add_column("Status")
        table.add_column("Active")

        for p in providers:
            is_active = "[green]Active[/green]" if p == active else ""
            table.add_row(p, "Available", is_active)

        console.print(table)
        console.print("\n[dim]Change with: scribe config set provider <name>[/dim]")


@providers_app.command("test")
def providers_test(
    name: Optional[str] = typer.Argument(None, help="Provider to test (default: active provider)."),
) -> None:
    """[bold]Test[/bold] a provider's API key and connectivity."""
    load_env()
    settings = load_config()
    provider_name = name or settings.provider

    console.print(f"Testing provider: [bold]{provider_name}[/bold]")

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    # Check if API key is set
    key_map = {
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "elevenlabs": "ELEVENLABS_API_KEY",
        "sargam": "SARGAM_API_KEY",
        "deepgram": "DEEPGRAM_API_KEY",
    }
    env_var = key_map.get(provider_name)
    if env_var:
        if os.environ.get(env_var):
            console.print(f"  API key ({env_var}): [green]Set[/green]")
        else:
            console.print(f"  API key ({env_var}): [red]Not set[/red]")
            console.print("  Add it to ~/.anyscribecli/.env")
            raise typer.Exit(code=1)

    if provider_name == "local":
        console.print("  [green]Local provider — no API key needed.[/green]")

    console.print(f"  Provider class: {provider.__class__.__name__}")
    console.print("  [green]Provider loaded successfully.[/green]")
