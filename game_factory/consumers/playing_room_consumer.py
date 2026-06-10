import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer 

from ..models.room import Room
from ..models.game_factory import GameFactory

import re

class GameFactoryPlayingRoomConsumer(AsyncJsonWebsocketConsumer):
    groups = ['broadcast']


    #=======接続したとき====================================

    async def connect(self):
        
        """
        WebSocket接続がリクエストされたときに呼び出される非同期メソッド
        """
        #0.接続を許可。インスタンス変数を定義
        await self.accept()

        #メンバ変数
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.connect_group = 'game_factory_' + self.room_id + '_playing'
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

        #Game登録してあるならばそれを表示
        room_game = await self._get_room_game_from_db()
        if room_game:
            await  self._broadcast_field_card_design_update()
            await  self._broadcast_field_cardInfo_update()



        #temp log
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is FIN   playing CONNECT !!!!,{playing_members}")
        




    #=========接続が切れたとき======================================

    async def disconnect(self, _close_code):
        """
        接続が切れたときのメソッド
        """
        #temp log
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is START playing DISCONNECT!!!!,{playing_members}")

        

        #接続を切る
        await self.channel_layer.group_discard( # グループからチャンネルを削除
            self.connect_group,
            self.channel_name,
        )

        #temp log
        playing_members = await self._get_playing_members_name()
        print(f"USER{self.user}is FIN   playing DISCONNECT!!!!,{playing_members}")
    


    #==========メッセージを受けたとき==============================

    async def receive_json(self, data):
        """ メッセージをjson形式で受け取ったとき、メッセージのtypeに応じて対応する。"""
        message_type = data['type']#命令の種類

        #gameを選択時
        if message_type=='game_choice':
            #本来はgame_design_idが送られてきて、GameFactoryからGameを作り、roomに登録し、更新されたfield_card_designをブロードキャストする。
            #今はまだ、仮のJSONを送るだけにする
            await self._create_and_set_game_from_design(data['game_design_id'])
            await self._broadcast_field_card_design_update()
            await self._broadcast_field_cardInfo_update()

        #ゲーム内の動作
        elif message_type=='move_card':
            card_id = data['card_id']
            from_path = data['from_path']
            to_path = data["to_path"]

            await self._move_card_fromAtoB(card_id, from_path, to_path)
            await self._broadcast_field_card_design_update()
            await self._broadcast_field_cardInfo_update()
            

        elif  message_type=='shuffle':
            print('shuffle')
            place = data['place'] if data['place']!= 'myself' else self.user.id
            direct = data['direct']
            await self._shuffle(place, direct)
            await self._add_log(f'shuffle|{place}|{direct}|プレイヤー{self.user}が{place}をシャッフル')



        elif message_type=='rewind':
            print('rewind')
            await self._rewind()

        
        elif message_type=='restart':
            print('restart')
            await self._init_game()


        







    

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




    async def _broadcast_field_card_design_update(self):
        #temp log
        print(f"USER{self.user}is START ORDER ALL to send field_card_design!!!!")
        await self.channel_layer.group_send(
            self.connect_group,
            {
                'type': 'field_card_design_update', 
            }
        )
        #temp log
        print(f"USER{self.user}is FIN   ORDER ALL to send field_card_design!!!!")




    async def _broadcast_field_cardInfo_update(self):
        #temp log
        print(f"USER{self.user}is START ORDER ALL to send field_cardInfo!!!!")
        await self.channel_layer.group_send(
            self.connect_group,
            {
                'type': 'field_cardInfo_update', 
            }
        )
        #temp log
        print(f"USER{self.user}is FIN   ORDER ALL to send field_cardInfo!!!!")





    #個別命令送信--------------------------

    async def redirect(self,event):
        """redirect命令をuserに送信"""

        url = event['url']
        await self.send(text_data=json.dumps({
            'type': 'redirect',
            'url': url
        }))
        print(f"USER{self.user} send redirect to {url}!!!! in playing")






    async def field_card_design_update(self,event):
        """ゲームデザイン更新をuserに送信"""

        # 仮の送るデータ
        field_card_design_dict = await self._get_field_card_design_dict_from_db()

        await self.send(text_data=json.dumps({
            'type': 'field_card_design_update',
            'field_card_design':field_card_design_dict,
        }))
        print(f"USER{self.user} send update field_card_design!!!!")




    async def field_cardInfo_update(self,event):
        """ゲーム情報（cardID,URLなど）をuserに送信"""

        field_cardInfo_dict= await self._get_fci_dict_for_user_from_db(self.user.id)

        await self.send(text_data=json.dumps({
            'type': 'field_cardInfo_update',
            'field_cardInfo':field_cardInfo_dict,
        }))
        print(f"USER{self.user} send update field_cardInfo!!!!")

        


    
    #データ更新-----------------------------

    @database_sync_to_async
    def _add_to_playing_members(self):
        """Userをplaying_membersに登録する"""
        try:
            room = Room.objects.filter(id=self.room_id).first()
            user = self.user

            if not room.playing_members.filter(pk=user.pk).exists():
                room.add_playing_member(user)
        except Room.DoesNotExist:
            pass




    @database_sync_to_async
    def _move_card_fromAtoB(self,card_id, from_path, to_path):
        '''カードの場所を変更する'''
        print(card_id, from_path, to_path)
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            room.game.move_card_fromAtoB(card_id, from_path, to_path)


    @database_sync_to_async
    def _shuffle(self, place, direct):
        """シャッフルする"""
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            room.game.shuffle(place, direct)


    @database_sync_to_async
    def _add_log(self,text):
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            room.game.add_log(text)


    @database_sync_to_async
    def _rewind(self):
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            room.game.rewind()




    #ゲーム作成---------------------------------
    @database_sync_to_async
    def _create_and_set_game_from_design(self,game_design_id):
        print(f"USER{self.user} START CREATE AND SET GAME!!!!")
        room = Room.objects.filter(id=self.room_id).first()
        GameFactory.create_and_set_game(game_design_id, room)




    #データ取得----------------------------------

    # room関連情報
    @database_sync_to_async
    def _get_room_from_db(self):
        room = Room.objects.filter(id=self.room_id).first()
        return room


    @database_sync_to_async
    def _is_user_in_playing_members(self):
        room = Room.objects.filter(id=self.room_id).first()
        if room.playing_members.filter(pk=self.user.pk).exists():
            return True
        else:
            return False
        

    @database_sync_to_async
    def _get_playing_members_name(self):
        """現在のplaying_members一覧をDBから取得する"""
        room = Room.objects.filter(id=self.room_id).first()
        # ユーザー名のリストを返す
        return [user.username for user in room.playing_members.all()]


    @database_sync_to_async
    def _get_room_owner_from_db(self):
        room = Room.objects.filter(id=self.room_id).first()
        return room.owner
    

    @database_sync_to_async
    def _get_room_game_from_db(self):
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            return room.game
        else:
            return None

    
    #game関連情報--------

    @database_sync_to_async
    def _get_field_card_design_dict_from_db(self):
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            field_card_design_dict = room.game.field_card_design_dict
            return field_card_design_dict
        else:
            return None
     

    @database_sync_to_async
    def _get_field_cardInfo_dict_from_db(self):
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            field_card_design_dict = room.game.field_cardInfo_cacheobj.dict()
            return field_card_design_dict
        else:
            return None
        
    @database_sync_to_async
    def _get_fci_dict_for_user_from_db(self,user_id):
        room = Room.objects.select_related('_game').filter(id=self.room_id).first()
        if  room and room.game:
            fci_for_user_dict = room.game.create_fci_for_user_dict(user_id)
            print("fci:",fci_for_user_dict)
            return fci_for_user_dict
        else:
            return None



