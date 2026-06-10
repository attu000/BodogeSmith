//room
const roomId = JSON.parse(document.getElementById('room-id').textContent);
//通信先設定、通信開始
const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const url = protocol + window.location.host + '/ws/game_factory/rooms/playing/'+ roomId ;
const ws = new WebSocket(url);
 
 

//Global 変数------------------------------------------------
const {createApp, ref} = Vue;
const field_card_design = ref({});
const field_cardInfo = ref({});



//Listener登録------------------------------------------------

// id=choice_gameに対して
const choiceGameLink = document.getElementById('choice_game');
if(choiceGameLink){
    choiceGameLink.addEventListener('click', (event) => {
        event.preventDefault();
        const choicePanel = document.getElementById('choice_panel');
        choicePanel.style.display = 'block';
    });
}

//id=choice_panelないの<a>をクリックしたら
const choicePanel = document.getElementById('choice_panel');
if(choicePanel){
    choicePanel.addEventListener('click', (event) => {
        if (event.target.tagName === 'A') {
            event.preventDefault();
            
            const elementId = event.target.id;
            const game_design_id = elementId.split('_')[1];
            
            const message = {
                'type': 'game_choice',
                'game_design_id': game_design_id
            };
            sendWebSocketMessage(message);
        }
    });
}


// id=test_moveに対して　後で消そう
const testMove = document.getElementById('test_move');
if(testMove){
    testMove.addEventListener('click', (event) => {
        event.preventDefault();
        const message = {
                'type': 'test_move',
            };
            sendWebSocketMessage(message);
    });
}


//Vue.app登録-------------------------------------------------

//field_card_design
const FieldCardDesignManager = createApp({
    delimiters: ['[[', ']]'],
    setup(){
        
        // ドラッグ開始時の処理
        const handleDragStart = (event, card_id, from_path) => {
            console.log(`Drag Start: card_id=${card_id}, from=${from_path.join('/')}`);
            // ドラッグ中にデータを渡すために、dataTransferオブジェクトに情報を格納する
            const data = JSON.stringify({
                card_id: card_id,
                from_path: from_path
            });
            event.dataTransfer.setData('application/json', data);
        };

        // ドラッグ中の要素がドロップ先の上にあるときの処理
        const handleDragOver = (event) => {
            // event.preventDefault()が呼ばれることで、その要素がドロップ先として有効になる
            // Vueのテンプレートで @dragover.prevent としているので、この関数の中身は空でもOK
        };

        // ドロップ時の処理
        const handleDrop = (event, to_path) => {
            // dataTransferからドラッグ開始時に格納したデータを取得
            const data = JSON.parse(event.dataTransfer.getData('application/json'));
            console.log(`Drop: card_id=${data.card_id}, from=${data.from_path.join('/')}, to=${to_path.join('/')}`);
            
            // WebSocketでサーバーにカード移動情報を送信
            const message = {
                type: 'move_card',
                card_id: data.card_id,
                from_path: data.from_path,
                to_path: to_path,
            };
            sendWebSocketMessage(message);
        };

        // Vueテンプレートで使えるように関数を返す
        return {
            field_card_design, 
            field_cardInfo,
            handleDragStart,
            handleDragOver,
            handleDrop
        }
    }
}).mount('#field_card_design_app');



//message受信→担当関数に命令を外注------------------------------

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
        
    }
    else if(data.type == 'field_card_design_update'){
        console.log(data.field_card_design);
        field_card_design.value = data.field_card_design;
    }

    else if (data.type == 'field_cardInfo_update') {
        console.log(data.field_cardInfo);
        field_cardInfo.value = data.field_cardInfo;
    }
};


//データ送信------------------------------
function sendWebSocketMessage(message) {
    // ws変数がWebSocketインスタンスを指していると仮定
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    } else {
        console.warn('WebSocket is not open. Message not sent:', message);
    }
}



// エラー記録処理---------------------------
ws.onerror = e => {
    console.log(e);
}


//命令外注先の担当関数-------------------------
