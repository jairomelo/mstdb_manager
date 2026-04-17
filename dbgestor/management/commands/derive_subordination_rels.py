from django.core.management.base import BaseCommand
from dbgestor.models import Documento
from dbgestor.utils import derive_subordination_rels


class Command(BaseCommand):
    help = 'Derive subordination relations from PersonaRolEvento co-participants.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--documento_id',
            type=int,
            default=None,
            help='Process a single document by ID. Omit to process all documents.',
        )

    def handle(self, *args, **options):
        doc_id = options['documento_id']
        if doc_id:
            doc_ids = [doc_id]
        else:
            doc_ids = list(Documento.objects.values_list('documento_id', flat=True))

        total = 0
        for did in doc_ids:
            n = derive_subordination_rels(did)
            if n:
                self.stdout.write(f'  documento {did}: {n} relaciones creadas')
            total += n

        self.stdout.write(self.style.SUCCESS(f'Total: {total} relaciones de subordinación creadas.'))
