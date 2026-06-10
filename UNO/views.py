from django.views import generic
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Room, GameMaster
from .forms import RoomCreationForm, RoomJoinForm
from django.contrib import messages


class HomeView(generic.TemplateView):
    template_name = 'UNO/home/home.html'




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
            room.add_waiting_member(request.user)
            return redirect('waiting_room', room_id=room.id)
    else:
        form = RoomCreationForm()
    return render(request, 'UNO/home/create_join_room.html', {'form': form})




@login_required
def join_room(request):
    """部屋を検索して参加するビュー"""
    if request.method == 'POST':
        form = RoomJoinForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            password = form.cleaned_data['password']
            try:
                room = Room.objects.get(_name=name)
                #passward確認
                if room.check_password(password):
                    #waiting_membersに入る
                    room.add_waiting_member(request.user)
                    return redirect('waiting_room', room_id=room.id)
                else:
                    messages.error(request, 'パスワードが間違っています。')
            except Room.DoesNotExist:
                messages.error(request, 'その名前の部屋は存在しません。')
    else:
        form = RoomJoinForm()
    return render(request, 'UNO/home/create_join_room.html', {'form': form})




def waiting_room(request, room_id):
    """部屋の待機ページ"""
    room = get_object_or_404(Room, id=room_id)
    #部屋に入る権限チェック
    #Playing_members権限があったら
    if (request.user  in room.playing_members.all()):
        return redirect(f'playing_room',room_id=room.id)
    
    #どの権限もなかったら
    if (request.user not in room.waiting_members.all()):
        print(f"__USER{request.user} __reject_waiting__")
        return redirect('join_room')
    
    print(f"__USER{request.user} __waiting__")
    return render(request, 'UNO/waiting/waiting_room.html', {'room': room})



def playing_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.user not in room.playing_members.all():
        print(f"__USER{request.user} __reject_playing__")
        return redirect('join_room')
    print(f"__USER{request.user} __playing__")

    #temp 今のところ部屋一つにつきゲーム一つとする
    if  not room.room_game.exists():
        room_game = GameMaster()
        room_game.init_game(room)
        print('gamecreate')
    
    
    #room.room_game.all()[0].init_game(room)
    
    return render(request, 'UNO/playing/playing_room.html', {'room': room})
