from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'role')
    search_fields = ('user__username', 'user__email', 'institution')
    list_filter = ('role',)
    raw_id_fields = ('user',)
