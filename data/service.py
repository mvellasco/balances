import sqlite3

from .structures import Event


class EventService:
    """Hold business logic for events."""
    @staticmethod
    def _fetch_events(ctx):
        with sqlite3.connect(ctx.obj["DB_PATH"]) as connection:
            cursor = connection.cursor()
            result = cursor.execute("select * from events order by date_created asc;")
            return result.fetchall()

    @staticmethod
    def get_all_events(context):
        """TODO: docstring me."""
        db_results = EventService._fetch_events(ctx=context)
        total_events = (Event(*res) for res in db_results)
        return total_events
