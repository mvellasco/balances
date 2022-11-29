"""Module to hold data structures used in the project."""
from collections import namedtuple
from dataclasses import dataclass
from decimal import Decimal

# Using a namedtuple here since they are more lightweight than other structures.
Event = namedtuple("Event", ("id", "type", "amount", "date_created"))


@dataclass
class Advance:
    """Represents an advance, with the *event* and *balance*"""
    event: Event
    balance: Decimal
