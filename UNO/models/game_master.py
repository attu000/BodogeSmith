from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from .room import Room
from .card import Card
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
import time
import random
from django.db.models import Case, When 


class GameMaster(models.Model):
    """
    ゲームマスター。ゲーム進行を管理する。
    """

    _game_name  = models.CharField("ゲーム名", max_length=30,default='unknown_game')
    #部屋
    _room = models.ForeignKey(Room, on_delete=models.CASCADE, blank=True, related_name="room_game", verbose_name="部屋")

    #card
    _cards = models.ManyToManyField(Card, blank=True, related_name='game_card', verbose_name='ゲーム内のカード一覧')

    #ターン
    _player_id_order = models.JSONField("プレイヤーの順番", default=list, help_text="プレイヤーのIDを順番に格納したリスト")
    _turn_player_index = models.PositiveIntegerField("現在どのプレイヤーターンかを示すインデックス", default=0)
    _turn_direction = models.IntegerField("ターンの進行方向", choices=[(1,'時計回り'), (-1,'反時計回り') ], default=1 )
    _current_player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="現在のプレイヤー")
    _current_turn_num = models.PositiveIntegerField("現在のターン数", default=0)

    #情報保存
    _action_que = models.JSONField("アクションを保存するキュー", default=list, help_text="カードの効果などをここに蓄積して順番に実行する")
    _game_logger = models.JSONField("ゲーム進行のログを保存するリスト", default=list, help_text="['move_card_fromAtoB|card_id|placeA|placeB|プレイヤーAがカードXを場所Bに移動させました']のように関数名、引数名、説明文を入力する")

    #ゲーム状況
    _place_card_id_dict = models.JSONField("どこにどこカードがあるか", default=dict, help_text="どこにどのカードがあるかを管理するリスト。｛'str(place_name)':[int(card1.id), int(card2.id)...]｝形式")





    # init-------------------------------

    def init_game(self, room):
        """ゲームを初期化する"""
        #データ初期化
        self._room = room
        self._player_id_order.clear()
        self._turn_player_index = 0
        self._turn_direction = 1
        self._current_turn_num = 0
        self._action_que.clear()
        self._game_logger.clear()
        self._place_card_id_dict.clear()

        #roomからplayer.idを取得
        play_member_id = [player.id for player in room.playing_members.all()]

        #プレイヤーターンを決める
        self._player_id_order += play_member_id

        #現在のターンプレイヤーを決める
        current_player_id = self._player_id_order[self._turn_player_index]
        self._current_player = get_object_or_404(get_user_model(), id=current_player_id)

        #カード生成する
        card_id_list = []
        COLOR_CHOICES = ['red','blue','yellow','green']
        RANK_CHOICES = ['0','1','2','3','4','5','6','7','8','9','skip','reverse','draw_two','wild', 'wild_draw_four']
        for rank in RANK_CHOICES:
            if rank in ['wild', 'wild_draw_four']:
                card = Card.objects.create(color='black', rank=rank)
                card_id_list.append(card.id)
            else:
                for color in COLOR_CHOICES:
                    card = Card.objects.create(color=color, rank=rank)
                    card_id_list.append(card.id)

        random.shuffle(card_id_list)



        #カード初期配置を決める
        for player_num,player_id in enumerate(play_member_id):
            self._place_card_id_dict[player_id] = [card_id_list[card_num] for card_num in range(7*player_num , 7*(player_num+1))]
        self._place_card_id_dict['field'] =[7*(player_num+1)]
        self._place_card_id_dict['deck'] =card_id_list[7*(player_num+1)+1 :]

        #game_logger
        self.add_log(f'init|{room}|ゲームを初期化しました')

        self.save()
        print('init DONE!!')



    #---set method-------------



    def move_card_fromAtoB(self, card_id, placeA, placeB):
        #placeAでcardがあるかを探す
        card_id = int(card_id)
        placeA = str(placeA)
        placeB = str(placeB)

        if card_id >=0:
            try:
                target_idx = self._place_card_id_dict[placeA].index(card_id)
            except:
                print(f'{card_id} is not found in {placeA}')
                print(self._place_card_id_dict[placeA])
                return
        
            temp = self._place_card_id_dict[placeA].pop(target_idx)
            self._place_card_id_dict[placeB].append(temp)
            self.save()

        else:
            try:
                temp = self._place_card_id_dict[placeA].pop()
            except:
                print('No more deck')
                return
            self._place_card_id_dict[placeB].append(temp)
            self.save()

        print(self._place_card_id_dict['deck'])
        print(self._place_card_id_dict['field'])


    def shuffle(self,place, direct):
        """
        後で元に戻せるような疑似的なシャッフル。
        direct=1の時
        id=0 -> id=len-1   へ移動
        id=0 -> id=len-3 へ移動
        ...
        id=0 -> id=1

        direct=-1の場合逆の移動となる。
        id=1 -> id=0 ...
        """
        place = str(place)
        direct = int(direct)

        target_list = self._place_card_id_dict[place]
        list_len = len(target_list)
        target_id_list = [0 for _ in range(1, list_len, 2)]#[0,0,0,0...]
        move_id_list = [i for i in range(list_len-1,0, -2)] #[len-1, len-3, ....]


        

        if(direct==-1):
            temp = target_id_list
            move_id_list.reverse()
            target_id_list = move_id_list
            move_id_list = temp

        for _ in range(3):#3回シャッフルする
            for i in range(len(target_id_list)):
                temp = target_list.pop(target_id_list[i])
                target_list.insert(move_id_list[i], temp)


        
        self.save()

        


        

        
    def add_log(self,text):
        self._game_logger.append(text)
        self.save()
        print('add log: ',text)



    
    def rewind(self):
        try:
            log = self._game_logger.pop()
        except:
            print('No log')
            return
        log_list = log.split('|')
        if log_list[0] == 'move_card_fromAtoB':
            card_id = int(log_list[1])
            placeA = log_list[2]
            placeB = log_list[3]
            self.move_card_fromAtoB(card_id, placeB, placeA)
        
        if log_list[0] == 'shuffle':
            place = log_list[1]
            direct = int(log_list[2])*-1
            self.shuffle(place, direct)


    




    #---get_method--------------

    def card_list(self, place):
        """
        場所に応じたカードリストを返す
        return:
        [card_object, card_object, card_object, ....]
        """
        card_id_list = self._place_card_id_dict[place]
        card_list_order = [When(id=id, then=pos) for pos, id in enumerate(card_id_list)]
        card_list = Card.objects.filter(id__in=card_id_list).order_by( Case(*card_list_order) )
        return list(card_list)
    




    def user_status_forJSON(self, user_id):
        """
        ユーザーのHTML上に映し出されるデータを送る
        return:
        
        user_status_dict = {
            'myself':{
                'name':user.name,
                'pk':user.pk,
                'card':[{'pk':card.pk, 'color':card.color, 'rank':card.rank}...]
            }

            'others':[{'name':user.name, 'pk':user.pk, 'card_num':'持っているカードの枚数'}...]

            'field': {'pk':card.pk, 'color':card.color, 'rank':card.rank} #一番上のカード
            'game_status':{
                'log':log[-1]
                }
        }
        """
        
        
        #myself
        myself = {}
        myself['name'] = get_object_or_404(get_user_model(), id=user_id).username
        myself['id'] = user_id

        myself_card = self.card_list(str(user_id))
        myself_card_forJSON = []
        for card in myself_card:
            myself_card_forJSON.append(card.info_dict)
        myself['card'] = myself_card_forJSON

        #others 「自分の次のプレイヤー」からplayer_id_order順に,自分以外を格納する
        others = []
        user_num = len(self._player_id_order)
        idx = self._player_id_order.index(user_id)
        for i in range(user_num-1):
            target_idx = (idx+i+1) % user_num
            target_user_id = self._player_id_order[target_idx]

            user_dict = {}
            user_dict['name'] = get_object_or_404(get_user_model(), id=target_user_id).username
            user_dict['pk'] = target_user_id
            user_dict['card_num'] = len(self._place_card_id_dict[str(target_user_id)])
            others.append(user_dict)

        #field
        card_list = self.card_list('field')
        if len(card_list)>=1:
            field = card_list[-1].info_dict
        else:
            field = None

        #game_status
        game_status = {
            'log':[log.split('|')[-1] for log in self._game_logger]
        }

        #return
        return {'myself':myself, 'others':others, 'field':field, 'game_status':game_status}
    


    #---property-----------------
    @property
    def game_name(self):
        return self._game_name
    

    @property
    def place_card_id_dict(self):
        return self._place_card_id_dict
    
    @property
    def place_card_dict_forJSON(self):
        """
        place_card_dict = {
            'place_name' : [
                                {
                                    'pk': card.pk,
                                    'color': card.color,
                                    ...
                                },

                                {
                                    'pk': card.pk,
                                    'color': card.color,
                                    ...
                                }
                            ]
        }
        """
        places = self._place_card_id_dict.keys()
        print(places)
        place_card_dict = {}
        for place in places:
            card_list = self.card_list(place)
            card_info_list = []
            for card in card_list:
                card_info_list.append(card.info_dict)
            place_card_dict[place] = card_info_list

        return place_card_dict
    


    


            






    

    

















