from django.urls import path
from . import views
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/join/', views.join_room, name='join_room'),
    path('rooms/waiting/<int:room_id>/', views.waiting_room, name='waiting_room'),
    path('rooms/playing/<int:room_id>/', views.playing_room, name='playing_room'),
    
]

# DEBUGモードの時に静的ファイルを配信するための設定
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
