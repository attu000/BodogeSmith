# account/forms.py
from django.contrib.auth.forms import UserCreationForm
from .models import Account

class AccountSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta): # UserCreationForm.Metaを継承することを推奨
        model = Account
        fields = ("username",) # usernameのみ、またはAccountモデルに追加した他のフィールドを指定