#account > urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('signup/', views.AccountSignUpView.as_view(), name='signup'),
    path('login/', views.AccountLoginView.as_view(), name='login'),
    path('logout/', views.AccountLogoutView.as_view(), name='logout'),
]