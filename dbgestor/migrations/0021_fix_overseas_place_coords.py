from django.core.cache import cache
from django.db import migrations


# Bug 4 — Mapa Trayectorias: places whose names denote overseas origins
# (África occidental/central, Península Ibérica, Asia, Perú) were geocoded
# with placeholder coordinates inside the Gulf of Mexico box, so their arcs
# and markers rendered on top of Nueva España (e.g. "São Tomé en Brasil" —
# in the live DB the island of São Tomé resolves to "Santo Tomé", already
# correct at 0.32, 6.60, but Lisboa/Sevilla/Guinea/Congo/Mozambique/etc.
# still sit in Michoacán/Veracruz). Move them to their real-world positions.
#
# Only rows that still carry the exact bad coordinates are touched, so
# manual corrections made through the catalogar UI are never overwritten.
FIXES = [
    # (lugar_id, nombre patron, old_lat, old_lon, new_lat, new_lon)
    (19, 'Lisboa', 19.694030, -101.145390, 38.722252, -9.139337),
    (25, 'Cabo Verde', 19.172500, -96.299167, 14.917719, -23.509155),
    (29, 'Sevilla', 23.007360, -101.256910, 37.388630, -5.995340),
    (37, 'Castilla', 19.458330, -101.301110, 40.416775, -3.703790),
    (99, 'Portugal', 21.407500, -101.841110, 39.399872, -8.038654),
    (113, 'Guinea', 20.004720, -96.621670, 9.945587, -9.696645),
    (131, 'Mozambique', 19.059444, -96.253611, -18.665695, 35.529562),
    (137, 'Perú', 16.098330, -92.936110, -9.189967, -75.015152),
    (157, 'Filipinas', 15.971670, -93.328330, 12.879721, 121.774017),
    (190, 'Congo', 17.531080, -99.028800, -4.038333, 21.758664),
    (274, 'España', 19.415000, -99.171389, 40.463667, -3.749220),
]


def fix_coords(apps, schema_editor):
    Lugar = apps.get_model('dbgestor', 'Lugar')
    for lugar_id, _name, old_lat, old_lon, new_lat, new_lon in FIXES:
        Lugar.objects.filter(
            lugar_id=lugar_id, lat=old_lat, lon=old_lon,
        ).update(lat=new_lat, lon=new_lon)
    # Aggregated trajectory payloads are cached per querystring (600s TTL);
    # stale entries would keep rendering the old positions.
    try:
        cache.clear()
    except Exception:
        pass


def unfix_coords(apps, schema_editor):
    Lugar = apps.get_model('dbgestor', 'Lugar')
    for lugar_id, _name, old_lat, old_lon, new_lat, new_lon in FIXES:
        Lugar.objects.filter(
            lugar_id=lugar_id, lat=new_lat, lon=new_lon,
        ).update(lat=old_lat, lon=old_lon)


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0020_seed_conducta_terms'),
    ]

    operations = [
        migrations.RunPython(fix_coords, unfix_coords),
    ]
