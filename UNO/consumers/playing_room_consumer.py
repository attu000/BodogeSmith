import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from ..models.room import Room
import re

class PlayingRoomConsumer(AsyncJsonWebsocketConsumer):
    groups = ['broadcast']


    #=======接続したとき====================================

    async def connect(self):
        
        """
        WebSocket接続がリクエストされたときに呼び出される非同期メソッド
        """
        #0.接続を許可。インスタンス変数を定義
        await self.accept()
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_game = await self._get_room_game_from_db()
        self.connect_group = self.room_id + 'playing'
        self.owner = await self._get_room_owner_from_db()
        self.user =  self.scope['user']
        

        await self.channel_layer.group_add( 
            self.connect_group,
            self.channel_name,
        )

        #temp log
        print(f"USER{self.user}is START playing CONNECT!!!!")



        #もしplaying_membersにいなかったらjoinへ
        if not await self._is_user_in_playing_members():
            await self.broadcast_redirect('/rooms/join')
            print(f"USER{self.user}is rejected PLAYING CONNECT!!!!")

        
        # 3.最新のgame_statusを共有する
        await self.broadcast_game_status_update()


        #temp log
        waiting_members = await self._get_waiting_members_name()
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is FIN   playing CONNECT !!!!{waiting_members},{playing_members}")
        




    #=========接続が切れたとき======================================

    async def disconnect(self, _close_code):
        """
        接続が切れたときのメソッド
        """
        #temp log
        waiting_members = await self._get_waiting_members_name()
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is START playing DISCONNECT!!!!{waiting_members},{playing_members}")



        
        #オーナーの切断の時は部屋を占めて、皆にredirectして、自分もmemberから消える
        playing_members = await self._get_playing_members_name()
        
        if self.user.id == self.owner.id:
            if len(playing_members) >=2:
                #temp
                pass
                #await self.broadcast_redirect('/rooms/join')
            #temp htmlのtest用にremoveしないようにする
           ##await self._clear_playing_members()

        #接続を切る
        await self.channel_layer.group_discard( # グループからチャンネルを削除
            self.connect_group,
            self.channel_name,
        )

        #temp log
        waiting_members = await self._get_waiting_members_name()
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is FIN   playing DISCONNECT!!!!{waiting_members},{playing_members}")
    


    #==========メッセージを受けたとき==============================

    async def receive_json(self, data):
        """ メッセージをjson形式で受け取ったとき、メッセージのtypeに応じて対応する。"""
        message_type = data['type']#命令の種類

        if message_type=='move_card':
            print(data['card_info'])
            data_list = data['card_info'].split('|')
            card_id = data_list[1]
            card_rank = data_list[2]
            card_color = data_list[3]
            origin_place = data['origin_place'] if data['origin_place']!= 'myself' else self.user.id
            target_place = data['target_place'] if data['target_place']!= 'myself' else self.user.id

            await self._move_card_fromAtoB(card_id, origin_place, target_place)
            await self.broadcast_game_status_update()
            await self._add_log(f'move_card_fromAtoB|{card_id}|{origin_place}|{target_place}|プレイヤー{self.user}がカード:{card_rank}_{card_color}を{origin_place}から{target_place}に移動。')

        elif  message_type=='shuffle':
            print('shuffle')
            place = data['place'] if data['place']!= 'myself' else self.user.id
            direct = data['direct']
            await self._shuffle(place, direct)
            await self.broadcast_game_status_update()
            await self._add_log(f'shuffle|{place}|{direct}|プレイヤー{self.user}が{place}をシャッフル')



        elif message_type=='rewind':
            print('rewind')
            await self._rewind()
            await self.broadcast_game_status_update()

        
        elif message_type=='restart':
            print('restart')
            await self._init_game()
            await self.broadcast_game_status_update()

        







    

    #======以下　外注先関数============================

    #全体命令送信--------------------------
    async def broadcast_redirect(self,url):
        #temp log
        print(f"USER{self.user}is START ORDER ALL to redirect to {url}!!!!")

        await self.channel_layer.group_send(
            self.connect_group,
            {
                'type': 'redirect', 
                'url':url,
            }
        )
        #temp log
        print(f"USER{self.user}is FIN   ORDER ALL to redirect to {url}!!!!")





    async def broadcast_game_status_update(self):
        #temp log
        print(f"USER{self.user}is START ORDER ALL to update game status!!!!")

        await self.channel_layer.group_send(
            self.connect_group,
            {
                'type': 'game_status_update', 
            }
        )
        #temp log
        print(f"USER{self.user}is FIN   ORDER ALL to update game status!!!!")



    #個別命令送信--------------------------



    async def redirect(self,event):
        """redirect命令をuserに送信"""

        url = event['url']
        await self.send(text_data=json.dumps({
            'type': 'redirect',
            'url': url
        }))
        print(f"USER{self.user} send redirect to {url}!!!! in playing")




    async def game_status_update(self,event):
        """ゲーム内容更新をuserに送信"""

        user_status_dict = await self._get_user_status_dict_from_db(self.user.id)

        await self.send(text_data=json.dumps({
            'type': 'game_status_update',
            'user_status_dict':user_status_dict,

        }))
        print(f"USER{self.user} send update game status!!!!")


    
    #データ更新-----------------------------

    @database_sync_to_async
    def _add_to_playing_members(self):
        """Userをplaying_membersに登録する"""
        try:
            room = Room.objects.get(id=self.room_id)
            user = self.user

            if not room.playing_members.filter(pk=user.pk).exists():
                room.add_playing_member(user)
        except Room.DoesNotExist:
            pass


    @database_sync_to_async
    def _remove_from_playing_members(self):
        """Userをplaying_membersから登録を外す"""
        try:
            # まずルームインスタンスを取得する
            room = Room.objects.get(id=self.room_id)
            user = self.user
            # room_memberフィールドにユーザーを追加する
            if room.playing_members.filter(pk=user.pk).exists():
                room.remove_playing_member(user)
                pass
        except Room.DoesNotExist:
            pass



    @database_sync_to_async
    def _clear_playing_members(self):
        '''playing_membersを空にする'''
        room = Room.objects.get(id=self.room_id)
        room.clear_playing_members()



    @database_sync_to_async
    def _move_card_fromAtoB(self,card_id, placeA, placeB):
        '''カードの場所を変更する'''
        self.room_game.move_card_fromAtoB(card_id, placeA, placeB)


    @database_sync_to_async
    def _shuffle(self, place, direct):
        """シャッフルする"""
        self.room_game.shuffle(place, direct)


    @database_sync_to_async
    def _add_log(self,text):
        self.room_game.add_log(text)


    @database_sync_to_async
    def _rewind(self):
        self.room_game.rewind()

    
    @database_sync_to_async
    def _init_game(self):
        room = Room.objects.get(id=self.room_id)
        self.room_game.init_game(room)



    #データ取得----------------------------------

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
    
    @database_sync_to_async
    def _get_room_game_from_db(self):
        room = Room.objects.get(id=self.room_id)
        return room.room_game.all()[0]
    
    
    @database_sync_to_async
    def _get_user_status_dict_from_db(self, user_id):
        room = Room.objects.get(id=self.room_id)
        self.room_game = room.room_game.all()[0]
        return self.room_game.user_status_forJSON(user_id)
        


