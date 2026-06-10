#account > views.py
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth import views as auth_views
from .forms import AccountSignupForm

# Create your views here.
class AccountSignUpView(generic.CreateView):
    form_class = AccountSignupForm
    success_url = reverse_lazy('login')
    template_name = 'account/signup.html'


class AccountLoginView(auth_views.LoginView):
    template_name = 'account/login.html'

class AccountLogoutView(auth_views.LogoutView):
    #logout後はHomeに戻る
    next_page = reverse_lazy('home')