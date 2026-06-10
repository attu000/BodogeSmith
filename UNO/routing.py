from UNO.consumers import WaitingRoomConsumer
from UNO.consumers import PlayingRoomConsumer

from django.urls import re_path # path から re_path に変更

websocket_urlpatterns = [
    # pathをre_pathに変更し、末尾に/?を追加
    re_path(r'ws/rooms/waiting/(?P<room_id>\w+)/?$', WaitingRoomConsumer.as_asgi()),
    re_path(r'ws/rooms/playing/(?P<room_id>\w+)/?$', PlayingRoomConsumer.as_asgi()),
]