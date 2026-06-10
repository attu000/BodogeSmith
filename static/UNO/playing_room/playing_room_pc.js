
const roomId = JSON.parse(document.getElementById('room-id').textContent);

const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const url = protocol + window.location.host + '/ws/rooms/playing/'+ roomId ;
const ws = new WebSocket(url);



//全体--------------------------------------------

document.addEventListener('mousedown', (e) => {
    if (contextMenu.style.display == 'block' && !contextMenu.contains(e.target)) {
        hideShuffleMenu();
    }
});




//---card_drag&drop----Menu表示---------------------------

const placeCardContainer = document.getElementById('place_card');
const myselfCardContainer = document.getElementById('myself');
const fieldCardContainer = document.getElementById('field');
const deckCardContainer = document.getElementById('deck');
const dropPlaces = [
    myselfCardContainer,
    fieldCardContainer,
    deckCardContainer,
]
let draggedCard = null; // ドラッグ中のカードを保持する変数なのら

let pressTimer; // 長押しと判定するためのタイマー



//1:myselfドラッグ開始
placeCardContainer.addEventListener('dragstart', (e) => {
    // タイマーを解除して、長押し処理をキャンセル
    clearTimeout(pressTimer);

    const card = e.target.closest('a[id^="Card|"]');
    if (card) {
        draggedCard = e.target;
        e.dataTransfer.setData('text/plain', card.id);
        setTimeout(() => {
            e.target.style.opacity = '0'; // 透明にする例
        }, 0);
    }
});


//2:ドラッグ終了時の処理 
placeCardContainer.addEventListener('dragend', (e) => {
    if (draggedCard) {
        draggedCard.style.opacity = ''; // スタイルを元に戻す
        draggedCard = null;
    }
});


//ForEach
dropPlaces.forEach(place =>{

    //3_1:ドロップ先の要素がドラッグを受け入れる許可
    place.addEventListener('dragover', (e) => {
        e.preventDefault(); // デフォルトの挙動（リンクを開くなど）をキャンセル
        e.currentTarget.style.backgroundColor = 'lightblue';
    });

    //3_2:ドラッグ要素がドロップゾーンから離れた時の処理
    place.addEventListener('dragleave', (e) => {
        e.currentTarget.style.backgroundColor = '';
    });


    //4:ドロップ時の処理
    place.addEventListener('drop', (e) => {
        e.preventDefault();
        e.currentTarget.style.backgroundColor = '';
        const origin_place = draggedCard.closest('.card-container-class').id;
        const target_place = e.currentTarget.id;

        if (draggedCard && origin_place!=target_place) {
            const card_info = e.dataTransfer.getData('text/plain');
            console.log(`カードID ${card_info} が場札にドロップされた！`);

            sendWebSocketMessage({
                type: 'move_card',
                card_info: card_info,
                origin_place: origin_place,
                target_place: target_place,
            });
        }
    });



    //５：長押し時の処理を追加

    // 5_1マウスボタンが押された時の処理
    place.addEventListener('mousedown', (e) => {
        console.log('mousedown');
        // 左クリックの場合のみ処理
        if (e.button !== 0) return;


        // タイマーを開始して、500ミリ秒後にメニューを表示
        pressTimer = window.setTimeout(() => {
            console.log('log_tup');
            showShuffleMenu(e.pageX, e.pageY, place.id);
        }, 500);
    });


    // 5_2マウスボタンが離された時の処理
    place.addEventListener('mouseup', () => {
        // タイマーを解除して、長押し処理をキャンセル
        clearTimeout(pressTimer);
    });

    
    // 5_3マウスが要素から離れた時の処理
    place.addEventListener('mouseleave', () => {
        // タイマーを解除して、長押し処理をキャンセル
        clearTimeout(pressTimer);
    });

})







//巻き戻す---------------------------------------------

const rewindButton = document.getElementById('rewind');
if (rewindButton){
    rewindButton.addEventListener('click', function(event) {
        event.preventDefault(); // aタグのデフォルトの動きを止める
        const message = {
            'type': 'rewind',
        };
        ws.send(JSON.stringify(message));
    });
}





//巻き戻す---------------------------------------------

const restartButton = document.getElementById('restart');
if (restartButton){
    restartButton.addEventListener('click', function(event) {
        event.preventDefault(); // aタグのデフォルトの動きを止める
        const message = {
            'type': 'restart',
        };
        ws.send(JSON.stringify(message));
    });
}




//messageを受け取ったら------------------------------

ws.onmessage = function(e) {
    const data = JSON.parse(e.data);
    console.log(data);
    
            
    if(data.type == 'history_back_from_playing_room'){
        window.history.back();

    }
    else if(data.type == 'redirect'){
        setTimeout(() => {
            window.location.href = data.url;
        }, 150);
        
    }else if(data.type == 'game_status_update'){
        console.log('update')
        console.log(data.user_status_dict)
        updateGameStatus(data.user_status_dict)      
    }

    
};


//データ送信

function sendWebSocketMessage(message) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    } else {
        console.warn('WebSocket is not open. Message not sent:', message);
        // 必要に応じて、再接続の試行やエラーハンドリングを行うなのら
    }
}


ws.onerror = e => {
    console.log(e);
}





// game update ------------------------------------------------

function updateGameStatus(user_status_dict){

    //１：自分の手札------------------------------------
    const myself_card_div = document.getElementById('myself');
    const myself_card_fragment = document.createDocumentFragment();

    //空にする
    myself_card_div.innerHTML = '';
    // 場所の名前を表示するヘッダーを作る
    const placeHeader = document.createElement('h3');
    placeHeader.textContent = user_status_dict['myself']['name'];
    myself_card_fragment.appendChild(placeHeader);

    //card情報を抜き出して格納する
    const myself_cards = user_status_dict['myself']['card'];

    myself_cards.forEach(card => {
    const cardA = document.createElement('a');
    cardA.href = '#';
    cardA.draggable='true';
    cardA.id = `Card|${card['pk']}|${card['rank']}|${card['color']}`;
    
    // カードの名前と画像を表示する例
    cardA.innerHTML = `〇${card['rank']}_${card['color']}　`;
    
    // 場所のDIVにカードのAを追加する
    myself_card_fragment.appendChild(cardA);
    });

    //保存
    myself_card_div.appendChild(myself_card_fragment);




    //2:相手の手札情報------------------------------------------
    const others_info_div = document.getElementById('others');
    const others_info_fragment = document.createDocumentFragment();
    //空にする
    others_info_div.innerHTML = '';
    // 場所の名前を表示するヘッダーを作る
    const otherHeader = document.createElement('h3');
    otherHeader.textContent = 'Others';
    others_info_fragment.appendChild(otherHeader);

    const others = user_status_dict['others'];

    others.forEach(other => {
    const otherP = document.createElement('p');
    otherP.id = `UserID|${other['pk']}`;
    
    // カードの名前と画像を表示する例
    otherP.innerHTML = `〇${other['name']}_have${other['card_num']}cards　`;
    
    // 場所のDIVにカードのAを追加する
    others_info_fragment.appendChild(otherP);
    });

    //保存
    others_info_div.appendChild(others_info_fragment);




    //3:Fieldの情報ーーーーーーーーーーーーーーーーーーーーーーーーーーーーー
    const field_card_div = document.getElementById('field');
    field_card_div.innerHTML = '';
    // 場所の名前を表示するヘッダーを作る
    const fieldHeader = document.createElement('h3');
    fieldHeader.textContent = 'Field';
    field_card_div.appendChild(fieldHeader);

    const field = user_status_dict['field'];
    if (field){
        const fieldP = document.createElement('a');
        fieldP.href = '#';
        fieldP.id = `Card|${field['pk']}|${field['rank']}|${field['color']}`
        fieldP.innerHTML = `〇${field['rank']}_${field['color']}　`;
        field_card_div.appendChild(fieldP);
    }



    //4:log
    const log_div = document.getElementById('log');
    const log_fragment = document.createDocumentFragment();
    //空にする
    log_div.innerHTML = '';

    const logHeader = document.createElement('h3');
    logHeader.textContent = 'LOG';
    log_fragment.appendChild(logHeader);

    const logs = user_status_dict['game_status']['log'];

    logs.reverse().forEach(log => {
    const logP = document.createElement('p');
    
    // カードの名前と画像を表示する例
    logP.innerHTML = `〇${log}　`;
    
    // 場所のDIVにカードのAを追加する
    log_fragment.appendChild(logP);
    });

    //保存
    log_div.appendChild(log_fragment);



    //5:deck
    const deck_div = document.getElementById('deck');
    //空にする
    deck_div.innerHTML = '';
    //カードを追加
    const deckHeader = document.createElement('h3');
    deckHeader.textContent = 'Deck';
    deck_div.appendChild(deckHeader);
    
    const deckA = document.createElement('a');
    deckA.id = 'Card|-1|deck|top';
    deckA.href = '#';
    deckA.textContent ='山札';
    deck_div.appendChild(deckA);




}




// 長押しメニュー表示-------------------------------------------


// カスタムコンテキストメニューの要素を作成
let contextMenu = document.createElement('div');
contextMenu.id = 'shuffle-context-menu';
// メニューのスタイルを設定
Object.assign(contextMenu.style, {
    position: 'absolute',
    display: 'none',
    backgroundColor: 'white',
    border: '1px solid #ccc',
    borderRadius: '5px',
    padding: '10px 15px',
    cursor: 'pointer',
    boxShadow: '2px 2px 5px rgba(0,0,0,0.2)',
    zIndex: '1000'
});
contextMenu.innerHTML = '<div>シャッフルする</div>';
document.body.appendChild(contextMenu);



const showShuffleMenu = (x, y, placeId) => {
    contextMenu.style.left = `${x}px`;
    contextMenu.style.top = `${y}px`;
    contextMenu.style.display = 'block';


    // メニュークリック時の処理（一度リスナーを解除して再設定）
    const newMenu = contextMenu.cloneNode(true);
    contextMenu.parentNode.replaceChild(newMenu, contextMenu);
    contextMenu = newMenu;
    contextMenu.addEventListener('click', () => {
        console.log(`コンテナID: ${placeId} のシャッフルをリクエストします。`);
        
        // DjangoにWebSocketメッセージを送信
        sendWebSocketMessage({
            type: 'shuffle',
            place: placeId,
            direct:1,
        });
        
        hideShuffleMenu(); // メニューを閉じる
    });
};

/**
 * コンテキストメニューを非表示にする関数
 */
const hideShuffleMenu = () => {
    if (contextMenu.style.display === 'block') {
        contextMenu.style.display = 'none';
    }
};