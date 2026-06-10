from django.views import generic
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages

from .forms import RoomCreationForm, RoomJoinForm, GameDesignBasicForm, CardForm
from .models import GameDesign, Card, Room
import json
from django.http import JsonResponse


def home(request):
    user_game_designs = []
    if request.user.is_authenticated:
        user_game_designs = GameDesign.objects.filter(_creater=request.user)
    
    context = {
        'game_designs': user_game_designs,
    }
    return render(request, 'GameFactory/home/home.html', context)





@login_required
def create_room(request):
    """部屋を作成するビュー"""
    if request.method == 'POST':
        form = RoomCreationForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.set_owner(request.user)
            room.set_password(form.cleaned_data['password'])
            room.save()
            room.add_playing_member(request.user)
            return redirect('game_factory:waiting_room', room_id=room.id)
    else:
        form = RoomCreationForm()
    return render(request, 'GameFactory/home/create_join_room.html', {'form': form})




@login_required
def join_room(request):
    """
    部屋を検索して参加するビュー
    1. pass_check  =No=> join_room
    2. room_status =CLOSED => in playing_member =Yes=> playing_room
                              in playing_member =No => join_room
    add playing_member & waiting_room
    """
    # GETリクエストの場合は、空のフォームを表示して終了
    if request.method != 'POST':
        form = RoomJoinForm()
        return render(request, 'GameFactory/home/create_join_room.html', {'form': form})

    # 以下、POSTリクエストの処理
    form = RoomJoinForm(request.POST)
    if not form.is_valid():
        # フォームが無効な場合は、エラー情報と共にフォームを再表示
        return render(request, 'GameFactory/home/create_join_room.html', {'form': form})

    name = form.cleaned_data['name']
    password = form.cleaned_data['password']



    # 1. 部屋の存在をチェック
    try:
        room = Room.objects.filter(_name=name).first()
    except Room.DoesNotExist:
        messages.error(request, 'その名前の部屋は存在しません。')
        return render(request, 'GameFactory/home/create_join_room.html', {'form': form})

    # 2. パスワードをチェック
    if not room.check_password(password):
        messages.error(request, 'パスワードが間違っています。')
        return render(request, 'GameFactory/home/create_join_room.html', {'form': form})
        
    # 3. 部屋が締切済の場合の処理
    if room.status == Room.RoomStatus.CLOSED:
        # すでにメンバーなら、ゲーム画面へリダイレクト
        if request.user in room.playing_members.all():
            return redirect('game_factory:playing_room', room_id=room.id)
        # メンバーでなければ、参加できない
        else:
            messages.error(request, 'この部屋は締め切られています。')
            return render(request, 'GameFactory/home/create_join_room.html', {'form': form})

    
    # 部屋が募集中なので、メンバーに追加して待機室へ
    room.add_playing_member(request.user)
    print("add waiting_room")
    return redirect('game_factory:waiting_room', room_id=room.id)





def waiting_room(request, room_id):
    """
    部屋の待機ページ
    1. in playing_member =No=> join_room
    2. room_status       =CLOSED=> playing_room
    => render waiting_room.html
    """
    room = get_object_or_404(Room, id=room_id)
    
    # 1. in playing_member =No=> join_room
    if (request.user  not in room.playing_members.all()):
        print("not in ")
        return redirect('game_factory:join_room')
    
    # 2. room_status  =CLOSED=> playing_room
    if (room.status == Room.RoomStatus.CLOSED):
        print("go to playing_room")
        return redirect('game_factory:playing_room', room_id=room.id)
    
    return render(request, 'GameFactory/waiting/waiting_room.html', {'room': room})






def playing_room(request, room_id):
    """
    部屋のプレイページ
    1. in playing_member =No=> join_room
    2. room_status       =OPEN=> waiting_room
    => redirect playing_room
    """
    room = get_object_or_404(Room, id=room_id)

    if request.user not in room.playing_members.all():
        return redirect('join_room')

    if room.status == Room.RoomStatus.OPEN:
        return redirect('waiting_room', room_id=room.id)
    
    player_count = room._playing_members.count()
    playable_games = GameDesign.objects.filter(
        _published=True,
        _player_limit__gte=player_count
    )
    game_designs_data = [
        {'id': gd.id, 'name': gd.name, 'player_limit': gd.player_limit}
        for gd in playable_games
    ]
    context = {
        'room': room,
        'player_count': player_count,
        'game_designs_data': game_designs_data,
        'is_owner': request.user == room.owner,
    }

    return render(request, 'GameFactory/playing/playing_room.html', context)




@login_required
def create_game_design(request):
    """
    新しい空のゲームデザインを作成し、その編集ページにリダイレクトする。
    """
    new_game_design = GameDesign.objects.create(
        _creater=request.user
    )

    # 2. 作成したインスタンスのIDを使って、ユニークな仮の名前を設定する
    new_game_design._name = f"無題のゲームデザイン - {new_game_design.id}"
    new_game_design.save(update_fields=['_name'])

    # 3. 作成したGameDesignの編集ページにリダイレクトする
    #    URLには新しく作成したオブジェクトのIDを渡す
    return redirect('game_factory:edit_game_design', game_design_id=new_game_design.id)
    


@login_required
def edit_game_design(request, game_design_id):
    """
    create_game.html をレンダリングするためのビュー。
    テンプレートに編集対象のgame_designオブジェクトを渡す。
    """
    game_design = get_object_or_404(GameDesign, id=game_design_id)
    
    # 作成者本人でなければホームページにリダイレクト
    if request.user != game_design.creater:
        messages.error(request, "編集する権限がありません。")
        return redirect('game_factory:home')

    context = {
        'game_design': game_design
    }
    return render(request, 'GameFactory/home/edit_game_design.html', context)




@login_required
@transaction.atomic
def update_game_design(request, game_design_id):
    """
    GameDesignに関する全ての変更リクエストを処理する単一APIエンドポイント.
    1. JSから送られてくるmaltipart情報の例：
        formData = 
            { action:'update_basic_info',  
            json_data :{_name: str , 
                        _player_limit: int }
            _card_image : file
            }
    2. 実際に受け取るrequest.POST/FILESの例：
        request.POST = {
            'action': 'update_basic_info',
            'json_data':{'_name': str , '_player_limit': int }}
        
        request.FILES = {
            '_card_image': file}
    """
    print("!!!!!!!!!!!UPDate!!!!!!!!!!!!")
    game_design = get_object_or_404(GameDesign, id=game_design_id)
    
    # --- 権限チェック ---
    if request.user != game_design._creater:
        return JsonResponse({'status': 'error', 'message': '権限がありません。'}, status=403)

    try:
        action = request.POST.get('action')
        json_data = request.POST.get('json_data', '{}')#もしjson_dataが見つからなかった場合は{}を返す。
        dict_data = json.loads(json_data)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'status': 'error', 'message': '無効なリクエスト形式です。'}, status=400)
    

    print(action)

    # --- actionの値に応じて処理を振り分け ---
    try:
        # basic
        if action == 'update_basic_info': 
            # formData = 
            # { action:'update_basic_info',  
            #   json_data :{_name: str , 
            #             _player_limit: int }}
            form = GameDesignBasicForm(dict_data, instance=game_design)
            if form.is_valid():
                form.save()
            else:
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        #card
        elif action == 'add_new_card':
            # formData = {
            # action:'add_new_card',
            # json_data : {
            #   _name : str}
            # _card_image : file
            # }
            card_form = CardForm(dict_data, request.FILES)
            if card_form.is_valid():
                new_card = card_form.save()
                game_design.add_card(new_card)
            else:return JsonResponse({'status': 'error', 'errors': card_form.errors}, status=400)

        elif action == 'update_card':
            # formData = {
            # action : 'update_card',
            # json_data : {
            #   id :int,
            #   _name : str,
            #   }
            # _card_image : file}
            card_id = dict_data.get('id')
            card_instance = get_object_or_404(Card, id=card_id)
            # CardFormを使って更新
            card_form = CardForm(dict_data, request.FILES, instance=card_instance)
            if card_form.is_valid():
                card_form.save()
            else:
              return JsonResponse({'status': 'error', 'errors': card_form.errors}, status=400)
            
        elif action=="update_card_initial_field":
            # formData = {
            #   action : 'update_card_initial_field,
            #   json_data :{
            #         card_id: int,
            #         field_type: str,
            #}}
            game_design.register_cardInfo_to_public(**dict_data)


        # field
        elif action == 'add_personal_field_type':
            # formData = {
            #    action : 'add_personal_field_type',
            #    json_data:{
            #        field_type:str
            #    }
            # }
            game_design.add_personal_field_type(**dict_data)

        elif action == 'add_public_field_type':
            # formData = {
            #    action : 'add_public_field_type',
            #    json_data:{
            #        field_type:str
            #    }
            # }
            game_design.add_public_field_type(**dict_data)

        elif action == 'add_virtual_public_field':
            # formData = {
            #     action:'add_virtual_public_field',
            #     json_data:{
            #         field_type:str,
            #         field_name:str
            #     }
            # }
            game_design.add_virtual_public_field(**dict_data)


        elif action == 'add_virtual_personal_field':
            # formData = {
            #     action:'add_virtual_personal_field',
            #     json_data:{
            #         field_type:str,
            #         field_name:str
            #     }
            # }
            game_design.add_virtual_personal_field(**dict_data)


        elif action == 'update_virtual_field':
          # JSから送られてくるjson_dataの想定:
          # {
          #   'category_name': 'Public',
          #   'field_type': Deck,
          #   'field_name': 'myDeck',
          #   'field_data': {card_num_limit:1, ..., design:{ position: [x,y], dimensions: [w,h] } }
          # }
          game_design.update_virtual_field(**dict_data)


        
        # publish
        elif action == 'publish_change':
            # formData = {
            # action : 'publish_change',
            # json_data : {
            #   status : publish or unpublish,
            # }
            #}
            if dict_data.get('status') == 'publish':
                game_design.publish()
            elif dict_data.get('status') == 'unpublish':
                game_design.unpublish()
            else:
                return JsonResponse({'status': 'error', 'message': '無効なステータスです。'}, status=400)
        

        else:
            return JsonResponse({'status': 'error', 'message': f"不明なアクション: {action}"}, status=400)
        
        #もしうまくいったら更新後データを送信
        print("Update Done!!!!!!!!!!!!!!")
        updated_game_design_data = game_design.to_dict()
        return JsonResponse({
            'status': 'success',
            'message': '更新が成功しました。',
            'updated_game_design': updated_game_design_data # ← 最新の完全なデータ
        })

    except (ValueError, KeyError, AttributeError) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)



@login_required
def get_game_design_data(request, game_design_id):
    """
    指定されたIDのGameDesignの全データをJSONで返すAPIエンドポイント。(GETリクエスト用)
    """
    # オブジェクトを取得し、存在しない場合は404エラーを返す
    game_design = get_object_or_404(GameDesign, id=game_design_id)
    
    # 権限チェック（作成者でなければアクセスを拒否）
    if request.user != game_design._creater:
        return JsonResponse({'status': 'error', 'message': '権限がありません。'}, status=403)
        
    # モデルの to_dict() メソッドを使ってデータを辞書に変換
    data = game_design.to_dict()
    
    return JsonResponse({'status': 'success', 'game_design': data})
    


    




def choice_game(request, room_id):
    """ゲーム選択画面"""
    room = get_object_or_404(Room, id=room_id)

    player_count = room._playing_members.count()

    playable_games = GameDesign.objects.filter(
        _published=True,
        _player_limit__gte=player_count
    )

    context = {
        'room': room,
        'game_designs': playable_games,
    }

    return render(request, 'GameFactory/playing/choice_game.html', context)
    

    

