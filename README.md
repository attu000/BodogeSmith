# BodogeSmith

カスタムカードゲームを作成・プレイできる汎用マルチプレイヤーカードゲームフレームワークです。  
ゲームのフィールドやカードをブラウザ上でデザインし、WebSocketによるリアルタイム対戦が可能です。

---

## 機能

- ユーザー登録・ログイン
- カードゲームのデザイン作成（フィールド・カード・レイアウトの設定）
- パスワード付きルームの作成・参加
- WebSocketによるリアルタイムマルチプレイヤーゲームプレイ
- カードの移動・シャッフル・巻き戻し（Undo）
- PC / モバイル対応UI

---

## 技術スタック

| 種別 | 技術 |
|------|------|
| バックエンド | Django 5.2.5 |
| WebSocket | Django Channels 4.3.1 / Daphne |
| データベース (開発) | SQLite3 |
| データベース (本番) | PostgreSQL (Heroku) |
| データバリデーション | Pydantic |
| 画像処理 | Pillow |
| フロントエンド | HTML / CSS / JavaScript |

---

## セットアップ

### 必要環境

- Python 3.11.4
- pip

### インストール手順

```bash
# 1. 仮想環境の作成・有効化
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 2. 依存パッケージのインストール
pip install -r requirements.txt

# 3. マイグレーションの実行
python manage.py migrate

# 4. 開発サーバーの起動（WebSocket対応）
daphne -b 127.0.0.1 -p 8000 UNOpj.asgi:application
```

### 環境変数

プロジェクトルートに `.env` ファイルを作成し、以下を設定してください。

```
SECRET_KEY=your-secret-key-here
```

### アクセス

- アプリ: http://127.0.0.1:8000
- 管理画面: http://127.0.0.1:8000/admin/

---

## アプリ構成

### `account` アプリ

ユーザー認証を管理します。

| URL | 機能 |
|-----|------|
| `/account/signup/` | ユーザー登録 |
| `/account/login/` | ログイン |
| `/account/logout/` | ログアウト |

### `game_factory` アプリ

カードゲームの作成・プレイを管理するメインアプリです。

| URL | 機能 |
|-----|------|
| `/` | ホーム（ゲームデザイン一覧） |
| `/rooms/create/` | ルーム作成 |
| `/rooms/join/` | ルーム参加 |
| `/rooms/waiting/<room_id>/` | 待機ロビー |
| `/rooms/playing/<room_id>/` | ゲームプレイ画面 |
| `/rooms/create_game_design/` | ゲームデザイン作成 |
| `/rooms/edit_game_design/<id>/` | ゲームデザイン編集 |
| `/rooms/choice_game/<room_id>/` | プレイするゲームの選択 |

#### WebSocket エンドポイント

| URL | 機能 |
|-----|------|
| `ws/game_factory/rooms/waiting/<room_id>/` | 待機ロビーのリアルタイム通信 |
| `ws/game_factory/rooms/playing/<room_id>/` | ゲームプレイのリアルタイム通信 |

---

## ゲームデザインの仕組み

### フィールドの種類

- **パブリックフィールド**: 全プレイヤーが共有するフィールド（デッキ・捨て札など）
- **パーソナルフィールド**: プレイヤーごとに個別のフィールド（手札など）

### カードの管理

- カードはフィールド間を `move_card_fromAtoB()` で移動
- `shuffle()` でフィールドのカードをシャッフル
- 全操作はログに記録され `rewind()` で巻き戻し可能
- カードの表示はプレイヤーごとに制御可能

### ゲームデザイン API

**POST** `/rooms/update_game_design/<id>/`

`action` パラメータで操作を指定します。

| action | 内容 |
|--------|------|
| `update_basic_info` | ゲーム名・プレイヤー上限の更新 |
| `add_new_card` | カードの追加（画像対応） |
| `update_card` | カードの編集 |
| `update_card_initial_field` | カードの初期配置設定 |
| `add_personal_field_type` | パーソナルフィールド種別の追加 |
| `add_public_field_type` | パブリックフィールド種別の追加 |
| `add_virtual_personal_field` | 仮想パーソナルフィールドの追加 |
| `add_virtual_public_field` | 仮想パブリックフィールドの追加 |
| `update_virtual_field` | フィールドのレイアウト・表示設定の変更 |
| `publish_change` | ゲームの公開・非公開切り替え |

**GET** `/rooms/get_game_design_data/<id>/`

ゲームデザインの全データ（フィールド・カード・レイアウト）をJSONで返します。

---

## デプロイ (Heroku)

```bash
# Procfile に記載されたコマンドで起動
daphne -b 0.0.0.0 -p $PORT UNOpj.asgi:application
```

本番環境では `DATABASE_URL` 環境変数により PostgreSQL に自動接続します。

---

## ディレクトリ構成

```
BodogeSmith/
├── UNOpj/              # プロジェクト設定 (settings, urls, asgi)
├── account/            # ユーザー認証アプリ
├── game_factory/       # メインゲームアプリ
│   ├── models/         # Room, Game, GameDesign, Card モデル
│   ├── consumers/      # WebSocket コンシューマー
│   ├── templates/      # HTMLテンプレート
│   └── static/         # JS / CSS (PC・モバイル対応)
├── UNO/                # UNO レガシーアプリ
├── static/             # 共通静的ファイル
├── media/              # アップロード画像
├── requirements.txt
├── Procfile
└── runtime.txt
```
