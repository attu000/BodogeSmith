from typing import Dict, List
from pydantic import BaseModel, Field, model_validator, ValidationError, ValidationInfo
from .field_cardInfo_model import CardInfoModel
from .card_status_for_user_model import CardStatusModel




class SendInfo(BaseModel):
    # 
    card_info_dict : CardInfoModel
    card_status_dict : CardStatusModel


class FieldCardInfoToSendModel(BaseModel):
    # Personal : {Hand : {MyHand: {User_id: [{SendInfo}, {}, ...]}}
    Personal: Dict[str , Dict[str, Dict[int,List[SendInfo]]]] = Field(default_factory=dict)
    Public :  Dict[str , Dict[str, List[SendInfo]]] = Field(default_factory=dict)




    @model_validator(mode='after')
    def check_field_names_are_unique(self): # ◀ 引数をselfに修正
        """PersonalとPublicの間でフィールド名が重複していないか検証する"""

        personal_names = set(self.Personal.keys())
        public_names = set(self.Public.keys())
        
        if not personal_names.isdisjoint(public_names):
            raise ValueError(f"フィールド名がPersonalとPublicで重複しています: {personal_names & public_names}")
            
        return self 


    @model_validator(mode='after')
    def check_fields_match_design(self, info: ValidationInfo):
        """FieldCardDesignModelとフィールド種類、仮想フィールド名が一致しているかのチェックをする"""
        design_model = info.context.get('design_model') if info.context else None
        if not design_model:
            return self

        error_messages = []

        # 'Personal' と 'Public' の両方のカテゴリをループでチェック
        for category_name in ('Personal', 'Public'):
            # getattr() を使って、文字列から動的に属性を取得
            design_data = getattr(design_model, category_name)
            actual_data = getattr(self, category_name)

            expected_field_types = set(design_data.keys())
            actual_field_types = set(actual_data.keys())
            
            # 1. フィールド種類名レベルでの検証
            if expected_field_types != actual_field_types:
                missing = expected_field_types - actual_field_types
                extra = actual_field_types - expected_field_types
                if missing:
                    error_messages.append(f"[{category_name}] 必須フィールド種別が不足: {missing}")
                if extra:
                    error_messages.append(f"[{category_name}] 未定義のフィールド種別が存在: {extra}")
                # この時点で不一致なら、下位の検証は行わずに次のカテゴリへ
                continue

            # 2. 仮想フィールド名レベルでの検証
            for field_type in expected_field_types:
                # 辞書としてキーでアクセス
                expected_virtual_fields = set(design_data[field_type].keys())
                actual_virtual_fields = set(actual_data[field_type].keys())

                if expected_virtual_fields != actual_virtual_fields:
                    missing = expected_virtual_fields - actual_virtual_fields
                    extra = actual_virtual_fields - expected_virtual_fields
                    if missing:
                        error_messages.append(f"[{category_name}.{field_type}] 必須仮想フィールドが不足: {missing}")
                    if extra:
                        error_messages.append(f"[{category_name}.{field_type}] 未定義の仮想フィールドが存在: {extra}")

        if error_messages:
            raise ValueError("、".join(error_messages))
            
        return self