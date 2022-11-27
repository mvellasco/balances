from datetime import datetime, timedelta
from decimal import Decimal

from .service import EventService
from .structures import Advance


class AdvanceStats:
    """Represent stats for advances."""

    def __init__(self, *args, **kwargs):
        self.overall_advance_balance = Decimal(0)
        self.overall_interest_payable_balance = Decimal(0)
        self.overall_interest_paid = Decimal(0)
        self.overall_payments_for_future = Decimal(0)
        self.total_interest_balance = Decimal(0)

    def calculate_overall_balance(self, advances):
        """Perform overall advance balance calculation."""
        self.overall_advance_balance = sum(Decimal(advance.balance) for advance in advances)
        return self.overall_advance_balance

    def process_for_date(self, ctx, end_date):
        """Process all events and keep track of specific stats.

        Return the advances found and processed.
        """
        events = EventService.filter_by_date(context=ctx, end_date=end_date)
        first_event_date = events[0].date_created
        dt_delta = datetime.fromisoformat(end_date) - datetime.fromisoformat(first_event_date)
        total_days = [
            datetime.fromisoformat(first_event_date) + timedelta(days=x)
            for x in range(dt_delta.days + 1)
        ]
        advances = []
        for day in total_days:
            # Check events for the day, calculate balances for interest
            # and total at the end of the process
            for event in filter(lambda e: datetime.fromisoformat(e.date_created) == day, events):
                # TODO: refactor this into a separate class that will do the
                # operations based on the given events.
                if event.type == "advance":
                    balance = event.amount
                    if self.overall_payments_for_future > 0:
                        if self.overall_payments_for_future > balance:
                            self.overall_payments_for_future -= balance
                            balance = 0
                        else:
                            balance = balance - self.overall_payments_for_future
                            self.overall_payments_for_future = 0
                    # TODO: refactor this into a proper method
                    advance = Advance(event=event, balance=round(balance, 2))
                    advances.append(advance)

                if event.type == "payment":
                    amount_to_pay = Decimal(event.amount)
                    if amount_to_pay <= 0:
                        continue

                    # Pay interest
                    if self.total_interest_balance > 0:
                        if amount_to_pay > self.total_interest_balance:
                            self.overall_interest_paid += self.total_interest_balance
                            amount_to_pay -= self.total_interest_balance
                            self.total_interest_balance = 0
                        else:
                            self.overall_interest_paid += amount_to_pay
                            self.total_interest_balance -= amount_to_pay
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
                        self.overall_payments_for_future += amount_to_pay
                        amount_to_pay = 0

            total_balance = self.calculate_overall_balance(advances=advances)
            total_interest_for_day = Decimal(total_balance) * Decimal(0.00035)
            self.total_interest_balance += Decimal(total_interest_for_day)
            self.overall_interest_payable_balance = Decimal(self.total_interest_balance)

            # Calculate final overall balance at the end
            self.calculate_overall_balance(advances=advances)

        return advances
