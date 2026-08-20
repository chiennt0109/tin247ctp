from django.shortcuts import render, redirect
from .forms import SecureSignupForm

def signup(request):
    if request.method == 'POST':
        form = SecureSignupForm(request.POST)
        if form.is_valid():
            form.save(request)
            return redirect('account_login')
    else:
        form = SecureSignupForm()
    return render(request, 'account/signup.html', {'form': form})
