import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from ..models.room import Room

class WaitingRoomConsumer(AsyncJsonWebsocketConsumer):
    groups = ['broadcast']


    #=======接続したとき====================================

    async def connect(self):
        
        """
        WebSocket接続がリクエストされたときに呼び出される非同期メソッド
        """
        #0.接続を許可。インスタンス変数を定義
        await self.accept()
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.connect_group = self.room_id + 'waiting'
        self.owner = await self._get_room_owner_from_db()
        self.user =  self.scope['user']
        self.intentional_disconnect = False #PlayingRoomに進むときとやHistorybackか、それ以外の切断を区別するため

        #グループ(room_id)についか
        await self.channel_layer.group_add( 
            self.connect_group,
            self.channel_name,
        )

        #temp log
        print(f"USER{self.user}is START WAITING CONNECT!!!!")


        #部屋に入る権限チェック
        in_waiting = await self._is_user_in_waiting_members()
        if (not in_waiting):
            print(f"USER{self.user}is rejected WAITING CONNECT!!!!")
            await self.redirect('/rooms/join')


        # 3.最新のメンバーリストを共有する
        await self.broadcast_members_update()

        #temp log
        waiting_members = await self._get_waiting_members_name()
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is FIN   WAITING CONNECT !!!!{waiting_members},{playing_members}")
        




    #=========接続が切れたとき======================================

    async def disconnect(self, _close_code):
        """
        接続が切れたときのメソッド
        """
        #temp log
        waiting_members = await self._get_waiting_members_name()
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is START WAITING DISCONNECT!!!!{waiting_members},{playing_members}")

        print(f"USER{self.user} when {self.intentional_disconnect}")


        #move_to_playing_roomの場合
        await self._remove_from_waiting_members()

        #部屋にまだ誰かいたら最新のメンバーリストを更新
        waiting_members = await self._get_waiting_members_name()
        if len(waiting_members) >=1:
            await self.broadcast_members_update()


        #接続を切る
        await self.channel_layer.group_discard( # グループからチャンネルを削除
            self.connect_group,
            self.channel_name,
        )

        #temp log
        waiting_members = await self._get_waiting_members_name()
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is FIN   WAITING DISCONNECT!!!!{waiting_members},{playing_members}")
    


    #==========メッセージを受けたとき==============================

    async def receive_json(self, data):
        """ メッセージをjson形式で受け取ったとき、メッセージのtypeに応じて対応する。"""
        message_type = data['type']#命令の種類

        #部屋を閉め切る
        if message_type == 'move_to_playing_room':
            await self.broadcast_move_to_playing_room()







    

    #======以下　外注先関数============================


    #全体に命令送信-----------------

    async def broadcast_members_update(self):
        #temp log
        print(f"USER{self.user}is START ORDER ALL to MEMBER_UPDATE!!!!")

        await self.channel_layer.group_send(
            self.connect_group,
            {
                'type': 'members_update', 
            }
        )
        #temp log
        print(f"USER{self.user}is FIN   ORDER ALL to MEMBER_UPDATE!!!!")




    async def broadcast_move_to_playing_room(self):
        """
        playing_roomに移動命令
        """

        #temp log
        print(f"USER{self.user}is START ORDER ALL to redirect to PLAYING ROOM!!!!")


        owner = await self._get_room_owner_from_db()
        # 命令者が部屋のオーナーかチェック
        if self.user == owner:

            #1.waiting_membersの人間をplaying_membersを設定
            await self._make_playingLst_from_waitingLst()
            print("WAITING_MEMBERs move to PLAYING_MEMBERs!!!!")


            # グループ全員にリダイレクト命令を一斉送信
            await self.channel_layer.group_send(
                self.connect_group,
                {
                    'type': 'move_to_playing_room', # 既存のリダイレクト用ハンドラを再利用
                }
            )

            #temp log
            print(f"USER{self.user}is FIN   ORDER ALL to redirect to PLAYING ROOM!!!!")
            






    #個別命令送信--------------------------


    async def move_to_playing_room(self, event):
        """redirect命令をuserに送信"""
        #意図的な集団切断であると伝える
        self.intentional_disconnect =True

        url = f'/rooms/playing/{self.room_id}' 
        await self.send(text_data=json.dumps({
            'type': 'redirect',
            'url': url
        }))
        print(f"USER{self.user}is send redirect to {url}!!!!")
        



    async def members_update(self, event):
        """waiting_membersの一覧をuserに送信"""
        # イベントからメンバーリストを受け取る
        waiting_members = await self._get_waiting_members_name()
        playing_members = await self._get_playing_members_name()

        # WebSocketを通じてクライアントにメンバーリストを送信する
        await self.send_json({
            'type': 'members_update',
            'waiting_members': waiting_members,
            'playing_members': playing_members,
        })

        print(f"USER{self.user}is send MEMBER UPDATE!!!!")



    async def redirect(self, url):
        """redirect命令をuserに送信"""

        await self.send(text_data=json.dumps({
            'type': 'redirect',
            'url': url
        }))
        print(f"USER{self.user}is send redirect to {url}!!!! in waiting")



    
    #データ更新-----------------------------

    @database_sync_to_async
    def _add_to_waiting_members(self):
        """Userをwaiting_membersに登録する"""
        try:
            room = Room.objects.get(id=self.room_id)
            user = self.user

            if not room.waiting_members.filter(pk=user.pk).exists():
                room.add_waiting_member(user)
        except Room.DoesNotExist:
            pass


    @database_sync_to_async
    def _remove_from_waiting_members(self):
        """Userをwaiting_membersから登録を外す"""
        try:
            # まずルームインスタンスを取得する
            room = Room.objects.get(id=self.room_id)
            user = self.user
            # room_memberフィールドにユーザーを追加する
            if room.waiting_members.filter(pk=user.pk).exists():
                room.remove_waiting_member(user)
                pass
        except Room.DoesNotExist:
            pass




    @database_sync_to_async
    def _make_playingLst_from_waitingLst(self):
        room = Room.objects.get(id=self.room_id)
        room.move_waitingList_to_playingList()



    #データ取得----------------------------------

    @database_sync_to_async
    def _is_user_in_waiting_members(self):
        room = Room.objects.get(id=self.room_id)
        if room.waiting_members.filter(pk=self.user.pk).exists():
            return True
        else:
            return False
        
    @database_sync_to_async
    def _is_user_in_playing_members(self):
        room = Room.objects.get(id=self.room_id)
        if room.playing_members.filter(pk=self.user.pk).exists():
            return True
        else:
            return False

    @database_sync_to_async
    def _get_waiting_members_name(self):
        """現在のwaiting_members一覧をDBから取得する"""
        room = Room.objects.get(id=self.room_id)
        # ユーザー名のリストを返す
        return [user.username for user in room.waiting_members.all()]
    
    @database_sync_to_async
    def _get_playing_members_name(self):
        """現在のwaiting_members一覧をDBから取得する"""
        room = Room.objects.get(id=self.room_id)
        # ユーザー名のリストを返す
        return [user.username for user in room.playing_members.all()]


    @database_sync_to_async
    def _get_room_from_db(self):
        room = Room.objects.get(id=self.room_id)
        return room
    
    @database_sync_to_async
    def _get_room_owner_from_db(self):
        room = Room.objects.get(id=self.room_id)
        return room.owner
    
    

