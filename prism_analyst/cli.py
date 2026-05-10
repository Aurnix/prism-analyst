"""CLI interface for PRISM Analyst."""

from __future__ import annotations

from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """PRISM Analyst — lightweight account intelligence for GTM teams."""
    pass


@cli.command()
@click.argument("company")
@click.option(
    "--mode",
    type=click.Choice(["no-llm", "quick", "full", "gated"]),
    default="quick",
    help="Analysis mode.",
)
def analyze(company: str, mode: str) -> None:
    """Analyze a single company by name, domain, or URL."""
    from .workflows.analyze import analyze_account

    outputs = analyze_account(company, mode=mode)
    click.echo("")
    for label, path in outputs.items():
        click.echo(f"  {label}: {path}")


@cli.command()
@click.argument("csv_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--mode",
    type=click.Choice(["no-llm", "quick", "gated"]),
    default="no-llm",
    help="Analysis mode for batch.",
)
def batch(csv_path: Path, mode: str) -> None:
    """Analyze a CSV of accounts."""
    from .workflows.batch import batch_analyze

    batch_analyze(csv_path, mode=mode)


@cli.command()
@click.argument("account_slug")
def gift(account_slug: str) -> None:
    """Generate a prospect-safe gift document for an analyzed account."""
    from .workflows.gift import generate_gift

    outputs = generate_gift(account_slug)
    if outputs:
        click.echo("")
        for label, path in outputs.items():
            click.echo(f"  {label}: {path}")


@cli.command()
@click.argument("account_slug")
def digest(account_slug: str) -> None:
    """Compare the latest run against the previous run for an account."""
    from .workflows.monitor import run_digest

    result = run_digest(account_slug)
    if result:
        click.echo(f"Digest written to: {result}")
    else:
        click.echo("Not enough runs to compare. Run analysis at least twice.")


@cli.command()
@click.argument("company")
def resolve(company: str) -> None:
    """Resolve a company name or domain into a normalized profile."""
    from .workflows.analyze import resolve_company

    profile = resolve_company(company)
    click.echo(f"Name:   {profile.name}")
    click.echo(f"Slug:   {profile.slug}")
    click.echo(f"Domain: {profile.domain or '(not detected)'}")


if __name__ == "__main__":
    cli()
