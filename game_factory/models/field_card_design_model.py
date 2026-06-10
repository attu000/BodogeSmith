from typing import Dict, Tuple, Literal,List
from pydantic import BaseModel, Field, validator, model_validator, ValidationError



# design部分のモデル
class DesignModel(BaseModel):
    position: Tuple[int, int] = (10, 10)
    dimensions: Tuple[int, int] = (10, 10)
    display_card_maxnum: int = Field(3, ge=0)
    init_reverse: bool = False
    reversible: bool=False



# Publicフィールドの基本モデル
class VirtualPublicFieldModel(BaseModel):
    card_num_limit: Tuple[int, int] = (0, 99)
    design: DesignModel = Field(default_factory=DesignModel)

    @validator('card_num_limit')
    def check_card_num_limit(cls, v):
        min_val, max_val = v
        if min_val > max_val:
            raise ValueError('card_num_limitの最小値は最大値以下である必要があります')
        return v
    


# Personalフィールドのモデル (Publicを継承)
class VirtualPersonalFieldModel(VirtualPublicFieldModel):
    target_player :Dict[str,bool] = Field(default_factory=dict)
    

# JSON全体のトップレベルモデル
class FieldCardDesignModel(BaseModel):
    #本来PublicFieldはVirtualFieldがないはずだが今のことろこうしている。
    
    # Personal: {'Hand': {MyHand: VirtualPersonalFieldModel }}
    Personal: Dict[str, Dict[str, VirtualPersonalFieldModel]] = Field(default_factory=dict)
    Public: Dict[str, Dict[str, VirtualPublicFieldModel]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def check_field_names_are_unique(self): # 引数を self に変更
        """PersonalとPublicの間でフィールド名が重複していないか検証する"""
        
        personal_names = set(self.Personal.keys())
        public_names = set(self.Public.keys())
        
        if not personal_names.isdisjoint(public_names):
            raise ValueError(f"フィールド名がPersonalとPublicで重複しています: {personal_names & public_names}")

        return self
    

    
    @model_validator(mode='after')
    def validate_public_field_structure(self):
        """Publicの各フィールド種類に仮想フィールドが1つだけ定義されているか検証する"""
        for field_type, virtual_fields_dict in self.Public.items():
            if len(virtual_fields_dict) > 1:
                raise ValueError(
                    f"Publicのフィールド種類 '{field_type}' には複数の仮想フィールドが定義されています"
                    f"（1つである必要があります）。"
                )
        return self
    

    
    @model_validator(mode='after')
    def validate_personal_target_player_values_conflict(self):
        """
        同じFieldType内では、target_playerのあるキーに対して
        Trueを持つFieldが複数存在しないか検証する
        """
        for field_type, virtual_field_dict in self.Personal.items():
            # FieldTypeごとに、どのキーがTrueになったかを記録するセット
            keys_with_true = set()
            
            for virtual_field_info in virtual_field_dict.values():
                for key, value in virtual_field_info.target_player.items():
                    if value is True:
                        # このキーが既にTrueとして記録されていたら、競合が発生
                        if key in keys_with_true:
                            raise ValueError(
                                f"Personalのフィールド種類 '{field_type}' 内で、"
                                f"target_playerのキー '{key}' にTrueが複数回設定されています。"
                            )
                        # 初めてTrueとして見つかったキーをセットに追加
                        keys_with_true.add(key)
        return self



    @model_validator(mode='after')
    def validate_personal_target_player_keys_are_consistent(self):
        """Personalフィールド間で target_player のキーが一貫しているか検証する"""
        target_player_keys_list = []
        # 全てのPersonalフィールドからtarget_playerのキーセットを収集
        for field_type_dict in self.Personal.values():
            for virtual_field_model in field_type_dict.values():
                target_player_keys_list.append(set(virtual_field_model.target_player.keys()))
        
        # Personalフィールドが1つ以下の場合はチェック不要
        if len(target_player_keys_list) < 2:
            return self
            
        # 最初のキーセットを基準とする
        first_keys = target_player_keys_list[0]

        # 2つ目以降のキーセットが基準と一致するかチェック
        for other_keys in target_player_keys_list[1:]:
            if first_keys != other_keys:
                raise ValueError(
                    "Personalフィールド間で target_player のキーが一致しません。"
                    f"基準: {first_keys}, 異なるもの: {other_keys}"
                )
        return self