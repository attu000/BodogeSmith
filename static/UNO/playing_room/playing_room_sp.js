
const roomId = JSON.parse(document.getElementById('room-id').textContent);

const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const url = protocol + window.location.host + '/ws/game_factory/rooms/playing/' + roomId + '/';
const ws = new WebSocket(url);



// --- グローバル変数と定数 ---
const placeCardContainer = document.getElementById('place_card');
const myselfCardContainer = document.getElementById('myself');
const fieldCardContainer = document.getElementById('field');
const deckCardContainer = document.getElementById('deck');
const dropPlaces = [
    myselfCardContainer,
    fieldCardContainer,
    deckCardContainer,
]

let draggedCard = null;     // ドラッグ/タッチ操作中のカード要素
let pressTimer = null;      // 長押し判定タイマー
let isDragging = false;     // ドラッグ/タッチ移動中かどうかのフラグ
let touchStartPos = { x: 0, y: 0 }; // タッチ開始座標
let clonedCard = null;      // タッチ操作時に表示するクローン要素


// --- イベントリスナー設定 ---

// スマホ用にtouchstartも追加
document.addEventListener('touchstart', (e) => {
    if (contextMenu.style.display === 'block' && !contextMenu.contains(e.target)) {
        hideShuffleMenu();
    }
}, { passive: true });


// --- カードのドラッグ＆ドロップ / タッチ操作 ---

// 1. 操作開始 (スマホ: touchstart)

// スマホ用タッチ開始
placeCardContainer.addEventListener('touchstart', (e) => {
    const card = e.target.closest('a[id^="Card|"]');
    if (!card) return;

    isDragging = false; // まだドラッグではない
    draggedCard = card;
    const touch = e.touches[0];
    touchStartPos = { x: touch.clientX, y: touch.clientY };

    // 長押し処理は、この後のdropPlacesのリスナーで開始されます
}, { passive: true });





// 2. 操作中 (スマホ: touchmove)
// スマホ用タッチ移動 (document全体で監視し、コンテナ外でも追従)
document.addEventListener('touchmove', (e) => {
    if (!draggedCard || e.touches.length === 0) return;

    const touch = e.touches[0];
    const dx = touch.clientX - touchStartPos.x;
    const dy = touch.clientY - touchStartPos.y;

    // 一定距離(10px)以上動いたらドラッグ操作と判定
    if (!isDragging && (Math.abs(dx) > 10 || Math.abs(dy) > 10)) {
        isDragging = true;
        clearTimeout(pressTimer); // 長押しをキャンセル

        // ドラッグ開始の処理：元のカードは半透明にして、クローンを生成
        draggedCard.style.opacity = '0.5';
        clonedCard = draggedCard.cloneNode(true);
        // クローンのスタイル設定
        Object.assign(clonedCard.style, {
            position: 'fixed', // 画面に固定
            pointerEvents: 'none', // クローン自体がイベントを拾わないように
            zIndex: '2000',
            opacity: '0.8',
            // 元の要素のサイズを維持
            width: `${draggedCard.offsetWidth}px`,
            height: `${draggedCard.offsetHeight}px`,
            display: 'inline-flex',
            justifyContent: 'center',
            alignItems: 'center',
            backgroundColor: '#fff',
            color: '#333',
            border: '1px solid #ccc',
            borderRadius: '6px',
            margin: '5px',
            textDecoration: 'none',
            fontSize: '16px',
            fontWeight: 'bold',
        });
        document.body.appendChild(clonedCard);
    }

    if (isDragging) {
        e.preventDefault(); // 画面スクロールを防止

        // クローンを指に追従させる (要素の中心が指の位置に来るように調整)
        clonedCard.style.left = `${touch.clientX - (clonedCard.offsetWidth / 2)}px`;
        clonedCard.style.top = `${touch.clientY - (clonedCard.offsetHeight / 2)}px`;

        // ドロップ先のハイライト処理
        clonedCard.style.display = 'none'; // 一時的にクローンを隠して下の要素を取得
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
        clonedCard.style.display = ''; // 表示に戻す

        dropPlaces.forEach(place => {
            // 下にある要素がドロップ先(またはその子要素)に含まれるか判定
            if (place.contains(elementBelow)) {
                place.style.backgroundColor = 'lightblue';
            } else {
                place.style.backgroundColor = '';
            }
        });
    }
}, { passive: false });


// 3. 操作終了 (スマホ: touchend)

// スマホ用タッチ終了
document.addEventListener('touchend', (e) => {
    if (!draggedCard) return;

    // ドロップ処理 (ドラッグ操作中だった場合のみ)
    if (isDragging && clonedCard) {
        clonedCard.style.display = 'none'; // ハイライト判定と同様に一時的に隠す
        const touch = e.changedTouches[0];
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
        const dropPlace = elementBelow ? elementBelow.closest('.card-container-class') : null;

        if (dropPlace && dropPlaces.includes(dropPlace)) {
            // PCのdropイベントと同様の処理を実行
            const origin_place = draggedCard.closest('.card-container-class').id;
            const target_place = dropPlace.id;

            if (origin_place !== target_place) {
                sendWebSocketMessage({
                    type: 'move_card',
                    card_info: draggedCard.id,
                    origin_place: origin_place,
                    target_place: target_place,
                });
            }
        }
    }

    // 後片付け
    clearTimeout(pressTimer);
    if (draggedCard) draggedCard.style.opacity = '';
    if (clonedCard) clonedCard.remove();
    dropPlaces.forEach(place => place.style.backgroundColor = '');

    draggedCard = null;
    clonedCard = null;
    isDragging = false;
});

// タッチが予期せずキャンセルされた場合も終了処理
document.addEventListener('touchcancel', (e) => {
    clearTimeout(pressTimer);
    if (draggedCard) draggedCard.style.opacity = '';
    if (clonedCard) clonedCard.remove();
    dropPlaces.forEach(place => place.style.backgroundColor = '');
    draggedCard = null;
    clonedCard = null;
    isDragging = false;
});


// --- ドロップゾーンと長押しのイベントリスナー ---

// ヘルパー関数: イベントから座標を取得 (PC/スマホ共通)
const getCoords = (e) => {
    if (e.touches && e.touches[0]) {
        return { x: e.touches[0].pageX, y: e.touches[0].pageY };
    }
    return { x: e.pageX, y: e.pageY };
};

// ヘルパー関数: 長押し開始処理
const handlePressStart = (e, place) => {
    // 左クリックまたはタッチの場合のみ処理
    if (e.type === 'mousedown' && e.button !== 0) return;

    const coords = getCoords(e);
    pressTimer = window.setTimeout(() => {
        // isDraggingフラグをチェックして、移動が始まっていない場合のみメニュー表示
        if (!isDragging) {
            showShuffleMenu(coords.x, coords.y, place.id);
        }
    }, 500); // 500msで長押しと判定
};

// ヘルパー関数: 長押しキャンセル処理
const handlePressCancel = () => {
    clearTimeout(pressTimer);
};


dropPlaces.forEach(place => {
    // --- PC用ドラッグイベント ---
    place.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.currentTarget.style.backgroundColor = 'lightblue';
    });
    place.addEventListener('dragleave', (e) => {
        e.currentTarget.style.backgroundColor = '';
    });
    place.addEventListener('drop', (e) => {
        e.preventDefault();
        e.currentTarget.style.backgroundColor = '';
        if (draggedCard) {
            const origin_place = draggedCard.closest('.card-container-class').id;
            const target_place = e.currentTarget.id;
            if (origin_place !== target_place) {
                const card_info = e.dataTransfer.getData('text/plain');
                sendWebSocketMessage({
                    type: 'move_card',
                    card_info: card_info,
                    origin_place: origin_place,
                    target_place: target_place,
                });
            }
        }
    });

    // --- 長押し処理 (PC & スマホ共通) ---
    place.addEventListener('mousedown', (e) => handlePressStart(e, place));
    place.addEventListener('touchstart', (e) => handlePressStart(e, place), { passive: true });

    // マウスが離れたら長押しキャンセル
    place.addEventListener('mouseup', handlePressCancel);
    place.addEventListener('mouseleave', handlePressCancel);
    
    // スマホで指が離れたり動いたりした際のキャンセルは、documentのtouchmove/touchendリスナーが処理します
});







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





//RE START---------------------------------------------

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
    cardA.classList.add('card');
    
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
    otherP.classList.add('card');
    
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
    deckA.classList.add('card');

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