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
from anyscribecli.config.settings import Settings, load_config, load_env
from anyscribecli.core.config_set import API_KEY_MAP, set_value
from anyscribecli.core.quality import QUALITY_TIERS, has_key
from anyscribecli.providers import (
    PROVIDER_KEY_ENV,
    PROVIDER_MODELS,
    get_models,
    get_provider,
    list_providers,
)

console = Console()
err_console = Console(stderr=True)

# ── Config subcommands ────────────────────────────────────────

config_app = typer.Typer(
    name="config",
    rich_markup_mode="rich",
    invoke_without_command=True,
)


def _provider_rows(settings: Settings) -> list[dict]:
    """One row per provider: what it would run, whether it can, how it's reached."""
    tier_of = {prov: word for word, prov in QUALITY_TIERS.items()}
    rows = []
    for name in list_providers():
        models = get_models(name, settings.extra_models)
        pinned = settings.provider_models.get(name)
        rows.append(
            {
                "name": name,
                "default_model": pinned or (models[0] if models else None),
                "models": models,
                "has_key": has_key(name),
                "tier": tier_of.get(name),
                "pinned": bool(pinned),
                "custom_models": settings.extra_models.get(name, []),
            }
        )
    return rows


@config_app.callback(invoke_without_command=True)
def config_main(
    ctx: typer.Context,
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]View and change[/bold] scribe settings. No subcommand shows the defaults dashboard."""
    if ctx.invoked_subcommand is not None:
        return

    # resolve_run pulls httpx in through the provider modules — keep it off the
    # import path of every other `scribe` command.
    from anyscribecli.core.resolve import resolve_run

    load_env()
    settings = load_config()
    try:
        plan = resolve_run(settings)
    except ValueError as e:
        # A hand-edited/downgraded config can hold an unknown provider — the
        # dashboard is where users diagnose that, so it must not traceback.
        if output_json:
            json.dump({"error": str(e), **settings.to_dict()}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            err_console.print(f"[red]Error:[/red] {e}")
            err_console.print("[dim]Fix with: scribe config set provider <name>[/dim]")
        raise typer.Exit(code=1)
    rows = _provider_rows(settings)

    if output_json:
        data = settings.to_dict()
        data["resolved"] = {
            "provider": plan.provider,
            "model": plan.model,
            "via": plan.via,
            "notes": plan.notes,
        }
        data["providers"] = rows
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    model = plan.model or (settings.local_model if plan.provider == "local" else "default")
    console.print(f"Next run: [bold]{plan.provider}[/bold] · {model} [dim]({plan.via})[/dim]")
    for note in plan.notes:
        console.print(f"  [dim]{note}[/dim]")

    table = Table(box=None, pad_edge=False)
    table.add_column("Provider", style="bold")
    table.add_column("Default model")
    table.add_column("Alternatives", style="dim")
    table.add_column("Key")
    table.add_column("Notes", style="dim")

    for row in rows:
        name = row["name"]
        others = [m for m in row["models"] if m != row["default_model"]]
        alts = ", ".join(others) if len(others) <= 2 else f"{len(others)} more"
        if PROVIDER_KEY_ENV[name] is None:
            key = "[dim]—[/dim]"
        else:
            key = "[green]✓[/green]" if row["has_key"] else "[yellow]missing[/yellow]"
        notes = [row["tier"]] if row["tier"] else []
        if row["pinned"]:
            notes.append("pinned")
        if row["custom_models"]:
            notes.append(f"{len(row['custom_models'])} custom")
        if name == "local":
            notes.append(f"local_model: {settings.local_model}")
        table.add_row(
            f"→ {name}" if name == plan.provider else f"  {name}",
            row["default_model"] or "—",
            alts,
            key,
            ", ".join(notes),
        )

    console.print()
    console.print(table)
    console.print()
    missing = [r["name"] for r in rows if not r["has_key"]]
    if missing:
        console.print(
            f"[dim]Missing keys:    {', '.join(missing)}  "
            f"(scribe config set <provider>_api_key <key>)[/dim]"
        )
    console.print(
        "[dim]Change provider: scribe config set provider <name>  "
        "(also sets quality = custom, so it sticks)[/dim]"
    )
    console.print(
        "[dim]Pin a model:     scribe config set provider_models.<provider> <model>[/dim]"
    )
    console.print(
        "[dim]Or pick a tier:  scribe config set quality accuracy|balanced|cost|free|custom[/dim]"
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
        ..., help="Setting key (e.g., 'provider', 'language', 'instagram.browser')."
    ),
    value: str = typer.Argument(..., help="New value."),
) -> None:
    """[bold]Change[/bold] a configuration setting.

    Use dot-notation for nested keys: `scribe config set instagram.browser firefox`
    """
    outcome = set_value(key, value)
    if not outcome.ok:
        err_console.print(f"[red]{outcome.error}[/red]")
        if outcome.choices:
            err_console.print(f"Available: {', '.join(outcome.choices)}")
        raise typer.Exit(code=1)
    console.print(f"[green]{outcome.message}[/green]")


@config_app.command("path")
def config_path() -> None:
    """[bold]Print[/bold] the config file location."""
    console.print(str(CONFIG_FILE))


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
    data = settings.to_dict()
    # Rendered explicitly below so every pinnable provider has a row even when
    # nothing is pinned — an empty dict flattens to nothing.
    data.pop("provider_models")
    data.pop("extra_models")
    items = _flat_items(data)
    for name in list_providers():
        if PROVIDER_MODELS.get(name):
            items.append(
                (
                    f"provider_models.{name}",
                    "str",
                    settings.provider_models.get(name) or "(default)",
                )
            )
    items.append(
        (
            "extra_models.openrouter",
            "list",
            ", ".join(settings.extra_models.get("openrouter") or []) or "(none)",
        )
    )

    # Add API key entries
    api_keys = []
    for key_name, env_var in API_KEY_MAP.items():
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
    rows = _provider_rows(settings)

    if output_json:
        result = [
            {
                "name": r["name"],
                "active": r["name"] == active,
                "model": r["default_model"] or "",
                "models": r["models"],
                "custom_models": r["custom_models"],
            }
            for r in rows
        ]
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        table = Table(title="Transcription Providers")
        table.add_column("Provider", style="bold")
        table.add_column("Model")
        table.add_column("Also available", style="dim")
        table.add_column("Active")

        for r in rows:
            current = r["default_model"] or ""
            others = ", ".join(
                f"{m} (custom)" if m in r["custom_models"] else m
                for m in r["models"]
                if m != current
            )
            is_active = "[green]Active[/green]" if r["name"] == active else ""
            table.add_row(r["name"], current, others, is_active)

        console.print(table)
        console.print("\n[dim]Change with: scribe config set provider <name>[/dim]")
        console.print(
            "[dim]Pin a model: scribe config set provider_models.<provider> <model>  "
            "(or per-run: scribe <url> -p <provider> -m <model>)[/dim]"
        )


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
    env_var = PROVIDER_KEY_ENV.get(provider_name)
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
