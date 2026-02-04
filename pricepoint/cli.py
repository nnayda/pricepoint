"""Pricepoint Client."""

import typer

from pricepoint.collectors.police_incidents import collect_cary_data

app = typer.Typer()


@app.command()
def collect_cary():
    """Run Cary police incident collector."""
    collect_cary_data()


@app.command()
def collect_durham():
    """Run Durham collector (example)."""
    print("Collecting Durham...")


"""
register this in toml:
[project.scripts]
pricepoint = "pricepoint.cli:app"

[project]
name = "pricepoint"
version = "0.1.0"
dependencies = [
    "typer",
]
"""

if __name__ == "__main__":
    app()
