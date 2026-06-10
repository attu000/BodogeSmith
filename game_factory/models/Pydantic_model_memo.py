

#field_card_design_dict:
"""例：
_field_card_design_dict = {
    'Personal':{
        'field_type':{
            'field':{ 
                    'target_dict':{'Myself':T, 'Others':F}
                    'card_num_limit':(0,99), 
                    'reversible':False 
                    'design':{
                        'position':(50,80),
                        'dimensions':(100,200), 
                        'display_card_maxnum':5, 
                        'init_reverse':True,
                }
            },
        },
    },

    "Public":{
        'field_type':{
            'field':{ 
                    'card_num_limit':(0,99), 
                    'reversible':False 
                    'design':{
                        'position':(50,80),
                        'dimensions':(100,200), 
                        'display_card_maxnum':5, 
                        'init_reverse':True,
                }
            },
        },
    },
    }
}
"""


#field_card_info_dict
"""
dct = {
    Personal:{
        field_type:{
            user_id:[
                {
                    card_id:int,
                    card_name:str,
                    card_url:str,
                    
                }
            ]
        }
    },
    Public:{
        field_type:[
                {
                    card_id:int,
                    card_name:str,
                    card_url:str,
                    
                }
        ]
    }
}
"""


#card_status_for_user
"""
dct = {
    users:{
        user_id:{
            card_id:{
                reverse:True
            }
        }
    }
}
"""

    
#field_card_info_to_send
"""
dct = {
    Personal:{
        field_type:{
            field:{
                user_id:[ #Persnoalのみ
                        {
                            card_info:{
                                card_id:int,
                                card_name:str,
                                card_url:str,
                            },
                            card_status:{
                                reverse:True,
                            }
                        }
                ]
            }
        }
    }
}"""