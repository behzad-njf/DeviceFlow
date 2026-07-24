from django.core.management.base import BaseCommand

from apps.routing.models import OperatorPrefix

# Common Iranian mobile prefixes (E.164). Longer prefixes win in resolver.
IR_PREFIXES = [
    # MCI (Hamrah Aval)
    ("+98910", "MCI"),
    ("+98911", "MCI"),
    ("+98912", "MCI"),
    ("+98913", "MCI"),
    ("+98914", "MCI"),
    ("+98915", "MCI"),
    ("+98916", "MCI"),
    ("+98917", "MCI"),
    ("+98918", "MCI"),
    ("+98919", "MCI"),
    ("+98990", "MCI"),
    ("+98991", "MCI"),
    ("+98992", "MCI"),
    ("+98993", "MCI"),
    ("+98994", "MCI"),
    # Irancell
    ("+98900", "Irancell"),
    ("+98901", "Irancell"),
    ("+98902", "Irancell"),
    ("+98903", "Irancell"),
    ("+98904", "Irancell"),
    ("+98905", "Irancell"),
    ("+98930", "Irancell"),
    ("+98933", "Irancell"),
    ("+98935", "Irancell"),
    ("+98936", "Irancell"),
    ("+98937", "Irancell"),
    ("+98938", "Irancell"),
    ("+98939", "Irancell"),
    # Rightel
    ("+98920", "Rightel"),
    ("+98921", "Rightel"),
    ("+98922", "Rightel"),
]


class Command(BaseCommand):
    help = "Seed Iranian mobile operator prefixes for smart routing"

    def handle(self, *args, **options):
        created = 0
        for prefix, operator in IR_PREFIXES:
            _, was_created = OperatorPrefix.objects.update_or_create(
                prefix=prefix,
                defaults={
                    "operator": operator,
                    "country": "IR",
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Operator prefixes ready ({created} created, "
                f"{OperatorPrefix.objects.filter(country='IR').count()} IR total)"
            )
        )
