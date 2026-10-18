"""Seed reviewed English drafts for unambiguous vocabulary registries.

Idempotent: creates missing rows as ``draft`` and never touches existing rows
(status or value), so team edits and publishes in the workbench are never
overwritten — same fill-when-empty contract as ``seed_variable_definitions``.
Domain-sensitive registries (Calidades, Etonimos, Hispanizaciones,
Actividades, ConductaTerm, descripcion fields) are deliberately excluded;
translate those via the workbench or ``import_translations`` with
team-reviewed CSVs.

Usage:
    python manage.py seed_vocab_translations_en
"""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from dbgestor.models import Translation

# (model_name, object_id, field_name, en_value)
REGISTRY = [
    # ---------------------------------------------------------- EstadoCivil
    ('estadocivil', 1, 'estado_civil', 'Widow'),
    ('estadocivil', 2, 'estado_civil', 'Married'),
    ('estadocivil', 3, 'estado_civil', 'Single'),
    ('estadocivil', 4, 'estado_civil', 'Married'),
    ('estadocivil', 5, 'estado_civil', 'Single'),
    ('estadocivil', 6, 'estado_civil', 'Widower'),
    ('estadocivil', 7, 'estado_civil', 'Maiden'),
    # ----------------------------------------------------- TiposInstitucion
    ('tiposinstitucion', 1, 'tipo', 'Convent'),
    ('tiposinstitucion', 2, 'tipo', 'Parish'),
    ('tiposinstitucion', 3, 'tipo', 'College'),
    ('tiposinstitucion', 4, 'tipo', 'Town council'),
    ('tiposinstitucion', 5, 'tipo', 'City'),
    ('tiposinstitucion', 6, 'tipo', 'Confraternity'),
    ('tiposinstitucion', 7, 'tipo', 'Hospital'),
    ('tiposinstitucion', 8, 'tipo', 'Monastery'),
    ('tiposinstitucion', 9, 'tipo', 'State government'),
    ('tiposinstitucion', 10, 'tipo', 'Hacienda'),
    ('tiposinstitucion', 11, 'tipo', 'Orphanage'),
    ('tiposinstitucion', 12, 'tipo', 'Pious foundation for orphan girls'),
    # ------------------------------------------------------------ TipoLugar
    ('tipolugar', 1, 'tipo_lugar', 'city'),
    ('tipolugar', 2, 'tipo_lugar', 'town'),
    ('tipolugar', 3, 'tipo_lugar', 'state'),
    ('tipolugar', 4, 'tipo_lugar', 'governorship'),
    ('tipolugar', 5, 'tipo_lugar', 'country'),
    ('tipolugar', 6, 'tipo_lugar', 'province'),
    ('tipolugar', 7, 'tipo_lugar', 'town'),
    ('tipolugar', 8, 'tipo_lugar', 'royal mining town'),
    ('tipolugar', 9, 'tipo_lugar', 'parish'),
    ('tipolugar', 10, 'tipo_lugar', 'fort'),
    ('tipolugar', 11, 'tipo_lugar', 'port'),
    ('tipolugar', 12, 'tipo_lugar', 'island'),
    ('tipolugar', 13, 'tipo_lugar', 'region'),
    ('tipolugar', 14, 'tipo_lugar', 'diocese'),
    ('tipolugar', 15, 'tipo_lugar', 'hacienda'),
    ('tipolugar', 16, 'tipo_lugar', 'Captaincy General'),
    # ------------------------------------------------------------ RolEvento
    ('rolevento', 1, 'rol_evento', 'grantor'),
    ('rolevento', 2, 'rol_evento', 'buyer'),
    ('rolevento', 3, 'rol_evento', 'previous owner'),
    ('rolevento', 4, 'rol_evento', 'owner of the enslaved person'),
    ('rolevento', 5, 'rol_evento', 'intermediary'),
    ('rolevento', 6, 'rol_evento', 'guarantor'),
    ('rolevento', 7, 'rol_evento', 'grantor of the power of attorney'),
    ('rolevento', 8, 'rol_evento', 'recipient of the power of attorney'),
    ('rolevento', 9, 'rol_evento', 'owner'),
    ('rolevento', 10, 'rol_evento', 'recipient of the donation'),
    ('rolevento', 11, 'rol_evento', 'seller'),
    ('rolevento', 12, 'rol_evento', 'payer'),
    ('rolevento', 13, 'rol_evento', 'executor of the will'),
    ('rolevento', 14, 'rol_evento', 'executor'),
    ('rolevento', 15, 'rol_evento', 'testator'),
    ('rolevento', 16, 'rol_evento', 'heir'),
    ('rolevento', 17, 'rol_evento', 'later owner'),
    ('rolevento', 18, 'rol_evento', 'executor'),
    ('rolevento', 19, 'rol_evento', 'recipient'),
    ('rolevento', 20, 'rol_evento', 'attorney-in-fact'),
    ('rolevento', 21, 'rol_evento', 'deceased owner'),
    ('rolevento', 22, 'rol_evento', 'lender'),
    ('rolevento', 23, 'rol_evento', 'notary'),
    ('rolevento', 24, 'rol_evento', 'witness'),
    ('rolevento', 25, 'rol_evento', 'financier'),
    ('rolevento', 26, 'rol_evento', 'mother'),
    ('rolevento', 27, 'rol_evento', 'bearer of the power of attorney'),
    ('rolevento', 28, 'rol_evento', 'administrator of the estate'),
    ('rolevento', 29, 'rol_evento', 'holder of goods'),
    ('rolevento', 30, 'rol_evento', 'dowry recipient'),
    ('rolevento', 31, 'rol_evento', 'grantor of the dowry'),
    ('rolevento', 32, 'rol_evento', 'recipient of the dowry'),
    ('rolevento', 33, 'rol_evento', 'asentista'),
    ('rolevento', 34, 'rol_evento', 'owner'),
    ('rolevento', 35, 'rol_evento', 'previous owner'),
    ('rolevento', 36, 'rol_evento', 'owner'),
    ('rolevento', 37, 'rol_evento', 'seller'),
    ('rolevento', 38, 'rol_evento', 'debtor'),
    ('rolevento', 39, 'rol_evento', 'seller and owner'),
    ('rolevento', 40, 'rol_evento', 'former owner'),
    ('rolevento', 41, 'rol_evento', 'former owner (deceased)'),
    ('rolevento', 42, 'rol_evento', 'executor and holder of goods'),
    ('rolevento', 43, 'rol_evento', 'owner (deceased)'),
    ('rolevento', 44, 'rol_evento', 'guardian'),
    ('rolevento', 45, 'rol_evento', 'grantor of dowry'),
    ('rolevento', 46, 'rol_evento', 'owner (deceased)'),
    ('rolevento', 47, 'rol_evento', 'seller (with power of attorney)'),
    ('rolevento', 48, 'rol_evento', 'mortgagor'),
    ('rolevento', 49, 'rol_evento', 'notifier'),
    ('rolevento', 50, 'rol_evento', 'payee'),
    ('rolevento', 51, 'rol_evento', 'recipient of the enslaved woman'),
    ('rolevento', 52, 'rol_evento', 'creditor'),
    ('rolevento', 53, 'rol_evento', 'assignor'),
    ('rolevento', 54, 'rol_evento', 'guardian'),
    ('rolevento', 55, 'rol_evento', 'assignee of the rights'),
    ('rolevento', 56, 'rol_evento', 'beneficiary'),
    ('rolevento', 57, 'rol_evento', 'mortgagee'),
    ('rolevento', 58, 'rol_evento', 'recipient of the enslaved person'),
    ('rolevento', 59, 'rol_evento', 'representative'),
    ('rolevento', 60, 'rol_evento', 'previous seller'),
    ('rolevento', 61, 'rol_evento', 'donor'),
    ('rolevento', 62, 'rol_evento', 'attesting witness'),
    ('rolevento', 63, 'rol_evento', 'former seller (with power of attorney)'),
    ('rolevento', 64, 'rol_evento', 'buyer on behalf of the institution'),
    ('rolevento', 65, 'rol_evento', 'seller (licensed)'),
    ('rolevento', 66, 'rol_evento', 'seller (licensed)'),
    ('rolevento', 67, 'rol_evento', 'former notary'),
    ('rolevento', 68, 'rol_evento', 'seller (executor of the will)'),
    ('rolevento', 69, 'rol_evento', 'source of the inheritance'),
    ('rolevento', 70, 'rol_evento', 'trainer'),
    ('rolevento', 71, 'rol_evento', 'apprentice'),
    # ------------------------------------------------------- TipoDocumental
    ('tipodocumental', 1, 'tipo_documental', 'Bill of sale'),
    ('tipodocumental', 2, 'tipo_documental', 'Letter of manumission'),
    ('tipodocumental', 3, 'tipo_documental', 'Will'),
    ('tipodocumental', 4, 'tipo_documental', 'Barter, exchange and transfer'),
    ('tipodocumental', 5, 'tipo_documental', 'Special power of attorney'),
    ('tipodocumental', 6, 'tipo_documental', 'Bond for pesos'),
    ('tipodocumental', 7, 'tipo_documental', 'Inventory of goods'),
    ('tipodocumental', 8, 'tipo_documental', 'Dowry deed'),
    ('tipodocumental', 9, 'tipo_documental', 'Substitution of power of attorney'),
    ('tipodocumental', 10, 'tipo_documental', 'Mortgage/pledge'),
    ('tipodocumental', 11, 'tipo_documental', 'Receipt of payment'),
    ('tipodocumental', 12, 'tipo_documental', 'Donation of enslaved persons'),
    ('tipodocumental', 13, 'tipo_documental', 'License'),
    ('tipodocumental', 14, 'tipo_documental', 'Auction sale'),
    ('tipodocumental', 15, 'tipo_documental', 'Transfer'),
    ('tipodocumental', 16, 'tipo_documental', 'Inheritance'),
    ('tipodocumental', 17, 'tipo_documental', 'Auction'),
    ('tipodocumental', 18, 'tipo_documental', 'Receipt and settlement of accounts'),
    ('tipodocumental', 19, 'tipo_documental', 'Power of attorney'),
    ('tipodocumental', 20, 'tipo_documental', 'Codicil'),
    ('tipodocumental', 21, 'tipo_documental', 'Dowry receipt'),
    ('tipodocumental', 23, 'tipo_documental', 'Distribution of goods'),
    ('tipodocumental', 24, 'tipo_documental', 'Power to make a will'),
    ('tipodocumental', 25, 'tipo_documental', 'Transfer of power of attorney'),
    ('tipodocumental', 26, 'tipo_documental', 'Sale at public auction'),
    ('tipodocumental', 27, 'tipo_documental', 'Payment bond'),
    ('tipodocumental', 28, 'tipo_documental', 'Cancellation of deed'),
    ('tipodocumental', 29, 'tipo_documental', 'Sale that did not go through'),
    ('tipodocumental', 30, 'tipo_documental', 'Sale and cancellation'),
    ('tipodocumental', 31, 'tipo_documental', 'Sale and debt'),
    ('tipodocumental', 32, 'tipo_documental', 'Sale and return'),
    ('tipodocumental', 33, 'tipo_documental', 'Assignment of rights'),
    ('tipodocumental', 34, 'tipo_documental', 'Assignment of rights'),
    ('tipodocumental', 35, 'tipo_documental', 'Surety bond'),
    ('tipodocumental', 36, 'tipo_documental', 'Report on enslaved persons'),
    ('tipodocumental', 37, 'tipo_documental', 'Sale and bond'),
    ('tipodocumental', 38, 'tipo_documental', 'Special bond'),
    ('tipodocumental', 39, 'tipo_documental', 'Lease deed'),
    ('tipodocumental', 40, 'tipo_documental', 'Exchange'),
    ('tipodocumental', 41, 'tipo_documental', 'Approval and ratification of sale'),
    ('tipodocumental', 42, 'tipo_documental', 'Power of attorney and bill of sale'),
    ('tipodocumental', 43, 'tipo_documental', 'Short power of attorney and bill of sale'),
    ('tipodocumental', 44, 'tipo_documental', 'Declaration on the purchase of enslaved persons'),
    ('tipodocumental', 45, 'tipo_documental', 'Assignment of an enslaved person'),
    ('tipodocumental', 46, 'tipo_documental', 'Apprenticeship deed'),
    ('tipodocumental', 47, 'tipo_documental', 'Revocation of the letter of manumission'),
    ('tipodocumental', 48, 'tipo_documental', 'Declaration'),
    ('tipodocumental', 49, 'tipo_documental', 'Exchange of enslaved persons'),
    ('tipodocumental', 50, 'tipo_documental', 'Damaged/illegible document'),
    ('tipodocumental', 51, 'tipo_documental', 'Receipt for pesos'),
    # ------------------------------------------------------- SituacionLugar
    ('situacionlugar', 1, 'situacion', 'previous place 1'),
    ('situacionlugar', 4, 'situacion', 'neighbor'),
    ('situacionlugar', 5, 'situacion', 'origin'),
    ('situacionlugar', 6, 'situacion', 'residence'),
    ('situacionlugar', 7, 'situacion', 'sojourn'),
    ('situacionlugar', 8, 'situacion', 'transit'),
    ('situacionlugar', 9, 'situacion', 'dwelling'),
    ('situacionlugar', 10, 'situacion', 'neighborhood'),
    ('situacionlugar', 11, 'situacion', 'birth'),
    ('situacionlugar', 12, 'situacion', 'death'),
    ('situacionlugar', 13, 'situacion', 'marriage'),
    ('situacionlugar', 14, 'situacion', 'Cuicatlán (town)'),
    ('situacionlugar', 15, 'situacion', 'resident'),
    ('situacionlugar', 16, 'situacion', 'escaped'),
    ('situacionlugar', 17, 'situacion', 'neighbor'),
    ('situacionlugar', 18, 'situacion', 'resident'),
]


class Command(BaseCommand):
    help = 'Seed reviewed English drafts for unambiguous vocabulary registries'

    def handle(self, *args, **options):
        created = updated = skipped = 0
        ct_cache = {}
        for model_name, object_id, field_name, value in REGISTRY:
            if model_name not in ct_cache:
                ct_cache[model_name] = ContentType.objects.get_by_natural_key(
                    'dbgestor', model_name)
            ct = ct_cache[model_name]
            model_class = ct.model_class()
            if not model_class._default_manager.filter(pk=object_id).exists():
                skipped += 1
                continue
            _, was_created = Translation.objects.get_or_create(
                content_type=ct, object_id=object_id,
                field_name=field_name, language_code='en',
                defaults={'value': value, 'status': 'draft'},
            )
            created += was_created
            updated += not was_created
        self.stdout.write(self.style.SUCCESS(
            f'✓ Vocab EN drafts: {created} created, {updated} already present, '
            f'{skipped} skipped'))
