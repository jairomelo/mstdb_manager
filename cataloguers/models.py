from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger("dbgestor")

User = get_user_model()

ROLE_CHOICES = [
    ('coordinator', 'Coordinador/a'),
    ('collaborator', 'Colaborador/a'),
    ('research_assistant', 'Ayudante de Investigación'),
    ('developer', 'Desarrollador/a'),
    ('cataloguer', 'Catalogador/a'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    bio = models.TextField(blank=True, default='')
    institution = models.CharField(max_length=255, blank=True, default='')
    institution_url = models.URLField(blank=True, default='')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, blank=True, default='')

    def __str__(self):
        return f"Profile: {self.user.username}"


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile whenever a new User is saved."""
    if created:
        UserProfile.objects.get_or_create(user=instance)