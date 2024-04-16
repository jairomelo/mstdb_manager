from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib.auth  import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from .forms import RegisterUserForm

import logging

logger = logging.getLogger("dbgestor")

def login_user(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None and password is not None:
            login(request, user)
            messages.success(request, f"Hola nuevamente {username} :)")
            return redirect('home')
            
        else:
            messages.error(request, f"No fue posible ingresar con el usuario {username}.")
            return redirect('login')
        
    else:
        return render(request, 'cataloguers/login.html', {})


def logout_user(request):
    logout(request)
    messages.success(request, "Hasta pronto :)")
    return redirect('home')


def register_user(request):
    if request.method == 'POST':
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  
            user.save()

            # Generate token and send email
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            verification_url = request.build_absolute_uri(
                reverse('activate_account', kwargs={'uidb64': uid, 'token': token})
            )
            send_mail(
                'Verifica tu cuenta',
                f'Por favor, haz clic en el siguiente enlace para activar tu cuenta: {verification_url}',
                'soporte@abcng.org',
                [user.email],
                fail_silently=False,
            )

            messages.success(request, "Por favor, revisa tu email para confirmar el registro.")
            return redirect('login')
        else:
            messages.error(request, "Corrige los siguientes errores.")
            return render(request, 'authusers/register.html', {'form': form})
    else:
        form = RegisterUserForm()
        return render(request, 'authusers/register.html', {'form': form})
    

def activate_account(request, uidb64, token):
    User = get_user_model()
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and PasswordResetTokenGenerator().check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, "¡Haz verificado exitosamente tu cuenta!")
        return redirect('home')
    else:
        messages.error(request, "¡El link de activación no es válido!")
        return redirect('register')
