from django.db import migrations


def create_profiles_for_existing_users(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('cataloguers', 'UserProfile')
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('cataloguers', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_profiles_for_existing_users,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
