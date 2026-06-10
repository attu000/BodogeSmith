from django import forms
from .models import Room, Card, GameDesign


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




class GameDesignBasicForm(forms.ModelForm):
    class Meta:
        model = GameDesign
        # フォームに表示するフィールドを指定
        fields = ['_name', '_player_limit']
        
        # フィールドの表示名を指定（任意）
        labels = {
            '_name': 'ゲームの名前',
            '_player_limit': 'プレイヤー上限人数',
        }


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['_name', '_card_image']
        labels = {
            '_name': 'カードの名前',
            '_card_image': 'カード画像',
        }