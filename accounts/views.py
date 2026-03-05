from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('account_login')
    else:
        form = UserCreationForm()
    return render(request, 'account/signup.html', {'form': form})
