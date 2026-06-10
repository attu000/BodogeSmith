from django.urls import path
from . import views
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

app_name = 'game_factory'

urlpatterns = [
    path('', views.home, name='home'),
    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/join/', views.join_room, name='join_room'),
    path('rooms/waiting/<int:room_id>/', views.waiting_room, name='waiting_room'),
    path('rooms/playing/<int:room_id>/', views.playing_room, name='playing_room'),
    path('rooms/create_game_design/', views.create_game_design, name='create_game_design'),
    path('rooms/edit_game_design/<int:game_design_id>/', views.edit_game_design, name='edit_game_design'),
    path('rooms/update_game_design/<int:game_design_id>/', views.update_game_design, name='update_game_design'),
    path('rooms/get_game_design_data/<int:game_design_id>/', views.get_game_design_data, name='get_game_design_data'),
    path('rooms/choice_game/<int:room_id>/', views.choice_game, name='choice_game'),
]

# DEBUGモードの時に静的ファイルを配信するための設定
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

