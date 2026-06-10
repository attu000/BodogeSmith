// データ取得
const roomId       = JSON.parse(document.getElementById('room-id').textContent);
const gameDesignsData = JSON.parse(document.getElementById('game-designs-data').textContent);
const isOwnerData  = JSON.parse(document.getElementById('is-owner-data').textContent);
const roomNameData = JSON.parse(document.getElementById('room-name').textContent);

// WebSocket接続
const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const ws = new WebSocket(protocol + window.location.host + '/ws/game_factory/rooms/playing/' + roomId);

// Vue refs（ws.onmessage からも参照するためモジュールスコープに置く）
const { createApp, ref, computed } = Vue;
const field_card_design = ref({});
const field_cardInfo    = ref({});
// GMのみ最初からパネルを開く。非GMは受け取り待ち。
const showSelectPanel   = ref(isOwnerData);

// Vue アプリ
createApp({
    delimiters: ['[[', ']]'],
    setup() {
        const gameDesigns = ref(gameDesignsData);
        const isOwner  = isOwnerData;
        const roomName = roomNameData;
        const hasGame  = computed(() => Object.keys(field_card_design.value).length > 0);

        // ゲーム開始・変更（GMのみ呼ばれる）
        const startGame = (gameDesignId) => {
            sendWsMessage({ type: 'start_game', game_design_id: gameDesignId });
        };

        // ドラッグ
        const handleDragStart = (event, card_id, from_path) => {
            event.dataTransfer.setData('application/json', JSON.stringify({ card_id, from_path }));
        };

        const handleDrop = (event, to_path) => {
            event.preventDefault();
            const raw = event.dataTransfer.getData('application/json');
            if (!raw) return;
            const { card_id, from_path } = JSON.parse(raw);
            sendWsMessage({ type: 'move_card', card_id, from_path, to_path });
        };

        // フィールドdiv直接のdropを処理
        // Personalフィールドで personal_user_field の外に落ちた場合の fallback
        const handleFieldDrop = (event, category, fieldTypeName, fieldName) => {
            if (category === 'Public') {
                handleDrop(event, [category, fieldTypeName]);
            } else if (category === 'Personal') {
                const users = field_cardInfo.value?.[category]?.[fieldTypeName]?.[fieldName];
                if (users) {
                    const firstUserId = Object.keys(users)[0];
                    if (firstUserId !== undefined) {
                        handleDrop(event, [category, fieldTypeName, firstUserId]);
                    }
                }
            }
        };

        return {
            field_card_design, field_cardInfo, showSelectPanel,
            gameDesigns, isOwner, roomName, hasGame,
            startGame, handleDragStart, handleDrop, handleFieldDrop,
        };
    }
}).mount('#app');


// WebSocket メッセージ受信
ws.onmessage = function(e) {
    const data = JSON.parse(e.data);

    if (data.type === 'redirect') {
        setTimeout(() => { window.location.href = data.url; }, 150);

    } else if (data.type === 'field_card_design_update') {
        field_card_design.value = data.field_card_design ?? {};
        // ゲームデータが届いたら選択パネルを閉じる
        if (Object.keys(field_card_design.value).length > 0) {
            showSelectPanel.value = false;
        }

    } else if (data.type === 'field_cardInfo_update') {
        field_cardInfo.value = data.field_cardInfo ?? {};
    }
};

ws.onerror = e => console.error('WebSocket error:', e);


// WebSocket 送信ヘルパー
function sendWsMessage(message) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    } else {
        console.warn('WebSocket not open:', message);
    }
}
