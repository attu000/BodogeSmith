from game_factory.consumers import GameFactoryWaitingRoomConsumer ,GameFactoryPlayingRoomConsumer

from django.urls import re_path # path から re_path に変更

websocket_urlpatterns = [
    # pathをre_pathに変更し、末尾に/?を追加
    re_path(r'ws/game_factory/rooms/waiting/(?P<room_id>\w+)/?$', GameFactoryWaitingRoomConsumer.as_asgi()),
    re_path(r'ws/game_factory/rooms/playing/(?P<room_id>\w+)/?$', GameFactoryPlayingRoomConsumer.as_asgi()),
]