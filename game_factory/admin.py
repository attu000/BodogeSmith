from django.contrib import admin
from .models import Room, Game, GameDesign, Card

# Register  # 1. models.pyからPostとCategoryをインポート

# 2. インポートしたモデルを登録
admin.site.register(Room)
admin.site.register(Game)
admin.site.register(GameDesign)
admin.site.register(Card)