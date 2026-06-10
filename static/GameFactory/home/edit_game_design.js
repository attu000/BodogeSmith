const { createApp, ref, computed, onMounted } = Vue;

createApp({
    delimiters: ['[[', ']]'],
    setup() {
        // --- 1. リアクティブデータ ---
        const gameDesign = ref({});
        const selectedField = ref(null);
        const selectedFieldType = ref(null);
        const selectedFieldCategory = ref(null);
        const newFieldTargets = ref({
            myself: false,
            others: false
        });

        // フォーム入力用のデータ
        const newCardName = ref('');
        const newFieldName = ref('');
        const newFieldTypeName = ref('');

        // ユーザーへのフィードバックメッセージ用
        const feedback = ref({ message: '', type: 'success', visible: false });


        // --- 2. 算出プロパティ ---

        // 編集対象のフィールドデータを算出
        const editingFieldData = computed(() => {
            if (!selectedField.value || !gameDesign.value.field_card_design) {
                return null;
            }
            return gameDesign.value.field_card_design[selectedFieldCategory.value][selectedFieldType.value][selectedField.value];
        });

        //-------------------------
        // --- 3. メソッド ---
        //-------------------------

        // メッセージ表示関数
        const displayMessage = (message, type = 'success') => {
            feedback.value = { message, type, visible: true };
            setTimeout(() => {
                feedback.value.visible = false;
            }, 4000);
        };

        // 汎用的なデータ更新リクエスト関数
        const sendUpdateRequest = async (formData) => {
            const gameDesignId = gameDesign.value.id;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const url = `/rooms/update_game_design/${gameDesignId}/`;

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData
                });
                const result = await response.json();

                if (response.ok) {
                    // 成功したら、サーバーから返された最新のデータでローカルのデータを更新
                    if (result.updated_game_design) {
                        gameDesign.value = result.updated_game_design;
                    }
                    displayMessage(result.message || '更新しました。', 'success');
                } else {
                    const errorMessage = result.message || (result.errors ? JSON.stringify(result.errors) : 'エラーが発生しました。');
                    displayMessage(errorMessage, 'error');
                    console.log(errorMessage);
                }
            } catch (error) {
                console.error('Fetch Error:', error);
                displayMessage('通信エラーが発生しました。', 'error');
            }
        };


        //-------------------------------------------
        // --- イベントハンドラ ---
        //-------------------------------------------

        //--------------
        // 基本情報の保存
        //-------------
        const saveBasicInfo = () => {
            const formData = new FormData();
            formData.append('action', 'update_basic_info');
            formData.append('json_data', JSON.stringify({
                '_name': gameDesign.value.name,
                '_player_limit': gameDesign.value.player_limit,
            })); 
            sendUpdateRequest(formData);
        };


        //------------
        //カード関連
        //-------------

        // カードの追加
        const addCard = () => {
            if (!newCardName.value) {
                displayMessage('カード名を入力してください。', 'error');
                return;
            }
            const formData = new FormData();
            const imageInput = document.getElementById('new-card-image'); // ファイルinputは直接参照
            
            formData.append('action', 'add_new_card');
            formData.append('json_data', JSON.stringify({ '_name': newCardName.value }));
            if (imageInput && imageInput.files.length > 0) {
                formData.append('_card_image', imageInput.files[0]);
            }
            
            sendUpdateRequest(formData);
            newCardName.value = ''; // フォームをリセット
            if (imageInput) imageInput.value = '';
        };

        //カードの所属フィールド変更
        const updateCardInitialField = (card) => {
            const formData = new FormData();
            formData.append('action', 'update_card_initial_field');
            
            const jsonData = {
                card_id: card.id,
                field_type: card.initial_field
            };
            formData.append('json_data', JSON.stringify(jsonData));
            
            sendUpdateRequest(formData);
        };
        
        //-------------
        //フィールド関連
        //-------------


        // フィールド種類の追加
        const addFieldType = (category) => {
            if (!newFieldTypeName.value) {
                displayMessage('フィールド種類名を入力してください。', 'error');
                return;
            }
            const formData = new FormData();
            // バックエンドの仕様に合わせて 'add_public_field' などに変更
            formData.append('action', `add_${category.toLowerCase()}_field_type`);
            formData.append('json_data', JSON.stringify({ 'field_type': newFieldTypeName.value }));
            
            sendUpdateRequest(formData);
            newFieldTypeName.value = ''; // フォームをリセット
        };


        // フィールドの追加
        const addVirtualField = (category, field_type) => {
            if (!newFieldName.value) {
                displayMessage('フィールド名を入力してください。', 'error');
                return;
            }

            // 1. まずJavaScriptオブジェクトを作成
            let jsonData = {
                'field_type': field_type,
                'field_name': newFieldName.value
            };

            // 2. Personalフィールドの場合、そのオブジェクトに target_player プロパティを追加
            if (category === 'Personal') {
                // newFieldTargets.value が { myself: true, others: false } のような
                // オブジェクトであることを想定しています
                jsonData.target_player = newFieldTargets.value;
            }

            const formData = new FormData();
            formData.append('action', `add_virtual_${category.toLowerCase()}_field`);
            
            // 3. 最終的に完成したオブジェクトをJSON文字列に変換して追加
            formData.append('json_data', JSON.stringify(jsonData));
            
            sendUpdateRequest(formData);
            newFieldName.value = ''; // フォームをリセット
            newFieldTargets.value = { myself: false, others: false }; // チェックボックスもリセット
        };



        //フィールド詳細の変更
        const saveVirtualFieldChanges = () => {
            // editingFieldDataが存在しない場合は何もしない
            if (!editingFieldData.value) {
                displayMessage('編集対象のフィールドが選択されていません。', 'error');
                return;
            }
            const formData = new FormData();
            formData.append('action', 'update_virtual_field');

            const jsonData = {
                category_name: selectedFieldCategory.value, 
                field_type :selectedFieldType.value, 
                field_name: selectedField.value,     
                field_data: editingFieldData.value 
            };

            formData.append('json_data', JSON.stringify(jsonData));
            sendUpdateRequest(formData);
        };
        
        // 公開ステータスの変更
        const publishChange = (status) => {
            const formData = new FormData();
            formData.append('action', 'publish_change');
            formData.append('json_data', JSON.stringify({ status: status })); // 'publish' or 'unpublish'
            sendUpdateRequest(formData);
        };
        
        // フィールド選択処理
        const selectField = (fieldName, fieldTypeName, category) => {
            selectedField.value = fieldName;
            selectedFieldType.value = fieldTypeName;
            selectedFieldCategory.value = category;
        };


        // --- 4. ライフサイクルフック ---

        // コンポーネントがマウントされた後に初期データを取得
        onMounted(async () => {
            const editor = document.getElementById('game-editor-app');
            const gameDesignId = editor.dataset.gameDesignId;
            try {
                const response = await fetch(`/rooms/get_game_design_data/${gameDesignId}/`);
                const result = await response.json();
                if (result.status === 'success' && result.game_design) {
                    gameDesign.value = result.game_design;
                } else {
                    throw new Error(result.message || '初期データの読み込みに失敗しました。');
                }
            } catch (error) {
                console.error('Initialization Error:', error);
                displayMessage(error.message, 'error');
            }
        });


        // --- 5. テンプレートへ公開 ---
        return {
            gameDesign,
            selectedField,
            selectedFieldCategory,
            newCardName,
            newFieldTypeName,
            newFieldName,
            feedback,
            editingFieldData,
            newFieldTargets,
            
            saveBasicInfo,
            addCard,
            addVirtualField,
            addFieldType,
            publishChange,
            selectField,
            saveVirtualFieldChanges,
            updateCardInitialField,
        };
    }
}).mount('#game-editor-app');