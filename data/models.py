from decimal import Decimal


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
