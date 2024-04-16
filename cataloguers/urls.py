from django.urls import path

from .views import login_user, logout_user, register_user, activate_account

urlpatterns = [
    path('login_user', login_user, name='login'),
    path('logout_user', logout_user, name='logout'),
    path('register_user', register_user, name='register'),
    path('activate/<uidb64>/<token>/', activate_account, name='activate_account'),
]
