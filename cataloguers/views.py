from django.shortcuts import render, redirect
from django.contrib.auth  import authenticate, login, logout
from django.contrib import messages
from .forms import RegisterUserForm

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
            messages.success(request, f"No fue posible ingresar con el usuario {username}.")
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
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, f"Una cordial bienvenida {username}")
            return redirect('home')
    else:
        form = RegisterUserForm()
    return render(request, 'cataloguers/register.html', {'form':form})