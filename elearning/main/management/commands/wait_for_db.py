import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Block until the default database accepts connections."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, **options):
        deadline = time.time() + options["timeout"]
        while True:
            try:
                connections["default"].cursor()
                self.stdout.write(self.style.SUCCESS("Database is ready."))
                return
            except OperationalError as exc:
                if time.time() > deadline:
                    raise SystemExit(f"Database not reachable after {options['timeout']}s: {exc}")
                self.stdout.write("Database unavailable, retrying in 1s...")
                time.sleep(1)
