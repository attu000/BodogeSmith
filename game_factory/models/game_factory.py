from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from .room import Room
from .card import Card
from .game_design import GameDesign
from .game import Game
from pydantic import ValidationError







class GameFactory:
    """
    GameDesignとRoomの情報から、新しいGameインスタンスを生成するためのファクトリクラス。
    """
    @classmethod
    def create_and_set_game(self, game_design_id: int, room: Room) -> Game:
        """
        指定されたゲームデザインとルームから、ゲームインスタンスを生成し、
        データベースに保存して返します。

        Args:
            game_design (GameDesign): ゲームの設計図となるインスタンス。
            room (Room): ゲームが開催される部屋のインスタンス。

        Returns:
            Game: 新しく生成・保存されたゲームのインスタンス。
            _name,  _players, _cards, _field_cardInfo_dict, _field_card_design_dictが必要。
        """
        #元となるデザイン取得
        game_design = GameDesign.objects.filter(pk=game_design_id).first()
        if not game_design:
            raise ValueError(f"指定されたID({game_design_id})のゲームデザインが見つかりません。")


        # 上限よりも多かったらエラー
        if game_design.player_limit < room.playing_members.count():
            raise ValueError("プレイヤー数が上限を超えています。")
        

        # --- 1. Gameインスタンスの基本情報を作成 ---
        #GameObject生成
        field_card_design_dict = game_design.field_card_design_cacheobj.dict()
        game = Game(
            _name=game_design.name,
            _field_card_design_dict=field_card_design_dict,
            _game_design_id=game_design.id,
        )

        # --- 2. そのほか必要情報を要件に従って構築 ---
        field_cardInfo_cacheobj = game_design.init_field_cardInfo_cacheobj.copy(deep=True)
        players = room.playing_members.all()
        cards = game_design.cards
        game.initialize_game_info(cards, players, field_cardInfo_cacheobj)

        #gameを部屋に登録
        room.game = game
        room.save()

        return game
