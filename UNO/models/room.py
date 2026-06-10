from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password

class Room(models.Model):
    """
    playできるUserを管理するModel
    """

    _name = models.CharField("部屋の名前", max_length=100, unique=True)
    _password = models.CharField("パスワード", max_length=128)
    _created_at = models.DateTimeField(auto_now_add=True)
    _owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="owned_rooms", 
        verbose_name="オーナー"
    )
    
    #waiting_roomにいるUser
    _waiting_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="joined_waiting_rooms", 
        blank=True, 
        verbose_name="参加メンバー"
    )

    #playing_roomで遊ぶことができるUser
    _playing_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="joined_playing_rooms", 
        blank=True, 
        verbose_name="参加メンバー"
    )

    
    
    #passward------
    def set_password(self, raw_password):
        self._password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self._password)
    

    

    #waiting_members-----------
    def add_waiting_member(self, user):
        if (user in self._waiting_members.all()) or (user in self._playing_members.all()):
            return
        self._waiting_members.add(user)
        self.save()

    def remove_waiting_member(self, user):
        self._waiting_members.remove(user)
        self.save()

    def clear_waiting_members(self):
        self._waiting_members.clear()



    #playing_members-----------
    def add_playing_member(self, user):
        if (user in self._waiting_members.all()) or (user in self._playing_members.all()):
            return
        self._playing_members.add(user)
        self.save()

    def remove_playing_member(self, user):
        self._playingmembers.remove(user)
        self.save()

    def clear_playing_members(self):
        self._playing_members.clear()


    #move_waitingList_and_playingList---
    def from_waiting_to_playing(self,user):
        """User一人を移動させる"""
        if (user in self._waiting_members.all()) or not(user in self._playing_members.all()):
            self.remove_waiting_member(user)
            self.add_playing_member(user)


    def from_playing_to_waiting(self,user):
        """User一人を移動させる"""
        if (user in self._playing_members.all()) or not(user in self._waiting_members.all()):
            self.remove_playing_member(user)
            self.add_waiting_member(user)


    def move_waitingList_to_playingList(self):
        """リストごと移動させる"""
        waiting_members = self._waiting_members.all()
        if len(waiting_members)<=0:
            return
        for member in waiting_members:
            self.from_waiting_to_playing(member)

    #owner------------------
    def set_owner(self, user):
        self._owner = user
        self.save()

    

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
    

    #====基本メソッド================
    def __str__(self):
        return self.name
