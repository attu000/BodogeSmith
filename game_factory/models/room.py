from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from .game import Game


class Room(models.Model):
    """
    playできるUserを管理するModel
    """
    # --- ステータスの選択肢を定義 ---
    class RoomStatus(models.TextChoices):
        OPEN = 'OPEN', '解放'
        CLOSED = 'CLOSED', '締切'

    _name = models.CharField("部屋の名前", max_length=100, unique=True)
    _password = models.CharField("パスワード", max_length=128)
    _created_at = models.DateTimeField(auto_now_add=True)
    _owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="owned_game_rooms", 
        verbose_name="オーナー"
    )

    _status = models.CharField(
        "ステータス",
        max_length=10,
        choices=RoomStatus.choices,
        default=RoomStatus.OPEN
    )

    #game
    _game = models.ForeignKey(
        Game,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        default=None,
        related_name='game_room',
    )


    #playing_roomで遊ぶことができるUser
    _playing_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="joined_playing_game_rooms", 
        blank=True, 
        verbose_name="参加メンバー"
    )

    
    
    #passward------
    def set_password(self, raw_password):
        self._password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self._password)
    

    



    #playing_members-----------
    def add_playing_member(self, user):
        if user in self._playing_members.all():
            return
        self._playing_members.add(user)
        self.save()

    def remove_playing_member(self, user):
        self._playing_members.remove(user)
        self.save()

    def clear_playing_members(self):
        self._playing_members.clear()




    #owner------------------
    def set_owner(self, user):
        self._owner = user
        self.save()

    
    # --- ステータス関連メソッド ---
    def open_room(self):
        """部屋のステータスを「募集中」に変更します。"""
        self._status = self.RoomStatus.OPEN
        self.save(update_fields=['_status'])

    def close_room(self):
        """部屋のステータスを「締切」に変更します。"""
        self._status = self.RoomStatus.CLOSED
        self.save(update_fields=['_status'])

    

    #====propaty()=========================
    
    @property
    def name(self):
        return self._name
    
    @property
    def created_at(self):
        return self._created_at
    
    @property
    def owner(self):
        return self._owner
    
    @property
    def waiting_members(self):
        return self._waiting_members
    
    @property
    def playing_members(self):
        return self._playing_members
    
    @property
    def status(self):
        return self._status
    
    @property
    def game(self):
        return self._game
    
    @game.setter
    def game(self, game: 'Game'):
        self._game = game
        self.save()

    

    #====基本メソッド================
    def __str__(self):
        return self.name
