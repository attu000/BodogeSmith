from django import forms
from .models import Room

class RoomCreationForm(forms.ModelForm):
    """部屋作成フォーム"""
    password = forms.CharField(widget=forms.PasswordInput, label="パスワード")

    class Meta:
        model = Room
        fields = ['_name', '_password']
        labels = {
            'name': '部屋の名前',
        }


class RoomJoinForm(forms.Form):
    """部屋参加フォーム"""
    name = forms.CharField(label="部屋の名前")
    password = forms.CharField(widget=forms.PasswordInput, label="パスワード")