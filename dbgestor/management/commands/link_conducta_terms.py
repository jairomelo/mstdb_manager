"""
Backfill command to link PersonaEsclavizada.conducta free text to the canonical
ConductaTerm vocabulary (e.g. huído).

Dry-run by default. --apply links only unambiguous matches; wildcard aliases
(trailing '*') and --review-alias words (default: 'busque') are reported for
manual review and never linked automatically.

    python manage.py link_conducta_terms --term huído
    python manage.py link_conducta_terms --apply --csv report.csv
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from dbgestor.models import ConductaTerm, PersonaEsclavizada

SNIPPET_CONTEXT = 60


class Command(BaseCommand):
    help = 'Link PersonaEsclavizada.conducta free text to canonical ConductaTerm entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--term',
            type=str,
            default=None,
            help='Canonico (or alias) of a single ConductaTerm to process (default: all terms)',
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Link matched personas to the term. Without this flag, dry-run only.',
        )
        parser.add_argument(
            '--review-alias',
            action='append',
            default=['busque'],
            help='Alias that should be reported as review instead of linked (repeatable)',
        )
        parser.add_argument(
            '--csv',
            type=str,
            default=None,
            help='Path to write the report CSV (persona_id, conducta_snippet, matched_alias, action)',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        review_aliases = {a.strip().lower() for a in options['review_alias'] if a.strip()}

        terms = ConductaTerm.objects.all()
        if options['term']:
            term = ConductaTerm.resolve(options['term'])
            if not term:
                raise CommandError(f'No ConductaTerm found for "{options["term"]}"')
            terms = [term]

        report_rows = []
        summary = []

        for term in terms:
            already = term.personas_esclavizadas.values_list('persona_id', flat=True)
            qs = PersonaEsclavizada.objects.exclude(persona_id__in=already).exclude(
                conducta__isnull=True
            ).exclude(conducta='')

            linked = 0
            review = 0
            term_rows = []
            seen_personas = set()
            for word in [term.canonico, *term.aliases]:
                is_review = word in review_aliases or word.endswith('*')
                candidates = qs.filter(conducta__unaccent__icontains=word.rstrip('*'))
                for persona in candidates:
                    if persona.persona_id in seen_personas:
                        continue
                    seen_personas.add(persona.persona_id)
                    action = 'review' if is_review else 'link'
                    if action == 'link':
                        linked += 1
                    else:
                        review += 1
                    term_rows.append({
                        'persona_id': persona.persona_id,
                        'conducta_snippet': self._snippet(persona.conducta, word.rstrip('*')),
                        'matched_alias': word,
                        'action': action,
                    })
            report_rows.extend(term_rows)

            label = f'{term.canonico}: {linked} link / {review} review'
            if apply_changes:
                link_ids = [r['persona_id'] for r in term_rows if r['action'] == 'link']
                if link_ids:
                    term.personas_esclavizadas.add(*PersonaEsclavizada.objects.filter(
                        persona_id__in=link_ids
                    ))
                label += ' — linked'
            else:
                label += ' (dry-run)'
            summary.append(label)

        for line in summary:
            self.stdout.write(line)

        if options['csv']:
            self._write_csv(options['csv'], report_rows)
            self.stdout.write(self.style.SUCCESS(f'Report written to {options["csv"]}'))

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry-run: nothing was linked. Use --apply to link.'))

    @staticmethod
    def _snippet(text, match):
        if not text:
            return ''
        lowered = text.lower()
        idx = lowered.find(match.lower())
        if idx == -1:
            idx = 0
        start = max(0, idx - SNIPPET_CONTEXT)
        end = min(len(text), idx + len(match) + SNIPPET_CONTEXT)
        snippet = text[start:end].replace('\n', ' ')
        return ('…' if start > 0 else '') + snippet + ('…' if end < len(text) else '')

    def _write_csv(self, path, rows):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f, fieldnames=['persona_id', 'conducta_snippet', 'matched_alias', 'action']
            )
            writer.writeheader()
            writer.writerows(rows)
