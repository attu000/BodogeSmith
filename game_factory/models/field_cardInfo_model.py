from typing import Dict, List
from pydantic import BaseModel, Field, model_validator, ValidationError, ValidationInfo



class CardInfoModel(BaseModel):
    card_id: int|None
    card_name:str|None
    card_url:str|None

class FieldCardInfoModel(BaseModel):
    """
    どの場所にどのカードがあるかを定義するPydanticモデル
    例：
    """
    #Public: {Hand: [cardInfoModel]}
    Public: Dict[str, List[CardInfoModel]] = Field(default_factory=dict)
    #Public: {Hand: {playerID: [cardInfoModel] } }
    Personal: Dict[str, Dict[int, List[CardInfoModel]]] = Field(default_factory=dict)





    @model_validator(mode='after')
    def check_field_names_are_unique(self): 
        """PersonalとPublicの間でフィールド名が重複していないか検証する"""

        personal_names = set(self.Personal.keys())
        public_names = set(self.Public.keys())
        
        if not personal_names.isdisjoint(public_names):
            raise ValueError(f"フィールド名がPersonalとPublicで重複しています: {personal_names & public_names}")
        
        print("validation OK: check_field_names_are_unique")
        return self 
    



    @model_validator(mode='after')
    def check_fields_match_design(self, info: ValidationInfo):
        """
        FieldCardDesignModelのフィールド定義と、このモデルのフィールド名が一致しているか検証する。
        """
        # 1. コンテキストから比較対象の design_model を取得
        design_model = info.context.get('design_model') if info.context else None

        # コンテキストが渡されなかった場合は検証をスキップ
        if not design_model:
            return self

        # 2. 期待されるフィールド名のセットを作成
        expected_fields = set(design_model.Public.keys()) | set(design_model.Personal.keys())

        # 3. 実際のフィールド名のセットを作成
        actual_fields = set(self.Public.keys()) | set(self.Personal.keys())

        # 4. セットを比較して差異をチェック
        if expected_fields != actual_fields:
            missing_fields = expected_fields - actual_fields
            extra_fields = actual_fields - expected_fields
            error_messages = []
            if missing_fields:
                error_messages.append(f"必須フィールドが不足しています: {missing_fields}")
            if extra_fields:
                error_messages.append(f"定義にない余分なフィールドが存在します: {extra_fields}")
            
            raise ValueError("、".join(error_messages))
        
        print("validation OK: check_fields_match_design")
        return self
    






    @model_validator(mode='after')
    def check_all_cards_are_present(self, info: ValidationInfo) -> 'FieldCardInfoModel':
        """
        コンテキストで渡されたQuerySetに含まれる全カードのIDが、
        このモデル内に過不足なく、かつ重複なく存在することを検証する。
        """
        # 1. コンテキストから比較対象のQuerySetを取得
        all_cards_qs = info.context.get('cards') if info.context else None
        
        # コンテキストが渡されなかった場合は検証をスキップ
        if not all_cards_qs:
            return self

        # 2. DBに存在する「あるべき」カードIDのセットを作成
        expected_card_ids = set(all_cards_qs.values_list('id', flat=True))

        # 3. このモデル内に「実際に」存在するカードIDのリストを収集
        actual_card_ids_list = []
        # Public: {Hand: [cardInfoModel]}
        for card_list in self.Public.values():
            actual_card_ids_list.extend(c.card_id for c in card_list)
        
        # Personal: {Hand: {playerID: [cardInfoModel]}}
        for player_dict in self.Personal.values():
            for card_list in player_dict.values():
                actual_card_ids_list.extend(c.card_id for c in card_list)

        # 4. モデル内でのカードIDの重複をチェック
        if len(actual_card_ids_list) != len(set(actual_card_ids_list)):
            # 重複しているIDを見つけてエラーメッセージに含める
            from collections import Counter
            counts = Counter(actual_card_ids_list)
            duplicates = {item for item, count in counts.items() if count > 1}
            raise ValueError(f"モデル内に重複したカードIDが存在します: {duplicates}")

        # 5. 「あるべきID」と「実際のID」のセットを比較
        actual_card_ids_set = set(actual_card_ids_list)
        
        if expected_card_ids != actual_card_ids_set:
            missing_from_model = expected_card_ids - actual_card_ids_set
            extra_in_model = actual_card_ids_set - expected_card_ids
            error_messages = []
            if missing_from_model:
                error_messages.append(f"モデルに存在しない必須カードIDがあります: {missing_from_model}")
            if extra_in_model:
                error_messages.append(f"DBに存在しない余分なカードIDがモデルに含まれています: {extra_in_model}")

            raise ValueError("、".join(error_messages))
        print("validation OK: check_all_cards_are_present")
        return self
