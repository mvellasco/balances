#!/usr/bin/env python3
import click
import csv
from datetime import datetime, timedelta
from decimal import Decimal
import os
import sqlite3
from typing import Dict

from data.service import EventService
from data.structures import Advance


@click.group()
@click.option("--debug/--no-debug", default=False, help="Debug output, or no debug output.")
@click.pass_context
def interface(ctx: Dict, debug: bool) -> None:
    """Ampla engineering takehome ledger calculator."""
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug  # you can use ctx.obj['DEBUG'] in other commands to log or print if DEBUG is on
    ctx.obj["DB_PATH"] = os.path.join(os.getcwd(), "db.sqlite3")
    if debug:
        click.echo(f"[Debug mode is on]")


@interface.command()
@click.pass_context
def create_db(ctx: Dict) -> None:
    """Initialize sqlite3 database."""
    if os.path.exists(ctx.obj["DB_PATH"]):
        click.echo("Database already exists")
        return

    with sqlite3.connect(ctx.obj["DB_PATH"]) as connection:
        if not connection:
            click.echo(
                "Error: Unable to create sqlite3 db file. Please ensure sqlite3 is installed on your system and "
                "available in PATH!"
            )
            return

        cursor = connection.cursor()
        cursor.execute(
            """
            create table events
            (
                id integer not null primary key autoincrement,
                type varchar(32) not null,
                amount decimal not null,
                date_created date not null
                CHECK (type IN ("advance", "payment"))
            );
        """
        )
        connection.commit()
    click.echo(f"Initialized database at {ctx.obj['DB_PATH']}")


@interface.command()
@click.pass_context
def drop_db(ctx: Dict) -> None:
    """Delete sqlite3 database."""
    if not os.path.exists(ctx.obj["DB_PATH"]):
        click.echo(f"SQLite database does not exist at {ctx.obj['DB_PATH']}")
    else:
        os.unlink(ctx.obj["DB_PATH"])
        click.echo(f"Deleted SQLite database at {ctx.obj['DB_PATH']}")


@interface.command()
@click.argument("filename", type=click.Path(exists=True, writable=False, readable=True))
@click.pass_context
def load(ctx: Dict, filename: str) -> None:
    """Load events with data from csv file."""
    if not os.path.exists(ctx.obj["DB_PATH"]):
        click.echo(f"Database does not exist at {ctx.obj['DB_PATH']}, please create it using `create-db` command")
        return

    loaded = 0
    with open(filename) as infile, sqlite3.connect(ctx.obj["DB_PATH"]) as connection:
        cursor = connection.cursor()
        reader = csv.reader(infile)
        for row in reader:
            cursor.execute(
                f"insert into events (type, amount, date_created) values (?, ?, ?)", (row[0], row[2], row[1])
            )
            loaded += 1
        connection.commit()

    click.echo(f"Loaded {loaded} events from {filename}")


@interface.command()
@click.argument("end_date", required=False, type=click.STRING)
@click.pass_context
def balances(ctx: Dict, end_date: str = None) -> None:
    """Display balance statistics as of `end_date`."""
    # NOTE: You may not change the function signature of `balances`,
    #       however you may implement it any way you want, so long
    #       as you adhere to the format specification.
    #       Here is some code to get you started!
    if end_date is None:
        end_date = datetime.now().date().isoformat()

    overall_advance_balance = Decimal(0)
    overall_interest_payable_balance = Decimal(0)
    overall_interest_paid = Decimal(0)
    overall_payments_for_future = Decimal(0)
    total_interest_balance = Decimal(0)

    # query events from database example
    total_events = EventService.get_all_events(context=ctx)
    events = list(filter(lambda e: e.date_created <= end_date, total_events))
    total_days = [
        datetime.fromisoformat(events[0].date_created) + timedelta(days=x)
        for x in range(
            (datetime.fromisoformat(end_date) - datetime.fromisoformat(events[0].date_created)).days + 1
        )
    ]
    advances = []

    for day in total_days:  # TODO: Place this in a event processor
        # Check events for the day, calculate balances for interest
        # and total at the end of the process
        for event in filter(lambda e: datetime.fromisoformat(e.date_created) == day, events):
            # TODO: refactor this into a separate class that will do the
            # operations based on the given events.
            if event.type == "advance":
                balance = event.amount
                if overall_payments_for_future > 0:
                    if overall_payments_for_future > balance:
                        overall_payments_for_future -= balance
                        balance = 0
                    else:
                        balance = balance - overall_payments_for_future
                        overall_payments_for_future = 0
                advance = Advance(event=event, balance=round(balance, 2))
                advances.append(advance)

            if event.type == "payment":
                amount_to_pay = Decimal(event.amount)
                if amount_to_pay > 0:
                    # Pay interest
                    if total_interest_balance > 0:
                        if amount_to_pay > total_interest_balance:
                            overall_interest_paid += total_interest_balance
                            amount_to_pay -= total_interest_balance
                            total_interest_balance = 0
                        else:
                            overall_interest_paid += amount_to_pay
                            total_interest_balance -= amount_to_pay
                            amount_to_pay = 0

                    # Pay the advances
                    for adv in advances:
                        _paid = 0
                        if amount_to_pay > adv.balance:
                            _paid += adv.balance
                            adv.balance = 0
                        elif amount_to_pay < adv.balance:
                            _paid += amount_to_pay
                            adv.balance -= amount_to_pay
                        else:
                            _paid += adv.balance
                            adv.balance = 0

                        amount_to_pay -= _paid

                    if amount_to_pay > 0:
                        # Sum remaining amount to future payments
                        overall_payments_for_future += amount_to_pay
                        amount_to_pay = 0

        total_balance = sum(Decimal(adv.balance) for adv in advances)
        total_interest_for_day = Decimal(total_balance) * Decimal(0.00035)
        total_interest_balance += Decimal(total_interest_for_day)
        overall_interest_payable_balance = Decimal(total_interest_balance)

        # Calculate final overall balance at the end
        overall_advance_balance = sum(Decimal(advance.balance) for advance in advances)

    click.echo("Advances:")
    click.echo("----------------------------------------------------------")
    click.echo("{0:>10}{1:>11}{2:>17}{3:>20}".format("Identifier", "Date", "Initial Amt", "Current Balance"))

    for seq, adv in enumerate(advances, start=1):
        click.echo("{0:>10}{1:>11}{2:>17}{3:>20}".format(
            seq,
            adv.event.date_created,
            round(Decimal(adv.event.amount), 2),
            round(Decimal(adv.balance), 2),
        ))

    click.echo("\nSummary Statistics:")
    click.echo("----------------------------------------------------------")
    click.echo("Aggregate Advance Balance: {0:31.2f}".format(overall_advance_balance))
    click.echo("Interest Payable Balance: {0:32.2f}".format(overall_interest_payable_balance))
    click.echo("Total Interest Paid: {0:37.2f}".format(overall_interest_paid))
    click.echo("Balance Applicable to Future Advances: {0:>19.2f}".format(overall_payments_for_future))


if __name__ == "__main__":
    interface()
