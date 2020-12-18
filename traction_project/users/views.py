from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from traction_app.secrets import auth_url_base, client_id
import random
import string


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            messages.success(request, f'Account created for {username}')
            user = authenticate(username=username, password=password)
            login(request, user)

            state = ''.join((random.choice(string.ascii_letters + string.digits) for i in range(24)))
            return redirect(f'{auth_url_base}?client_id={client_id}&response_type=code&state={state}')

    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'users/profile.html')
