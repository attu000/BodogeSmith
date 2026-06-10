from django.db import models
from django.conf import settings
from .card import Card
from .field_cardInfo_model import FieldCardInfoModel
from .card_status_for_user_model import CardStatusForUserModel
from .field_card_info_to_send_model import FieldCardInfoToSendModel as FCIToSendModel
from .field_card_design_model import FieldCardDesignModel
from .field_card_info_to_send_model import FieldCardInfoToSendModel
from pydantic import ValidationError
import datetime
import json
import copy
from typing import List, Union

class Game(models.Model):
    """
    実際にプレイするゲームを管理するモデル.GameDesignClassからGameFacotryClassを通して生成される。GameDesignClassのことは参照しない。
    """
    #基本情報
    _name = models.CharField("ゲームの名前", max_length=100)

    # restart時に元のGameDesignを参照するために保持
    _game_design_id = models.IntegerField("元のゲームデザインID", null=True, blank=True)
    _created_at = models.DateTimeField(auto_now_add=True)

    _players = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="joined_games", 
        blank=True, 
        verbose_name="参加メンバー"
    )

    _cards = models.ManyToManyField(
        Card,
        blank=True,
        related_name='game',
        verbose_name='ゲーム内のカード一覧'
    )



    #ゲーム管理情報
    _game_log = models.JSONField(
        "ゲームログ",
        default=list,
        blank=True, 
        help_text="ゲームの操作履歴を [関数名, [引数のリスト], 誰からの指示か(User)、説明文、日時] の形式で保存します。"
    )

    _player_id_order = models.JSONField(
        "_player_id_order",
        default=list,
        blank=True, 
    ) 

    #game状況情報--------------

    _field_cardInfo_dict = models.JSONField(
        "_field_cardInfo_dict:どの場所にどこカードがあるか", 
        default=dict, 
        blank=True,
    )

    _card_status_for_user_dict = models.JSONField(
        "_card_status_for_user_dict:Card一枚一枚のステータスを仮想フィールドごと、ユーザーごとに管理", 
        default=dict, 
        blank=True,
    )

    
    _field_card_design_dict =  models.JSONField(
        "_field_card_design_dict:各仮想フィールドをどのように表示するか", 
        default=dict, 
    )



    #------------------------------------
    # ## _field_card_Info_dict関連 ##
    #------------------------------------
    @property
    def field_cardInfo_cacheobj(self) -> FieldCardInfoModel:
        if not hasattr(self, '_field_cardInfo_cacheobj'):
            self._field_cardInfo_cacheobj = FieldCardInfoModel.parse_obj(self._field_cardInfo_dict)
        return self._field_cardInfo_cacheobj


    def _set_field_cardInfo_cacheobj(self, value: dict):
        if not hasattr(self, '_field_cardInfo_cacheobj'):
            self._field_cardInfo_cacheobj = FieldCardInfoModel.parse_obj(self._field_cardInfo_dict)

        #validation
        try:
            design_model = FieldCardDesignModel.parse_obj(self.field_card_design_dict)
            value = FieldCardInfoModel.model_validate(value, context={'design_model': design_model, 'cards':self._cards})
        except :
            print("_field_cardInfo_cacheobjの更新に失敗しました。")
            raise ValidationError("_field_cardInfo_cacheobjの更新に失敗しました。")
        
        self._field_cardInfo_cacheobj = value
        self.save()


    #-----------------------------------------
    #   card_status_for_usr_dict as 
    #----------------------------------------
    @property
    def card_status_for_user_cacheobj(self) -> CardStatusForUserModel:
        if not hasattr(self, '_fcs_for_user_cacheobj'):
            self._card_status_for_user_cacheobj = CardStatusForUserModel.parse_obj(self._card_status_for_user_dict)
        return self._card_status_for_user_cacheobj


    def _set_card_status_for_user_cacheobj(self, value: dict):
        if not hasattr(self, '_card_status_for_user_cacheobj'):
            self._card_status_for_user_cacheobj = CardStatusForUserModel.parse_obj(self._card_status_for_user_dict)

        #validation
        try:
            value = CardStatusForUserModel.model_validate(value, context={'players': self._players, 'cards':self._cards})
        except:
            print("_card_status_for_user_cacheobjの更新に失敗しました。")
            raise ValidationError("_card_status_for_user_cacheobjの更新に失敗しました。")

        self._card_status_for_user_cacheobj = value
        self.save()



    #save-------------------------------------

    def save(self, *args, **kwargs):
        if hasattr(self, '_card_status_for_user_cacheobj'):
            self._card_status_for_user_dict = self._card_status_for_user_cacheobj.dict()
        if hasattr(self, '_field_cardInfo_cacheobj'):
            self._field_cardInfo_dict = self._field_cardInfo_cacheobj.dict()

        super().save(*args, **kwargs)


    
    #-------------------------------------------------------
    #カードの移動などゲーム上での動作を定義
    #-------------------------------------------------------

    def _get_card_list(self, field_spec: str) -> list[int]:
        """
        Args:
            field_spec (str): 'deck' や 'hand/player_1' のような文字列
        Returns:
            list[int]:対応するカードIDのリストを返す＊参照渡しである。
        """
        cards_model = self.field_cardID
        parts = field_spec.split('/')
        field_name = parts[0]
        
        try:
            if len(parts) == 1:
                # Publicフィールドの場合 (例: 'deck')
                return cards_model.Public[field_name]
            elif len(parts) == 2:
                # Personalフィールドの場合 (例: 'hand/player_1')
                player_id = parts[1]
                return cards_model.Personal[field_name][player_id]
            else:
                raise KeyError()
        except KeyError:
            raise KeyError(f"指定された場所 '{field_spec}' が存在しません。")







    def move_card_fromAtoB(self, card_id:int, from_path:List[Union[str,int]], to_path: List[Union[str,int]]):
        """
        指定された場所間でカードを1枚移動させる。
        
        Args:
            cardID (int): 移動するカードのID。-1の場合、移動元の先頭カードを移動させる。
            from_path (list): 移動元の場所 : 
            to_path (list): 移動先の場所
        """
        from_category = from_path[0]
        from_field_type = from_path[1]
        from_user_id = None
        to_category = to_path[0]
        to_field_type = to_path[1]
        to_user_id = None

        #### field_cardInfo_cacheを変更
        field_cardInfo_dict = self.field_cardInfo_cacheobj.dict()

        #移動元場所特定
        card_info_list = None
        try:
            if from_category=="Personal":
                from_user_id = int(from_path[2])
                card_info_list = field_cardInfo_dict[from_category][from_field_type][from_user_id]

            elif from_category=="Public":
                card_info_list = field_cardInfo_dict[from_category][from_field_type]
        except:
                raise ValueError("指定された場所は存在しませんでした")
        
        
        #Card特定
        indx_to_pop = None
        for indx, card_info_dict in enumerate(card_info_list):
            if card_info_dict['card_id'] == card_id:
                indx_to_pop = indx
                break

        #card_id = -1の場合
        if card_id == -1:
            indx_to_pop = 0
        
        if indx_to_pop is None:
            raise ValueError("指定されたcardは存在しませんでした")
            

        card_info_to_move = card_info_list.pop(indx_to_pop)#参照渡しのためこれでいい



        #移動先場所特定
        target_card_info_list = None
        try:
            if to_category=="Personal":
                to_user_id = int(to_path[2])
                target_card_info_list = field_cardInfo_dict[to_category][to_field_type][to_user_id]

            elif to_category=="Public":
                target_card_info_list = field_cardInfo_dict[to_category][to_field_type]
        except:
                raise ValueError("指定された場所は存在しませんでした")
        
        #移動
        target_card_info_list.append(card_info_to_move)

        #set
        self._set_field_cardInfo_cacheobj(field_cardInfo_dict)



        ### card_status_dictを変更
        card_status_for_user_dict = self.card_status_for_user_cacheobj.dict()
        
        for user_id, card_dict in card_status_for_user_dict['users'].items():
            #Publicの場合、field_card_designのinit_reverseを参照
            if to_category == 'Public':

                #あとでPublicFieldはFieldのみにする
                public_fields = self.field_card_design_dict[to_category][to_field_type].keys()
                target_field = list(public_fields)[0]
                card_dict[card_id]['reverse'] = self.field_card_design_dict[to_category][to_field_type][target_field]['design']['init_reverse']
            
            #Personalの場合、to_user_id==user_idの場合はfield_card_disign_dictのmyself==Trueとなっているfieldのinit_reverseを参照

            if to_category=='Personal':
                if user_id == to_user_id:
                    #myself
                    myself_field_name = [field_name for field_name, field_dict in self.field_card_design_dict[to_category][to_field_type].items() if field_dict['target_player']['myself'] ][0]
                    card_dict[card_id]['reverse'] =self.field_card_design_dict[to_category][to_field_type][myself_field_name]['design']['init_reverse']

                else:
                    others_field_name = [field_name for field_name, field_dict in self.field_card_design_dict[to_category][to_field_type].items() if field_dict['target_player']['others'] ][0]
                    card_dict[card_id]['reverse'] =self.field_card_design_dict[to_category][to_field_type][others_field_name]['design']['init_reverse']


        self._set_card_status_for_user_cacheobj(card_status_for_user_dict)






    def shuffle(self, field: str, direct: int):
        """
        指定された場所のカードを疑似的にシャッフルする。
        
        Args:
            field (str): シャッフルする場所 (例: 'deck', 'hand/player_1')
            direct (int): 1なら正方向、-1なら逆方向にシャッフル。
        """
        cards_model = self.field_cardID #参照渡し
        card_list = self._get_card_list(field) #参照渡し
        
        list_len = len(card_list)
        if list_len < 2:
            return # カードが2枚未満なら何もしない

        if direct == 1:
            # 正方向のシャッフル
            # 行先: len-1, len-3, ..., 1
            for i in range(list_len - 1, 0, -2):
                card = card_list.pop(0)
                card_list.insert(i, card)
        elif direct == -1:
            # 逆方向のシャッフル
            # 移動元: 1, 3, ..., len-1
            for i in range(1, list_len, 2):
                card = card_list.pop(i)
                card_list.insert(0, card)
        else:
            raise ValueError("direct引数は1または-1である必要があります。")

        #変更をセッター経由で反映。参照渡しなのでcacheobjはすでに更新されているが、この行によってDjangoがfield_cardID_isntanceに変更があったことを記録できる。
        # また、一応Setter経由でSetすることで、cacheobj変更時にちゃんとSetterの内容を通過することを保証させ、Setter拡張に備える。
        self._set_field_cardID(cards_model)





    #-----------------------
    # log関連
    #----------------------
    def add_log(self, func:str, args:list[str], userID:int, exp:str):
        """
        Args:
            func(str):実行した関数名
            args(list[str]): 関数に渡した引数
            userID : その関数を実行を命令したUserのID
            exp(str): 何をしたかの説明（自然言語）
        Code：
            game_logに追加
            save()
        """
        # ログエントリを辞書として作成
        # 記録としてタイムスタンプも加える
        log_entry = {
            'func': func,
            'args': args,
            'userID': userID,
            'exp': exp,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        
        # game_logリストに新しいログを追加
        self.game_log.append(log_entry)
        
        # 変更をデータベースに即時保存
        self.save()

    

    def rewind(self):
        """
        ゲームログの最後の操作を取り出し、その逆を実行して状態を巻き戻す。
        """
        # --- 1. 最後のログを取得して、ログリストから削除 ---
        try:
            log = self.game_log.pop()
        except IndexError:
            # ログが空の場合はIndexErrorが発生する
            raise ValueError("ログがありません")
            return

        func = log['func']
        args = log['args']


        # --- 2. 関数名に応じて、逆の操作を実行 ---
        if func == 'move_card_fromAtoB':
            # args は [cardID, from_path, to_path] のはず
            card_id, original_from, original_to = args
            # 移動元と移動先を逆にして、同じカードを移動させる
            self.move_card_fromAtoB(card_id, original_to, original_from)


        elif func == 'shuffle':
            # args は [field, direct] のはず
            field, direction = args
            # シャッフルの方向を逆にする (-1 を掛ける)
            self.shuffle(field, -direction)
            
        else:
            # 未知の操作の場合は、ログを元に戻してエラーを出す
            self.game_log.append(log)
            raise NotImplementedError(f"関数 '{func}' の巻き戻し操作は実装されていません。")

        # --- 3. 状態の変更（カード位置とログ）をデータベースに保存 ---
        self.save()

        




    #--------------------
    #HTMLへの送信
    #-------------------
    def create_fci_for_user_dict(self,user_id:int):
        """
        仮想フィールドごとに送るカード情報
        """

        #category,field_type,fieldなどを与えられたら、送るべき情報を成型してくれる関数
        def create_info_object_to_send(category:str, field_type:str, field:str, user_id:int, field_card_design_dict:dict, card_status_for_user_dict:dict, field_cardInfo_dict:dict):
            #各fieldにて
            # field_card_design_dictを参照して、display_card_maxnumの数以下のカード枚数を取得。
            # その枚数だけcard_info_dictとcard_status_dictをまとめた辞書をリストに格納。
            # ただし、fcs_for_user_dictを参照して、対応するユーザーの辞書内で、対応する各カードが裏面の状態の場合はcard_info_dictは空辞書になる
            # ただし、PersnoalFieldの場合はこれをplayer_fromからplayer_toまで行いuser_idをkeyとした辞書にしてまとめてreturnする。

            #格納するカード上限
            display_card_maxnum = field_card_design_dict[category][field_type][field]["design"]["display_card_maxnum"]

            
            return_info_object = None

            if category=="Personal":
                #return_info_object = Dict{ user_id: List[ Dict{card_info_dict: {},  card_status_dict: {} }]}
                return_info_object = {}
                #誰の情報を格納するのか
                target_player_dict = field_card_design_dict[category][field_type][field]['target_player']

                #どのユーザーの情報を送るか決定
                target_user_id_list = []
                if(target_player_dict['myself']):
                    target_user_id_list.append(user_id)
                if target_player_dict['others']:
                    target_user_id_list += [player_id for player_id in self._player_id_order if player_id != user_id]


                for target_user_id in target_user_id_list:
                    return_info_object[target_user_id] = []
                    #情報を取り出す
                    card_info_list = field_cardInfo_dict[category][field_type][target_user_id][ : display_card_maxnum]
                    #もしカードが裏返しだったら情報を空にする
                    for card_info_dict in card_info_list:
                        card_id = card_info_dict["card_id"]
                        #自分にとってカードがどう見えているか
                        card_status_dict = card_status_for_user_dict['users'][user_id][card_id]
                        
                        card_info_dict_to_send = None
                        if card_status_dict['reverse']==True:
                            card_info_dict_to_send = {key: None for key , _ in card_info_dict.items()}
                            #card_idは渡す
                            card_info_dict_to_send['card_id']=card_info_dict['card_id']
                        else:
                            card_info_dict_to_send = card_info_dict
                        return_info_object[target_user_id].append({'card_info_dict':card_info_dict_to_send, 'card_status_dict':card_status_dict})



            elif category=="Public":
                #return_info_object = List[ Dict{card_info_dict: {},  card_status_dict: {} }]
                return_info_object = []

                card_info_list = field_cardInfo_dict[category][field_type][ : display_card_maxnum]
                for card_info_dict in card_info_list:
                    card_id = card_info_dict["card_id"]
                    card_status_dict = card_status_for_user_dict['users'][user_id][card_id]

                    card_info_dict_to_send = None
                    if card_status_dict['reverse']==True:
                        card_info_dict_to_send = {key: None for key , _ in card_info_dict.items()}
                        #card_idは渡す
                        card_info_dict_to_send['card_id']=card_info_dict['card_id']
                    else:
                        card_info_dict_to_send = card_info_dict
                    return_info_object.append({'card_info_dict':card_info_dict_to_send, 'card_status_dict':card_status_dict})
            print(f"return_object:/n{category},{field_type},{field},{user_id}:\n", return_info_object)
            return return_info_object


        ###　メインロジック----------
        # Getter
        field_card_design_dict = self.field_card_design_dict
        card_status_for_user_dict = self.card_status_for_user_cacheobj.dict()
        field_cardInfo_dict = self.field_cardInfo_cacheobj.dict()
        
        # 辞書の枠組みを作る 
        # Dict{ category_name: 
        #      Dict{ field_type_name: 
        #           Dict{ field_name: 
        #               Dict{ player_id:　←Personalの時のみユーザー辞書を追加
        #                   List[ 
        #                     Dict{
        #                         card_info_dict: CardInfoDict,  
        #                         card_status_dict:CardStatusDict} 
        #                      ]}}}}
        dict_to_send = {}

        #category
        for category_name, field_type_dict  in field_card_design_dict.items():
            dict_to_send[category_name] = {}
            #field_type
            for field_type_name , field_dict in field_type_dict.items():
                dict_to_send[category_name][field_type_name] = {}
                #field
                for field_name , field_info in field_dict.items():
                    info_object_to_send = create_info_object_to_send(category_name, field_type_name, field_name, user_id, field_card_design_dict, card_status_for_user_dict, field_cardInfo_dict)
                    dict_to_send[category_name][field_type_name][field_name] = info_object_to_send

        
        print("dict_to_send",dict_to_send)
        
        
        try:
            model_to_send = FieldCardInfoToSendModel.model_validate(dict_to_send)
        except:
            raise ValueError("FieldCardInfoToSendModelオブジェクトの生成失敗")
        

        return model_to_send.dict()







    #-----------------------------------------
    #GameFactory内初期化関連メソッド
    #----------------------------------------
    def initialize_game_info(self, cards, players, init_card_info_model: FieldCardInfoModel):
        """
        プレイヤー情報と初期カード情報モデルを使って、
        field_cardInfo の状態を初期化する。
        """
         #### ManytoManyField設定するためいったん保存
        self.save()

        #### _players
        self._players.set(players)

        #### _cards
        self._cards.set(cards)

        #### _player_id_order
        self._player_id_order = [player.id for player in players]
        #### 




        ####field_cardInfo_dict--------
        # Personalフィールドをプレイヤーごとに初期化
        for field_type in self._field_card_design_dict.get('Personal', {}):
            init_card_info_model.Personal[field_type] = {
                player.id: [] for player in players
            }
        # Setter
        self._set_field_cardInfo_cacheobj(init_card_info_model)


        #### card_status_for_user_dict------------
        #カードid：それが初期に入っているPublicFieldのinit_reverce　　の逆引き辞書を作る
        card_id_reverse_dict = {}
        field_cardInfo_dict = self.field_cardInfo_cacheobj.dict()
        for field_type_name, card_info_list in field_cardInfo_dict["Public"].items():
            for card_info in card_info_list:
                card_id = card_info['card_id']
                #今のところPublicにはfiledは一つだけなので
                field_names = self.field_card_design_dict['Public'][field_type_name].keys()
                field_name = list(field_names)[0]
                is_reverse = self.field_card_design_dict['Public'][field_type_name][field_name]['design']['init_reverse']
                card_id_reverse_dict[card_id] = {"reverse":is_reverse}

        print("card_id_reverse_dict",card_id_reverse_dict)
        #これを人数分コピーして辞書にする
        card_status_for_user_dict = {
            player.id : copy.deepcopy(card_id_reverse_dict) for player in players
        }

        print("card_status_for_user_dict", card_status_for_user_dict)
        card_status_for_user_dict = {"users": card_status_for_user_dict}
        #Setter
        self._set_card_status_for_user_cacheobj(card_status_for_user_dict)


        self.save()







    def restart(self, game_design_id: int = None):
        """
        ゲームを指定したGameDesign（省略時は同じDesign）の初期状態に完全リセットする。
        """
        from .game_design import GameDesign

        if game_design_id is not None:
            self._game_design_id = game_design_id

        if self._game_design_id is None:
            raise ValueError("このゲームにはGameDesignIDが設定されていません。")

        game_design = GameDesign.objects.filter(pk=self._game_design_id).first()
        if game_design is None:
            raise ValueError(f"GameDesign(id={self._game_design_id})が見つかりません。")

        # ログをリセット
        self._game_log = []

        # cacheobjを破棄して再初期化が走るようにする
        for attr in ('_field_cardInfo_cacheobj', '_card_status_for_user_cacheobj'):
            if hasattr(self, attr):
                delattr(self, attr)

        # field_card_designをGameDesignから再コピー
        self._field_card_design_dict = game_design.field_card_design_cacheobj.dict()

        # initialize_game_infoで全状態を再構築
        cards = game_design.cards
        players = self._players.all()
        init_card_info_model = game_design.init_field_cardInfo_cacheobj.copy(deep=True)
        self.initialize_game_info(cards, players, init_card_info_model)


    #--------------------------------------
    #その他property
    #-------------------------------------
    @property
    def field_card_design_dict(self):
        return self._field_card_design_dict

        

