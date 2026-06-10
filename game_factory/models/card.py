from django.db import models
from django.conf import settings

 
class Card(models.Model):
    """
    UNOカード1枚を表すモデル
    """


    _name = models.CharField("カードの名前", max_length=100)
    _created_at = models.DateTimeField(auto_now_add=True)
    _card_image = models.ImageField(
        "カード画像",
        upload_to='card_images/', # アップロード先のディレクトリを指定
        blank=True, # 画像がなくてもOK
        null=True   # データベースにNULLを許容
    )


    def __str__(self):
        return f'{self._name}'
    

    def to_dict(self):
        card_info_dict = {
            'card_id':self.id,
            'card_name':self.name,
            'card_url':self.image.url,
        }
        return card_info_dict
    
    @property
    def name(self):
        return self._name
    
    @property
    def image(self):
        return self._card_image
    
    



