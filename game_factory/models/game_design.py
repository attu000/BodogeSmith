from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from .room import Room
from .card import Card
from .field_card_design_model import FieldCardDesignModel, VirtualPersonalFieldModel, VirtualPublicFieldModel
from .field_cardInfo_model import FieldCardInfoModel, CardInfoModel
from pydantic import ValidationError






class GameDesign(models.Model):

    #基本情報
    _name = models.CharField("ゲームの名前", max_length=100, unique=True)
    _creater = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="created_game_designs", 
        verbose_name="作成者"
    )
    _created_at = models.DateTimeField(auto_now_add=True)
    #ステータス
    _published = models.BooleanField("公開状態", default=False)

    #ゲーム情報
    _cards = models.ManyToManyField(
        Card,
        blank=True,
        related_name='gamedesign',
        verbose_name='ゲーム内のカード一覧'
    )

    _player_limit = models.IntegerField(
    "プレイヤー上限",
    default=10,
    validators=[MinValueValidator(1)],
    help_text="ゲームに参加できるプレイヤーの上限人数を設定します。"
    ) 

    #情報更新はcacheobjの情報を更新してsave()すること。直接書き換えはできない。
    _field_card_design_dict =  models.JSONField(
        "各場所をどのように表示するか", 
        default=dict, 
        help_text="これは基本的に変更しない。HTMLに送るだけ。"
    )

    #情報更新はcacheobjの情報を更新してsave()すること。直接書き換えはできない。
    _init_field_cardInfo_dict = models.JSONField(
        "初期で各カードがどのPublicFieldに存在するかの辞書",
        default=dict, 
    )







    #----------------------------------
    # ▼▼ field_card_design_dict構築 ▼▼ 
    #_field_card_design_dict: JSONfieldで保存してある
    #_field_card_design_cacheobj: FieldCardDesignModelオブジェクトで保存してある。キャッシュである。
    #------------------------------------
    @property
    def field_card_design_cacheobj(self) -> FieldCardDesignModel:
        """PydanticモデルとしてJSONデータを取得する (GETTER)"""
        # まだ、self._field_card_design_dictの中身が存在しない場合の時のみ、FieldCardDesignModelでオブジェクトを生成し、cacheobjというキャッシュに入れる。
        if not hasattr(self, '_field_card_design_cacheobj'):
            self._field_card_design_cacheobj = FieldCardDesignModel.parse_obj(self._field_card_design_dict)
        return self._field_card_design_cacheobj
    

    #一部を変更してもバリデーターが走らないのでSetterを使って全体を更新する必要あり。
    def _set_field_card_design_cacheobj(self, value: dict):
        if not hasattr(self, '_field_card_design_cacheobj'):
            self._field_card_design_cacheobj = FieldCardDesignModel.parse_obj(self._field_card_design_dict)
        value = FieldCardDesignModel.model_validate(value)
        self._field_card_design_cacheobj = value

    
    #----------------------------------
    # ▼▼ init_field_cardID_dict構築 ▼▼ 
    #_init_field_card_dict: JSONfieldで保存してある
    #_init_field_card_cacheobj: FieldCardDesignModelオブジェクトで保存してある。キャッシュである。
    #------------------------------------

    @property
    def init_field_cardInfo_cacheobj(self) -> FieldCardInfoModel:
        """PydanticモデルとしてJSONデータを取得する (GETTER)"""
        # まだ、self._field_card_design_dictの中身が存在しない場合の時のみ、FieldCardDesignModelでオブジェクトを生成し、cacheobjというキャッシュに入れる。
        if not hasattr(self, '_init_field_cardInfo_cacheobj'):
            self._init_field_cardInfo_cacheobj = FieldCardInfoModel.parse_obj(self._init_field_cardInfo_dict)
        return self._init_field_cardInfo_cacheobj
    
    #一部を変更してもバリデーターが走らないのでSetterを使って全体を更新する必要あり。
    def _set_init_field_cardInfo_cacheobj(self, value: dict):
        if not hasattr(self, '_init_field_cardInfo_cacheobj'):
            self._init_field_cardInfo_cacheobj = FieldCardInfoModel.parse_obj(self._init_field_cardInfo_dict)
        value = FieldCardInfoModel.model_validate(value)
        self._init_field_cardInfo_cacheobj = value
        self.save()
        

    

    #save()--------------------


    def save(self, *args, **kwargs):
        # 保存する直前に、Pydanticオブジェクトから辞書データへ一度だけ同期する
        if hasattr(self, '_field_card_design_cacheobj'):
            self._field_card_design_dict = self._field_card_design_cacheobj.dict()

        if hasattr(self, '_init_field_cardInfo_cacheobj'):
            self._init_field_cardInfo_dict = self._init_field_cardInfo_cacheobj.dict()
        
        super().save(*args, **kwargs)





    # ------------------------------------------------------------------
    # ▼▼ フィールドを安全に操作するための専用メソッド ▼▼
    # ------------------------------------------------------------------

    def add_personal_field_type(self, field_type: str):
        """
        Personalフィールド種類を適切な初期値で追加する。
        """
        #Getterでfield_card_designとinit_field_cardInfoのキャッシュを呼び出す
        design_dict = self.field_card_design_cacheobj.dict()
        cardInfo_dict = self.init_field_cardInfo_cacheobj.dict()
        
        #field_card_designに新しいフィールド種類を登録
        design_dict["Personal"][field_type] = {}
        self._set_field_card_design_cacheobj(design_dict) # SETTERを呼び出し

        #field_card_Infoに新しいフィールド種類を登録
        cardInfo_dict["Personal"][field_type] = {}

        #フィールド種類が一致しているかの検証
        cardInfo_model = FieldCardInfoModel.model_validate(
            cardInfo_dict,
            context={'design_model': self.field_card_design_cacheobj}
        )
        self._set_init_field_cardInfo_cacheobj(cardInfo_model) # SETTERを呼び出し
        self.save()





    def add_public_field_type(self, field_type: str):
        """
        Publicフィールドを適切な初期値で追加する。
        """
        #Getterでfield_card_designとinit_field_cardInfoのキャッシュを呼び出す
        design_dict = self.field_card_design_cacheobj.dict()
        cardInfo_dict = self.init_field_cardInfo_cacheobj.dict()
        
        #field_card_designに新しいフィールド種類を登録
        design_dict["Public"][field_type] = {}
        self._set_field_card_design_cacheobj(design_dict)# SETTERを呼び出し



        #field_card_Infoに新しいフィールド種類を登録
        cardInfo_dict["Public"][field_type] = []
        #フィールドが一致しているかの検証
        cardInfo_model = FieldCardInfoModel.model_validate(
            cardInfo_dict,
            context={'design_model': self.field_card_design_cacheobj}
        )
        self._set_init_field_cardInfo_cacheobj(cardInfo_model)# SETTERを呼び出し
        self.save()





    def add_virtual_personal_field(self, field_type:str, field_name: str,  target_player:dict):
        """
        Personalフィールドを適切な初期値で追加する。
        """
        # field_card_designのキャッシュをGetter呼び出し
        design_model = self.field_card_design_cacheobj   
            
        new_field = VirtualPersonalFieldModel(
            target_player = target_player
        )
        design_model.Personal[field_type][field_name] = new_field
        self._set_field_card_design_cacheobj(design_model.model_dump()) # SETTERを呼び出し
        self.save()





    def add_virtual_public_field(self, field_type:str, field_name: str):
        """
        Publicフィールドを適切な初期値で追加する。
        """
        design_model = self.field_card_design_cacheobj
        
        new_field = VirtualPublicFieldModel()
        design_model.Public[field_type][field_name] = new_field
        
        self._set_field_card_design_cacheobj(design_model.model_dump())# SETTERを呼び出し
        self.save()





    def update_virtual_field(self, category_name: str, field_type:str, field_name: str, field_data: dict):
        """
        指定されたカテゴリとフィールド名のフィールド情報を、新しいデータで再帰的に更新する。

        Args:
            category_name (str): 'Personal' または 'Public'。
            fielt_type(str): フィールド種類名
            field_name (str): 更新対象の仮想フィールド名。
            field_data (dict): 更新したい情報を含む辞書。
                                (例: {'design': {'position': [10, 20]}})

        Raises:
            KeyError: 指定されたカテゴリやフィールド名が存在しない場合。
            ValueError: Pydanticのバリデーションに失敗した場合。
        """
        design_model = self.field_card_design_cacheobj

        # 1. 更新対象のフィールドモデルを取得
        if category_name == 'Personal' and field_name in design_model.Personal[field_type]:
            target_field = design_model.Personal[field_type][field_name]
            FieldModelClass = VirtualPersonalFieldModel
        elif category_name == 'Public' and field_name in design_model.Public[field_type]:
            target_field = design_model.Public[field_type][field_name]
            FieldModelClass = VirtualPublicFieldModel
        else:
            raise KeyError(f"カテゴリ '{category_name}' にフィールド '{field_name}' は存在しません。")

        # 2. 既存のデータを辞書に変換
        existing_data = target_field.dict()

        # 3. 既存データに新しいデータを再帰的にマージする
        def recursive_update(original, new):
            for key, value in new.items():
                if isinstance(value, dict) and (key in original) and isinstance(original[key], dict):
                    recursive_update(original[key], value)
                else:
                    original[key] = value
            return original

        updated_data = recursive_update(existing_data, field_data)

        try:
            # 4. マージ後のデータで新しいPydanticモデルインスタンスを作成（ここで検証が走る）
            updated_field = FieldModelClass.parse_obj(updated_data)

            # 5. 更新したインスタンスで元のモデルを置き換え
            if category_name == 'Personal':
                design_model.Personal[field_type][field_name] = updated_field
            else: # Public
                design_model.Public[field_type][field_name] = updated_field
            
            self._set_field_card_design_cacheobj(design_model.model_dump())  # SETTERを呼び出し
            self.save()

        except ValidationError as e:
            raise ValueError(f"'{field_name}' の更新に失敗しました: {e}")



    #----------------------------------------
    #published
    #----------------------------------------

    def publish(self):
        self._published = True
        self.save()

    def unpublish(self):
        self._published = False
        self.save()

    #-------------------------------------------
    #Card 追加
    #-------------------------------------------

    def add_card(self, card: Card):
        self._cards.add(card)
        self.save()



    def remove_card(self, card: Card):
        self._cards.remove(card)
        self.save()




    def register_cardInfo_to_public(self, card_id: int, field_type: str):
        card = Card.objects.filter(id=card_id).first()
        if card is None:
            raise ValueError(f"カードID '{card_id}' は存在しません。")
        init_field_cardInfo = self.init_field_cardInfo_cacheobj 
        if field_type not in init_field_cardInfo.Public:
            raise ValueError(f"Publicフィールド '{field_type}' は存在しません。")
        new_card_info = CardInfoModel(**card.to_dict())
        
        init_field_cardInfo.Public[field_type].append(new_card_info)
        self._set_init_field_cardInfo_cacheobj(init_field_cardInfo.model_dump()) # Setter呼び出し
        self.save()




    #---------------------------------
    # その他set, get　property
    #--------------------------------

    def to_dict(self):
        """
        GameDesignの現在の状態を包括的な辞書として返す
        """
        # 1. カードIDから所属フィールド名を引くための逆引きマップを作成。
        #    例: {101: ('Deck',), 102: 'Deck', 103: 'DiscardPile'}
        card_location_map = {}
        #いったん辞書にする
        init_publicField_cardInfo = self.init_field_cardInfo_cacheobj.dict().get('Public', {}) # {field_type:[{card_id: card_name, card_url}...]}
        for public_field_type, card_info_list in init_publicField_cardInfo.items():
            for card_info in card_info_list:
                card_location_map[card_info['card_id']] = public_field_type

        cards_list = [
            {'id': card.id, 
             'name': card.name, 
             'image_url': card.image.url,
             'initial_field': card_location_map.get(card.id, None)
             }
            for card in self.cards
        ]
        return {
            'id': self.id,
            'name': self.name,
            'player_limit': self.player_limit,
            'published': self.published,
            'cards': cards_list,
            'field_card_design': self.field_card_design_cacheobj.dict(),
            'init_field_cardInfo': self.init_field_cardInfo_cacheobj.dict(),
            'creater': self.creater.username
        }

    
    @property
    def cards(self):
        return self._cards.all()

    @property
    def name(self):
        return self._name
    
    @property
    def player_limit(self):
        return self._player_limit
    
    @property
    def published(self):
        return self._published

    @property
    def creater(self):
        return self._creater

    @property
    def created_at(self):
        return self._created_at