from typing import Dict, List,Set
from pydantic import BaseModel, Field, model_validator, ValidationError, ValidationInfo


class CardStatusModel(BaseModel):
    reverse:bool = False



class CardStatusForUserModel(BaseModel):
    # users: {user_id: { card_id: {CardStatusModel }}}
    users: Dict[int, Dict[int, CardStatusModel]] = Field(default_factory=dict)



@model_validator(mode='after')
def check_ids_are_valid(self, info: ValidationInfo) -> 'CardStatusForUserModel':
    """
    コンテキストで渡されたplayersとcardsのQuerySetと照合し、
    このモデル内のuser_idとcard_idがすべて有効か検証する。
    """
    if not info.context:
        return self

    # 1. コンテキストから検証の基準となるQuerySetを取得
    players_qs = info.context.get('players_qs')
    cards_qs = info.context.get('cards_qs')

    # コンテキストに必要な情報がなければ検証をスキップ
    if not players_qs or not cards_qs:
        return self
        
    # 2. QuerySetから効率的にIDのセットを作成
    valid_user_ids = set(players_qs.values_list('id', flat=True))
    valid_card_ids = set(cards_qs.values_list('id', flat=True))

    # 3. このモデル内に「実際に」存在するuser_idとcard_idを収集
    actual_user_ids = set(self.users.keys())
    
    actual_card_ids = set()
    for user_cards in self.users.values():
        actual_card_ids.update(user_cards.keys())

    # 4. 存在しないIDがないかチェック
    invalid_users = actual_user_ids - valid_user_ids
    if invalid_users:
        raise ValueError(f"存在しない不正なuser_idが含まれています: {invalid_users}")

    invalid_cards = actual_card_ids - valid_card_ids
    if invalid_cards:
        raise ValueError(f"存在しない不正なcard_idが含まれています: {invalid_cards}")
    
    #辞書のkeyだから重複はない

    print("validation OK: check_ids_are_valid")
    return self