from django.db import models

# Create your models here.
class LogMessage(models.Model):
    level = models.CharField(max_length=10)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.level} - {self.message}"