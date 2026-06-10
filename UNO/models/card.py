from django.db import models
from django.conf import settings
from .room import Room


class Card(models.Model):
    """
    UNOカード1枚を表すモデル
    """

    color = models.CharField("色", max_length=10,)
    rank = models.CharField("種類/数字", max_length=20)
    action = models.TextField("カードの効果", blank=True)


    def __str__(self):
        return f'{self.rank}_{self.color}'
    
    @property
    def info_dict(self):
        info_dict = {
            'pk':self.pk,
            'color':self.color,
            'rank':self.rank,
            'action':self.action,
        }
        return info_dict


