"""
Populate UserProfile rows from the contributors data in mstdb_theme/src/conf/contributors.js.
Matches users by username (case-insensitive, using the first part of the contributor name).
Run with: python manage.py seed_user_profiles [--dry-run]

Contributors without a matching Django user are skipped; run this command again
after creating the relevant user accounts.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

# Mirrors mstdb_theme/src/conf/contributors.js
CONTRIBUTORS = [
    # coordinators
    dict(name="Alvaro Alcántara", institution="Centro INAH Veracruz",
         institution_url="https://www.inah.gob.mx/", role="coordinator"),
    dict(name="Alex Borucki", institution="Universidad de California, Irvine",
         institution_url="https://www.ucirvine.edu/", role="coordinator"),
    dict(name="Gabriela Iturralde", institution="INAH, Ciudad de México",
         institution_url="https://www.inah.gob.mx/", role="coordinator"),
    dict(name="Sabrina Smith", institution="Universidad de California, Merced",
         institution_url="https://www.ucmerced.edu/", role="coordinator"),
    # collaborators
    dict(name="Gabriela Iturralde Nieto", institution="INAH, Ciudad de México",
         institution_url="", role="collaborator"),
    dict(name="Maira Cristina Córdova", institution="UNAM",
         institution_url="", role="collaborator"),
    dict(name="Jorge E. Delgadillo Núñez", institution="Universidad de Vanderbilt",
         institution_url="", role="collaborator"),
    dict(name="Luis Benedicto Juárez Luévano", institution="Universidad de Hamburgo",
         institution_url="", role="collaborator"),
    dict(name="María Irma López",
         institution="Instituto Nacional de Antropología e Historia",
         institution_url="", role="collaborator"),
    dict(name="Julieta Pineda", institution="", institution_url="", role="collaborator"),
    dict(name="Pablo Miguel Sierra Silva", institution="Universidad de Rochester",
         institution_url="", role="collaborator"),
    dict(name="Tatiana Seijas", institution="Rutgers University",
         institution_url="", role="collaborator"),
    # research assistants
    dict(name="Berenice Tepozano", institution="Universidad de California, Irvine",
         institution_url="https://www.humanities.uci.edu/students/berenice-tepozano",
         role="research_assistant"),
    # developers
    dict(name="Jairo A. Melo Flórez",
         institution="Digital Humanities Research Facilitator, UCSB Library",
         institution_url="https://www.library.ucsb.edu/staff/jairo-melo-florez",
         role="developer"),
]


def _candidate_usernames(full_name):
    """Generate likely username candidates from a full name."""
    parts = full_name.lower().split()
    if not parts:
        return []
    candidates = [
        parts[0],                           # first name
        "".join(parts),                     # alljoinedtogether
        parts[0] + parts[-1],               # firstlast
        parts[-1],                          # last name
    ]
    if len(parts) >= 2:
        candidates.append(f"{parts[0]}.{parts[-1]}")   # first.last
        candidates.append(f"{parts[0]}_{parts[-1]}")   # first_last
    return list(dict.fromkeys(candidates))  # preserve order, deduplicate


class Command(BaseCommand):
    help = "Seed UserProfile from contributors data"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Show what would be updated without saving")

    def handle(self, *args, **options):
        from cataloguers.models import UserProfile

        dry_run = options['dry_run']
        updated = skipped = 0

        for contrib in CONTRIBUTORS:
            user = None
            for candidate in _candidate_usernames(contrib['name']):
                try:
                    user = User.objects.get(username__iexact=candidate)
                    break
                except User.DoesNotExist:
                    continue

            if user is None:
                self.stdout.write(
                    self.style.WARNING(f"  No user match for: {contrib['name']}")
                )
                skipped += 1
                continue

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.institution = contrib.get('institution', '')
            profile.institution_url = contrib.get('institution_url', '')
            profile.role = contrib.get('role', '')

            if not dry_run:
                profile.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  Updated profile for {user.username} ({contrib['name']})"
                ))
            else:
                self.stdout.write(
                    f"  [dry-run] Would update {user.username} ({contrib['name']})"
                )
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone: {updated} updated, {skipped} skipped (no user match)")
        )
