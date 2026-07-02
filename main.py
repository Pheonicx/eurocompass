from statistics import mean

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

from config.banks import BANKS
from utils.csv_handler import save_rate
from utils.exporter import export_csv, export_json
from utils.history_sync import sync_history

load_dotenv()

console = Console()


def main():
    console.print(
        Panel.fit(
            "[bold cyan]GFIS[/bold cyan]\nGermany Finance Intelligence System",
            border_style="cyan",
        )
    )

    table = Table(show_header=True, header_style="bold green")

    table.add_column("Bank", style="cyan", justify="center")
    table.add_column("Currency", justify="center")
    table.add_column("Buy", justify="right")
    table.add_column("Sell", justify="right")
    table.add_column("Status", justify="center")

    results = []

    for collector in BANKS:

        try:
            rate = collector.get_rate()

            if rate:

                save_rate(rate)

                results.append(rate)

                table.add_row(
                    rate["bank"],
                    rate["currency"],
                    f'{rate["buy"]:.4f}',
                    f'{rate["sell"]:.4f}',
                    "[green]OK[/green]",
                )

            else:

                table.add_row(
                    collector.__name__.split(".")[-1].upper(),
                    "-",
                    "-",
                    "-",
                    "[red]FAILED[/red]",
                )

        except Exception as e:

            table.add_row(
                collector.__name__.split(".")[-1].upper(),
                "-",
                "-",
                "-",
                "[red]ERROR[/red]",
            )

            console.print(f"[red]{e}[/red]")

    console.print(table)

    if not results:
        console.print("\n[bold red]No bank data collected.[/bold red]")
        return

    best_buy = min(results, key=lambda x: x["buy"])
    highest_buy = max(results, key=lambda x: x["buy"])

    best_sell = min(results, key=lambda x: x["sell"])
    highest_sell = max(results, key=lambda x: x["sell"])

    avg_buy = mean(r["buy"] for r in results)
    avg_sell = mean(r["sell"] for r in results)

    summary = {
    "banks_processed": len(results),
    "lowest_buy": {
        "bank": best_buy["bank"],
        "value": best_buy["buy"],
    },
    "highest_buy": {
        "bank": highest_buy["bank"],
        "value": highest_buy["buy"],
    },
    "lowest_sell": {
        "bank": best_sell["bank"],
        "value": best_sell["sell"],
    },
    "highest_sell": {
        "bank": highest_sell["bank"],
        "value": highest_sell["sell"],
    },
    "average_buy": avg_buy,
    "average_sell": avg_sell,
}
    # Export latest market snapshot
    export_json(results, summary)
    export_csv(results)
    sync_history()

    stats = Table(show_header=False)

    stats.add_column(style="bold cyan")
    stats.add_column()

    stats.add_row("Banks Processed", str(len(results)))
    stats.add_row(
        "Lowest Buy",
        f'{best_buy["bank"]} ({best_buy["buy"]:.4f})',
    )
    stats.add_row(
        "Highest Buy",
        f'{highest_buy["bank"]} ({highest_buy["buy"]:.4f})',
    )
    stats.add_row(
        "Lowest Sell",
        f'{best_sell["bank"]} ({best_sell["sell"]:.4f})',
    )
    stats.add_row(
        "Highest Sell",
        f'{highest_sell["bank"]} ({highest_sell["sell"]:.4f})',
    )
    stats.add_row(
        "Average Buy",
        f"{avg_buy:.4f}",
    )
    stats.add_row(
        "Average Sell",
        f"{avg_sell:.4f}",
    )

    console.print()
    console.print(
        Panel.fit(
            stats,
            title="Market Statistics",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()