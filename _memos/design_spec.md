# BodogeSmith 設計仕様書

> 作成日: 2026-06-10

---

## はじめに

BodogeSmith は「どんなカードゲームでも作れる・遊べる」ことを目指した汎用マルチプレイヤーカードゲームプラットフォームである。ユーザーはカードゲームのルールをコードではなくブラウザ上のGUIで設計し、作成したゲームを複数人でリアルタイムに遊ぶことができる。

このドキュメントは、システム全体の設計思想・データ構造・各機能の仕様を記述したものである。初めてこのプロジェクトに触れる開発者が全体像を把握できるように書かれている。

---

## 1. システム全体の構成

### 技術スタック

| 役割 | 技術 |
|------|------|
| Webフレームワーク | Django 5.x |
| リアルタイム通信 | Django Channels 4.x（WebSocket） |
| ASGIサーバー | Daphne |
| データバリデーション | Pydantic |
| データベース（開発） | SQLite3 |
| データベース（本番） | PostgreSQL（Heroku経由） |

### Djangoアプリ構成

```
BodogeSmith/
├── BodogeSmith/        ← プロジェクト設定（settings, urls, asgi）
├── account/            ← ユーザー認証
├── game_factory/       ← ゲームの作成・管理・プレイ（メインアプリ）
│   ├── models/
│   │   ├── card.py
│   │   ├── card_status_for_user_model.py  ← Pydanticモデル
│   │   ├── field_card_design_model.py     ← Pydanticモデル
│   │   ├── field_cardInfo_model.py        ← Pydanticモデル
│   │   ├── field_card_info_to_send_model.py ← Pydanticモデル
│   │   ├── game.py
│   │   ├── game_design.py
│   │   ├── game_factory.py
│   │   └── room.py
│   ├── consumers/
│   │   ├── waiting_room_consumer.py
│   │   └── playing_room_consumer.py
│   ├── templates/
│   ├── static/
│   ├── views.py
│   └── urls.py
└── _memos/             ← 設計メモ・ドキュメント
```

---

## 2. ページ構成と画面遷移

### 2-1. ページ一覧

このアプリには以下の主要ページが存在する。

```
Home（マイページ）
  ├─ 部屋を作る  → 待機部屋
  ├─ 部屋に参加  → 待機部屋
  │
  ├─ ゲーム一覧（自分が作ったもの）
  │    └─ クリック → ゲーム編集ページ
  │
  └─ 新規ゲーム作成 → ゲーム作成（3段階）
                        ├─ カードセット作成・編集
                        ├─ フィールドデザイン作成・編集
                        └─ ゲーム作成・編集（CardSet + FieldDesignを組み合わせる）

待機部屋
  └─ GameMasterが締め切る → 遊び部屋（全員自動遷移）

遊び部屋（WebSocket常時接続）
```

### 2-2. Home（マイページ）

**URL:** `/`

Homeページはログインユーザーの作業起点となるページである。大きく分けて「部屋関連」と「ゲーム設計関連」の2つの機能を提供する。

**部屋関連:**
- 「部屋を作る」ボタンを押すと、部屋名とパスワードを入力するフォームが表示される。作成すると自動的にその部屋の待機部屋へ遷移する。部屋を作ったユーザーは自動的にその部屋のGameMaster（オーナー）になる。
- 「部屋に参加する」ボタンを押すと、部屋名とパスワードを入力するフォームが表示される。正しいパスワードが入力されると待機部屋へ遷移する。

**ゲーム設計関連:**
- 自分が作成した`GameDesign`の一覧が表示される。各ゲームをクリックすると編集ページへ遷移できる。
- 「新規ゲーム作成」ボタンで新しいゲームを作り始めることができる。

### 2-3. 待機部屋

**URL:** `/rooms/waiting/<room_id>/`  
**WebSocket:** `ws/game_factory/rooms/waiting/<room_id>/`

待機部屋は、ゲームが始まる前に参加者が集まる場所である。

**参加者全員に共通の動作:**
- ページを開くと即座にWebSocket接続が確立される。
- 現在この部屋に参加しているメンバーの一覧がリアルタイムで表示される（誰かが入退室するたびに更新される）。
- ページを閉じる・ブラウザバックするなどしてWebSocket接続が切れた場合、そのユーザーは`playing_members`から自動的に除外される（ただし、部屋がすでに締め切られた後は除外しない）。

**GameMaster（部屋オーナー）のみの動作:**
- 「どのゲームで遊ぶか」を選択するUIが表示される（公開済みで、現在の参加人数以上のプレイヤー上限を持つ`GameDesign`の一覧）。
- ゲームを選択し「部屋を締め切る」ボタンを押すと、以下が一連で実行される：
  1. `room.close_room()` — 部屋のステータスを`CLOSED`に変更
  2. `GameFactory.create_and_set_game(game_design_id, room)` — Gameインスタンスを生成してDBに保存し、Roomに紐付ける
  3. WebSocketで部屋全員に`redirect_to_playing`メッセージを送信
  4. 全員が自動的に遊び部屋へリダイレクトされる

**アクセス制御:**
- `playing_members`に含まれないユーザーがURLを直接入力してアクセスしようとした場合、部屋参加フォームへリダイレクトされる。
- 部屋がすでに`CLOSED`の場合、`playing_members`のユーザーは遊び部屋へリダイレクト、そうでないユーザーは参加不可のメッセージが表示される。

### 2-4. 遊び部屋

**URL:** `/rooms/playing/<room_id>/`  
**WebSocket:** `ws/game_factory/rooms/playing/<room_id>/`

遊び部屋は、実際にゲームをプレイする場所である。WebSocketで常時接続されており、全てのカード操作がリアルタイムで全員に反映される。

**画面の構成:**
- `_field_card_design_dict`（フィールドの設計図）に従って、各フィールドが画面上の指定された位置・サイズで表示される。
- 各フィールドには、自分向けに整形された`field_card_info_to_send`に従ってカードが表示される。
- 自分が操作できるフィールドのカードはドラッグ&ドロップで移動できる。

**カード操作の排他制御（ロック方式）:**

複数のプレイヤーが同じカードを同時に触ることを防ぐため、以下のロック機構を実装する。

1. プレイヤーAがカードを「つかむ」（mousedown / touchstart）
   → `card_lock` メッセージをサーバーに送信
   → サーバーは全員に「カードIDがAにロックされた」を通知
   → 他のプレイヤーの画面でそのカードがグレーアウトされ、操作不能になる

2. プレイヤーAがカードをフィールドに「置く」（mouseup / touchend）
   → `card_move` メッセージをサーバーに送信（`card_id`, `from_path`, `to_path` を含む）
   → サーバーが`game.move_card_fromAtoB()`を実行してDBを更新
   → サーバーが各プレイヤー向けの最新`field_card_info_to_send`を個別に配信
   → 全員の画面でカードが移動先へ移動するアニメーションが再生される
   → ロックが解除される

3. プレイヤーAがカードを「つかんだまま離す」（元の場所に戻す操作）
   → `card_unlock` メッセージをサーバーに送信
   → ロックが解除される

**その他の操作:**
- フィールドのシャッフル: `shuffle`メッセージ → `game.shuffle()`実行 → 全員に配信
- 操作の取り消し（Undo）: `rewind`メッセージ → `game.rewind()`実行 → 全員に配信

### 2-5. ゲーム作成（3段階構成）

ゲーム作成は「カードセット作成」「フィールドデザイン作成」「ゲーム作成」の3段階に分離する。この分離の理由は**再利用性**にある。例えば「トランプ52枚」というカードセットを一度作っておけば、大富豪・七並べ・ポーカーなど複数のゲームでそのカードセットを使い回すことができる。同様に「2人対戦レイアウト」というフィールドデザインを一度作れば、異なるカードゲームに同じフィールドを使い回せる。

#### 2-5-a. カードセット作成

**URL:** `/card_sets/<id>/edit/`

カードセットは「カードの集合体」を定義する場所である。例えば「トランプ」なら52枚のカードそれぞれに名前と画像を設定する。

機能:
- カードセットの名前を設定する
- カードを追加・編集・削除する。各カードには`名前`と`画像（任意）`を設定できる

#### 2-5-b. フィールドデザイン作成

**URL:** `/field_designs/<id>/edit/`

フィールドデザインは「ゲームボードのレイアウト」を定義する場所である。ここで「どこに何というフィールドがあり、どのように表示されるか」を一人称視点で設計する。

ここで重要なのは、**「一人称視点で設計する」** という考え方である。手札は自分の手前に表示され、山札は中央に、相手の手札は奥に表示される——というように、自分（Myself）を中心とした視点でレイアウトを設計する。このレイアウトがそのままゲームプレイ時の画面構成になる。

操作:
- フィールドをドラッグ&ドロップでキャンバス上に配置（PowerPointのように図形を操作するイメージ）
- フィールドをクリックして選択し、サイドパネルでプロパティを設定

**実装方針の補足:**  
DnDエディタはフロントエンドの実装コストが高いため、まず「`position`・`dimensions`を数値テキストボックスで直接入力する」形で機能を実現し、DnD操作はその後の改善として追加する。

#### 2-5-c. ゲーム作成

**URL:** `/game_designs/<id>/edit/`

ゲーム作成では、カードセットとフィールドデザインを組み合わせて「実際に遊べるゲーム」として定義する。

機能:
- 使用するカードセットを選択する
- 使用するフィールドデザインを選択する
- ゲーム開始時（初期状態）でどのカードをどのPublicフィールドに置くかを設定する（後述）
- プレイヤー上限人数を設定する
- 公開・非公開の切り替えをする（公開されたゲームのみ部屋で選択できる）

**3段階の独立性:**  
カードセット作成・フィールドデザイン作成・ゲーム作成はそれぞれ独立したページであり、Homeからいつでも好きなものにアクセスできる。ただし、ゲーム作成ページはCardSetとFieldDesignが存在しない状態では設定できる項目がなく、実質的に何もできない。

**カード初期配置UIの仕様（現時点）:**  
カード一覧をチェックボックスで選択し、対象のPublicフィールドを指定して一括配置する形式とする。将来的にはカードの並び順（スタックの上下関係）も定義できるようにする必要があるが、現時点では未解決問題として保留する。

---

## 3. データ設計の根本思想

ゲームに関するデータ設計を理解するには、まず「神目線」と「User目線」という2つの視点の違いを理解する必要がある。

### 3-1. 神目線とUser目線

**神目線のデータ** とは、全てのカードの本当の情報（どこに何のカードがあるか）を知っているデータである。プレイヤーが誰でも、山札に何のカードが積まれているか、相手の手札が何かを全て知っている。これがデータベースに保存される真実のデータである。

**User目線のデータ** とは、ある特定のプレイヤーの視点から見た情報である。自分の手札は表向きに見えるが、山札は裏向きに見える。相手の手札も裏向きに見える。このように「どのプレイヤーにとって、あるカードがどう見えるか」という情報はプレイヤーによって異なる。

ゲームの処理の流れは以下のようになる：

```
【ゲーム設計時】
フィールドの設計図（field_card_design_dict）を一人称視点で作成する。
どこに手札があり、どこに山札があるか。
この段階ではまだ何人で遊ぶかが未定であるため、
「相手の手札エリア」は人数に依存しない形で定義される。

【ゲーム開始時（人数確定後）】
GameFactory が field_card_design_dict と初期カード配置情報をもとに
Game インスタンスを生成する（これが「神目線のデータ」の誕生）。
この時点で初めて、何人のプレイヤーが参加するかが確定し、
Personal フィールドがプレイヤー人数分だけ初期化される。

【プレイ中】
プレイヤーAがカードを動かす
  ↓
WebSocket 経由でサーバーに to_path / from_path が送られる
  ↓
サーバーが「神目線のデータ」（field_cardInfo_dict）を更新する
  ↓
各プレイヤー向けに「User目線のデータ」（field_card_info_to_send）を生成する
  ↓
WebSocket 経由で各プレイヤーに個別に送信する
  ↓
各プレイヤーの画面が更新される
```

### 3-2. 人数未定という制約

フィールドデザインを設計する段階では、何人でゲームをプレイするかが未定である。これはデータ設計上の重要な制約になる。

例えば「手札」というPersonalフィールドを考えると、ゲームプレイ時には「プレイヤー1の手札」「プレイヤー2の手札」……というように人数分のデータが必要になる。しかし設計段階ではこれを`{player_id: [cards]}`という構造であらかじめ定義することはできない。

この問題への対処として、設計段階（`FieldDesign`・`GameDesign`）では**フィールドの「種類」と「見た目」のみを定義し、プレイヤーごとの具体的なデータ構造はGame生成時（人数確定後）に初めて作られる**という設計にしている。

具体的には:
- 設計時: `Personal.Hand` という「手札」フィールドが存在することだけを定義する
- Game生成時: `Personal.Hand = {player1.id: [], player2.id: [], ...}` というように人数分展開される

---

## 4. Djangoモデル設計

### 4-1. `CardSet`（カードセット）

カードの集合体を管理するモデルである。複数の`GameDesign`から再利用できる。

```python
class CardSet(models.Model):
    _name    = CharField(max_length=100, unique=True)
    _creater = ForeignKey(Account, on_delete=SET_NULL, null=True)
    _cards   = ManyToManyField(Card, blank=True)
```

---

### 4-2. `Card`（カード1枚）

1枚のカードを表すモデル。`CardSet`を通じて`GameDesign`に紐付く。

```python
class Card(models.Model):
    _name       = CharField(max_length=100)
    _card_image = ImageField(upload_to='card_images/', blank=True, null=True)
```

プロパティ:
- `name`: カード名
- `image`: カード画像（`ImageFieldFile`）
- `to_dict()`: `{card_id, card_name, card_url}` の辞書を返す（field_cardInfo_dictに格納する形式）

---

### 4-3. `FieldDesign`（フィールドデザイン）

フィールドのレイアウト・表示設定を管理するモデル。  
内部的には`_field_card_design_dict`というJSONフィールドでデータを保持し、Pydanticモデル（`FieldCardDesignModel`）を通じてバリデーションと操作を行う。

```python
class FieldDesign(models.Model):
    _name                   = CharField(max_length=100, unique=True)
    _creater                = ForeignKey(Account, on_delete=SET_NULL, null=True)
    _field_card_design_dict = JSONField(default=dict)
    # ↑ FieldCardDesignModel として読み書きされる
```

フィールドの追加・更新などの操作は、Pydanticキャッシュオブジェクトを通じて行われる（§5で詳述）。

---

### 4-4. `GameDesign`（ゲームデザイン）

カードセットとフィールドデザインを組み合わせて「遊べるゲーム」として定義するモデル。カードの初期配置情報を持つ。

```python
class GameDesign(models.Model):
    _name                    = CharField(max_length=100, unique=True)
    _creater                 = ForeignKey(Account, on_delete=SET_NULL, null=True)
    _published               = BooleanField(default=False)
    _player_limit            = IntegerField(default=10)

    _card_set                = ForeignKey(CardSet, on_delete=SET_NULL, null=True)
    _field_design            = ForeignKey(FieldDesign, on_delete=SET_NULL, null=True)

    # カードの初期配置（どのPublicフィールドに最初どのカードがあるか）
    _init_field_cardInfo_dict = JSONField(default=dict)
    # ↑ FieldCardInfoModel として読み書きされる
```

`_init_field_cardInfo_dict` はPublicフィールドへの初期配置のみを定義する。Personalフィールドは人数確定後に初めて展開されるため、ここでは定義しない。

---

### 4-5. `Game`（ゲームインスタンス）

実際にプレイ中のゲームを表すモデル。`GameFactory`によって`GameDesign`から生成される。神目線のデータを全て保持している。

```python
class Game(models.Model):
    _name                      = CharField(max_length=100)
    _created_at                = DateTimeField(auto_now_add=True)
    _players                   = ManyToManyField(Account)      # 参加プレイヤー
    _cards                     = ManyToManyField(Card)         # ゲーム内の全カード
    _game_log                  = JSONField(default=list)       # 操作履歴
    _player_id_order           = JSONField(default=list)       # プレイヤーの順番
    _field_card_design_dict    = JSONField(default=dict)       # フィールドの設計図（FieldDesignからコピー）
    _field_cardInfo_dict       = JSONField(default=dict)       # 神目線: 現在のカード位置
    _card_status_for_user_dict = JSONField(default=dict)       # 各Userからのカードの見え方
```

Gameモデルが持つ主要なメソッド:

| メソッド | 説明 |
|---------|------|
| `move_card_fromAtoB(card_id, from_path, to_path)` | カードを別フィールドへ移動する |
| `shuffle(field, direct)` | フィールドのカードを疑似シャッフルする |
| `add_log(func, args, user_id, exp)` | 操作ログを記録する |
| `rewind()` | 最後の操作を取り消す（ログを参照して逆操作を実行） |
| `initialize_game_info(cards, players, init_card_info_model)` | ゲーム開始時の初期化 |
| `create_fci_for_user_dict(user_id)` | 特定Userへの送信データを生成する |

---

### 4-6. `Room`（部屋）

参加するプレイヤーを管理し、`Game`インスタンスへの参照を持つモデル。

```python
class Room(models.Model):
    _name            = CharField(max_length=100, unique=True)
    _password        = CharField(max_length=128)   # ハッシュ化済み
    _created_at      = DateTimeField(auto_now_add=True)
    _owner           = ForeignKey(Account, ...)    # GameMaster
    _status          = CharField(choices=[OPEN, CLOSED])
    _playing_members = ManyToManyField(Account)    # 参加中のメンバー
    _game            = ForeignKey(Game, null=True) # プレイ中のGame（未開始はNull）
```

ステータスは`OPEN`（募集中）と`CLOSED`（締切済み）の2種類。締め切られた後は新規メンバーの参加ができない。

---

### 4-7. `GameFactory`（ファクトリクラス）

`GameDesign`と`Room`の情報から`Game`インスタンスを生成するユーティリティクラス。Djangoモデルではなく、ファクトリパターンで実装されている。

```python
class GameFactory:
    @classmethod
    def create_and_set_game(cls, game_design_id: int, room: Room) -> Game:
        # 1. GameDesignを取得し、プレイヤー数のチェック
        # 2. Game インスタンスの基本情報を設定（name, field_card_design_dict）
        # 3. game.initialize_game_info() を呼び出し、
        #    Personalフィールドをプレイヤー人数分展開し、
        #    card_status_for_user_dict の初期値を設定する
        # 4. Room に Game を紐付けて保存
```

---

## 5. JSONデータ構造の仕様

ゲームに関するデータは複数のJSONフィールドで管理されている。Pydanticモデルを通じてバリデーションされる。

### 5-1. `_field_card_design_dict` — フィールドの設計図

**保持するモデル:** `FieldDesign`, `Game`  
**Pydanticモデル:** `FieldCardDesignModel`

このJSONは「どこにどんなフィールドがあり、どのように表示されるか」を定義する。ゲーム設計時に`FieldDesign`として保存され、ゲーム開始時に`Game`にコピーされる。

```json
{
  "Personal": {
    "<field_type名>": {
      "<field名>": {
        "target_player": {
          "myself": true,
          "others": false
        },
        "card_num_limit": [0, 99],
        "reversible": false,
        "design": {
          "position": [50, 80],
          "dimensions": [100, 200],
          "display_card_maxnum": 5,
          "init_reverse": true
        }
      }
    }
  },
  "Public": {
    "<field_type名>": {
      "<field名>": {
        "card_num_limit": [0, 99],
        "reversible": false,
        "design": {
          "position": [200, 80],
          "dimensions": [80, 120],
          "display_card_maxnum": 1,
          "init_reverse": false
        }
      }
    }
  }
}
```

**構造の説明:**

トップレベルは`Personal`と`Public`の2つに分かれる。

- **`Personal`** — プレイヤーごとに個別に持つフィールドの定義。「手札」が代表例。  
  `field_type` → `field名` → フィールド設定 という3階層になっている。
  
- **`Public`** — 全プレイヤーで共有するフィールドの定義。「山札」「捨て札」が代表例。  
  Publicの`field_type`には仮想フィールド（`field名`）が**必ず1つだけ**存在するという制約がある（Pydanticバリデーターで強制）。

**各プロパティの説明:**

| プロパティ | 型 | 説明 |
|-----------|------|------|
| `target_player.myself` | bool | このフィールドに自分（カード操作者本人）のカードを表示するか |
| `target_player.others` | bool | このフィールドに他のプレイヤーのカードを表示するか |
| `card_num_limit` | [int, int] | このフィールドに置けるカード枚数の[最小, 最大] |
| `reversible` | bool | このフィールドでカードを手動で表裏反転できるか（山札などはFalse） |
| `design.position` | [int, int] | フィールドの左上座標 [x, y]（px） |
| `design.dimensions` | [int, int] | フィールドの [幅, 高さ]（px） |
| `design.display_card_maxnum` | int | 実際に画面に並べて表示するカードの最大枚数 |
| `design.init_reverse` | bool | ゲーム開始時にこのフィールドのカードが裏向きか |

**`display_card_maxnum`の補足:**  
例えばOthersの手札エリアは`1`にしておけば、相手が何人いても横に広がりすぎない。手札は`5`などにしておくと一覧性が高い。山札は基本`1`。なおこれは「表示枚数の上限」であり、実際にフィールドにあるカードの枚数には影響しない。

**Personalにおける`myself`と`others`の意味:**

一人称視点の設計では、同じ「手札」という`field_type`に対して、通常2種類のフィールドが定義される:

- `myself: true, others: false` のフィールド → 自分の手札をどう見せるか（自分だけに見える。表向き）
- `myself: false, others: true` のフィールド → 他の人の手札をどう見せるか（他の人の視点から見た相手の手札。裏向きが多い）

こうすることで「自分の手札は見えるが、相手の手札は裏向き」という状態を表現できる。

**`others`フィールドは「コンテナ」として扱う:**

`others: true`のフィールドは、HTMLのコンテナ要素（`<div>`など）に相当する概念として設計する。`position`と`dimensions`はそのコンテナ全体の位置・サイズを指定し、コンテナ内部にゲームプレイ時（人数確定後）に参加プレイヤーの人数分の子要素が自動生成される。子要素はコンテナ内で等間隔に並べられる。これにより設計段階では人数が未定でも、コンテナの枠だけを設計しておけばよい。

---

### 5-2. `_init_field_cardInfo_dict` / `_field_cardInfo_dict` — カードの位置情報

**保持するモデル:** `GameDesign`（`_init_field_cardInfo_dict`）, `Game`（`_field_cardInfo_dict`）  
**Pydanticモデル:** `FieldCardInfoModel`

このJSONは「今どのフィールドにどのカードがあるか」を表す神目線のデータである。

```json
{
  "Public": {
    "<field_type名>": [
      {
        "card_id": 1,
        "card_name": "ハートのA",
        "card_url": "/media/card_images/heart_ace.png"
      },
      {
        "card_id": 2,
        "card_name": "ハートの2",
        "card_url": "/media/card_images/heart_2.png"
      }
    ]
  },
  "Personal": {
    "<field_type名>": {
      "<user_id(整数)>": [
        {
          "card_id": 10,
          "card_name": "スペードのK",
          "card_url": "/media/card_images/spade_k.png"
        }
      ]
    }
  }
}
```

**`GameDesign`の`_init_field_cardInfo_dict`:**  
ゲーム開始前の初期配置を定義する。ここでは**Publicフィールドへの初期配置のみ**を設定できる。Personalフィールドは人数が確定してから初めて展開されるため、設計段階では定義しない。

例えばトランプゲームであれば「Deckというフィールドに52枚全部置いておく」という状態を設定する。

**`Game`の`_field_cardInfo_dict`:**  
プレイ中の現在のカード位置を表す。ゲーム開始時に`GameDesign._init_field_cardInfo_dict`をベースにPersonalフィールドを展開して初期化される。カードが移動するたびにこのJSONが更新される。

---

### 5-3. `_card_status_for_user_dict` — Userごとのカードの見え方

**保持するモデル:** `Game`  
**Pydanticモデル:** `CardStatusForUserModel`

このJSONは「あるプレイヤーから見て、あるカードがどのように見えるか」を管理する。神目線のカード位置データ（`_field_cardInfo_dict`）はどのプレイヤーにとっても同じだが、カードの「見え方」はプレイヤーによって異なる。この違いをこのJSONが表現する。

```json
{
  "users": {
    "<user_id(整数)>": {
      "<card_id(整数)>": {
        "reverse": true
      }
    }
  }
}
```

`reverse: true` はそのプレイヤーからそのカードが裏向きに見えることを意味する。

**初期値の設定:**  
ゲーム開始時、各カードが最初に置かれているPublicフィールドの`init_reverse`の値がそのカードの初期`reverse`値として全プレイヤー分設定される。

**カード移動時の更新:**  
`move_card_fromAtoB()`が呼ばれると、`_card_status_for_user_dict`も同時に更新される。  
移動先フィールドの`init_reverse`を参照して、全プレイヤーのそのカードの`reverse`値を更新する。  
- 移動先がPublicフィールドの場合: そのPublicフィールドの`init_reverse`で全員一律に設定
- 移動先がPersonalフィールドの場合:
  - 自分（`myself`が`true`のフィールド）の視点では`myself`フィールドの`init_reverse`が適用される
  - 他のプレイヤーの視点では`others`フィールドの`init_reverse`が適用される

**将来的な拡張候補:**
- `locked_by: user_id | null` — どのユーザーがこのカードをロック中かを表す（排他制御に使用）

---

### 5-4. `field_card_info_to_send` — Userへの送信データ

**Pydanticモデル:** `FieldCardInfoToSendModel`  
**生成メソッド:** `game.create_fci_for_user_dict(user_id)`

このデータは`_field_cardInfo_dict`と`_card_status_for_user_dict`を特定のUser向けに合成したもので、WebSocketで各プレイヤーに個別に送信される。

```json
{
  "Personal": {
    "<field_type名>": {
      "<field名>": {
        "<user_id(整数)>": [
          {
            "card_info": {
              "card_id": 10,
              "card_name": "スペードのK",
              "card_url": "/media/card_images/spade_k.png"
            },
            "card_status": {
              "reverse": false
            }
          }
        ]
      }
    }
  },
  "Public": {
    "<field_type名>": {
      "<field名>": [
        {
          "card_info": {
            "card_id": 1,
            "card_name": "ハートのA",
            "card_url": "/media/card_images/heart_ace.png"
          },
          "card_status": {
            "reverse": true
          }
        }
      ]
    }
  }
}
```

**`_field_cardInfo_dict`との構造上の違い:**  
- `_field_card_design_dict`の構造（`field_type` → `field名` → ...）に合わせた形になっている
- カード情報（`card_info`）と表示状態（`card_status`）がペアになっている
- `reverse: true`のカードは`card_info`の内容が`null`に置き換えられる（裏向きのカードの名前・画像は見えない）。ただし`card_id`だけはカード選択等のUI操作のために送る
- `display_card_maxnum`の枚数分だけカードが含まれる（それ以上のカードはフロントに送らない）

---

## 6. Pydanticモデルとキャッシュ機構

### 6-1. なぜPydanticを使うのか

DjangoのJSONFieldは単純なPython dictとして扱われ、バリデーションの仕組みがない。例えばフィールド名がPersonalとPublicで重複してはいけない、Publicのfield_typeには仮想フィールドが1つしか持てない、といった制約をJSONFieldだけでは強制できない。

そこでPydanticを使い、JSONデータを読み書きする際に必ずPydanticモデルを経由させることで、型チェックとバリデーションを自動的に行う仕組みを作っている。

### 6-2. キャッシュオブジェクトのパターン

DBからJSONを読み出してPydanticモデルに変換するコストを毎回払わないよう、**キャッシュオブジェクト**というパターンを採用している。

```python
# GETTERの例（game_design.py）
@property
def field_card_design_cacheobj(self) -> FieldCardDesignModel:
    # 初回アクセス時だけDBのJSONをPydanticモデルに変換する
    if not hasattr(self, '_field_card_design_cacheobj'):
        self._field_card_design_cacheobj = FieldCardDesignModel.parse_obj(
            self._field_card_design_dict
        )
    return self._field_card_design_cacheobj

# save()の例 — 保存時にPydanticオブジェクトをdictに変換してJSONFieldに書き戻す
def save(self, *args, **kwargs):
    if hasattr(self, '_field_card_design_cacheobj'):
        self._field_card_design_dict = self._field_card_design_cacheobj.dict()
    super().save(*args, **kwargs)
```

**重要なルール:** Pydanticキャッシュオブジェクトの値を変えるときは、直接プロパティを書き換えてはいけない。必ずSETTERメソッド（`_set_field_card_design_cacheobj()`など）を呼ぶ。これはPydanticの一部フィールドを書き換えてもバリデーターが再実行されないためで、SETTERを経由することで常にモデル全体の整合性チェックが走ることを保証している。

---

## 7. WebSocket通信設計

### 7-1. 技術的背景

通常のHTTPリクエストはクライアントからサーバーへの一方的な通信だが、WebSocketは双方向の常時接続を維持できる。遊び部屋では複数のプレイヤーが行ったカード操作をリアルタイムで全員の画面に反映する必要があるため、WebSocketを使っている。

Django ChannelsとDaphne（ASGIサーバー）を組み合わせることで、通常のDjangoの同期的な処理（HTTP）とWebSocketの非同期処理を共存させている。

### 7-2. Channel Layer とグループ

Django Channelsでは、複数のWebSocket接続をグループとして束ねることができる。同じグループ宛にメッセージを送ると、そのグループの全メンバーにメッセージが配信される（これを`group_send`と呼ぶ）。

グループ名は以下の規則で決まる：
- 待機部屋: `game_factory_<room_id>_waiting`
- 遊び部屋: `game_factory_<room_id>_playing`

### 7-3. 待機部屋Consumer（`GameFactoryWaitingRoomConsumer`）

**接続時（`connect`）:**
1. WebSocket接続を受け入れる
2. `room_id`と`user`をインスタンス変数に保存
3. 該当のグループに参加する
4. `playing_members`に含まれているか確認。含まれていなければ参加フォームへリダイレクト
5. 全員にメンバーリスト更新を送信する

**切断時（`disconnect`）:**
1. 部屋がまだ`OPEN`状態の場合、`playing_members`からユーザーを除外する
2. 全員にメンバーリスト更新を送信する
3. グループから自身を削除する

**メッセージ受信時（`receive_json`）:**

| type | 条件 | 処理 |
|------|------|------|
| `move_to_playing_room` | 送信者がオーナーのみ有効 | `room.close_room()`実行 → 全員に`redirect`を送信 |

**サーバーから各Clientへの送信:**

| type | 内容 |
|------|------|
| `members_update` | 現在の`playing_members`のユーザー名一覧 |
| `redirect` | リダイレクト先URL |

### 7-4. 遊び部屋Consumer（`GameFactoryPlayingRoomConsumer`）

**接続時（`connect`）:**
1. WebSocket接続を受け入れる
2. グループに参加する
3. `playing_members`でなければ参加フォームへリダイレクト
4. Gameがすでに存在する場合（再接続などの場合）、`field_card_design_dict`と`field_card_info_to_send`を送信する

**メッセージ受信時（`receive_json`）:**

| type | ペイロード | 処理 |
|------|-----------|------|
| `game_choice` | `{game_design_id}` | `GameFactory.create_and_set_game()`でGameを生成し、全員に設計図とカード情報を配信 |
| `move_card` | `{card_id, from_path, to_path}` | `game.move_card_fromAtoB()`を実行し、全員にカード情報を配信 |
| `shuffle` | `{place, direct}` | `game.shuffle()`を実行し、ログに記録 |
| `rewind` | なし | `game.rewind()`で最後の操作を取り消す（誰でも使用可能） |
| `restart` | なし | **GMのみ使用可能。** ゲームログ・カード位置・カードステータス全てを`GameDesign`の初期状態に完全リセットする |
| `card_lock` | `{card_id}` | カードをロック中状態にし、全員に通知（未実装、追加予定） |
| `card_unlock` | `{card_id}` | カードのロックを解除し、全員に通知（未実装、追加予定） |

**`move_card`の`from_path` / `to_path`フォーマット:**

```json
// Publicフィールドの場合: ["Public", "<field_type名>"]
"from_path": ["Public", "Deck"]

// Personalフィールドの場合: ["Personal", "<field_type名>", <user_id(整数)>]
"to_path": ["Personal", "Hand", 3]
```

**サーバーから各Clientへの送信:**

| type | 内容 |
|------|------|
| `field_card_design_update` | フィールドの設計図（`_field_card_design_dict`） |
| `field_cardInfo_update` | そのUserに向けた`field_card_info_to_send` |
| `lock_update` | ロック中のカード情報（`{card_id: user_id}`のdict）（追加予定） |
| `redirect` | リダイレクト先URL |

---

## 8. URLとビュー設計

### 8-1. URL一覧

| URL | ビュー関数 | 説明 |
|-----|----------|------|
| `/` | `home` | マイページ |
| `/rooms/create/` | `create_room` | 部屋作成フォーム（GET/POST） |
| `/rooms/join/` | `join_room` | 部屋参加フォーム（GET/POST） |
| `/rooms/waiting/<room_id>/` | `waiting_room` | 待機部屋 |
| `/rooms/playing/<room_id>/` | `playing_room` | 遊び部屋 |
| `/card_sets/create/` | `create_card_set` | カードセット新規作成 |
| `/card_sets/<id>/edit/` | `edit_card_set` | カードセット編集 |
| `/field_designs/create/` | `create_field_design` | フィールドデザイン新規作成 |
| `/field_designs/<id>/edit/` | `edit_field_design` | フィールドデザイン編集 |
| `/game_designs/create/` | `create_game_design` | ゲーム新規作成 |
| `/game_designs/<id>/edit/` | `edit_game_design` | ゲーム編集 |
| `/game_designs/<id>/update/` | `update_game_design` | ゲーム更新API（POST） |
| `/game_designs/<id>/data/` | `get_game_design_data` | ゲームデータ取得API（GET） |

### 8-2. ゲーム更新API（`update_game_design`）

`/game_designs/<id>/update/` へのPOSTリクエストを受け付け、`action`パラメータによって処理を振り分けるAPIエンドポイント。フロントエンドとのやり取りはJSON（multipart含む）で行う。

| `action` | 処理内容 |
|----------|---------|
| `update_basic_info` | ゲーム名・プレイヤー上限の更新 |
| `add_new_card` | カードセットへのカード追加（画像あり） |
| `update_card` | カードの名前・画像の更新 |
| `update_card_initial_field` | カードの初期配置（どのPublicフィールドに入れるか）の設定 |
| `add_personal_field_type` | Personalのfield_typeを追加 |
| `add_public_field_type` | Publicのfield_typeを追加 |
| `add_virtual_personal_field` | Personalの仮想フィールド（field名）を追加 |
| `add_virtual_public_field` | Publicの仮想フィールド（field名）を追加 |
| `update_virtual_field` | 仮想フィールドのプロパティ更新（位置・サイズ・各設定値） |
| `publish_change` | ゲームの公開・非公開切り替え |

---

## 9. フロントエンド設計方針

### 9-1. 遊び部屋の画面描画

ゲームボードは`_field_card_design_dict`の情報をもとに動的に構築される。

- 各フィールドは`position`と`dimensions`を使ってCSSの`position: absolute`で絶対座標配置する
- カードは`reverse: true`の場合はカード裏面画像を表示し、`false`の場合はカード表面（`card_url`の画像）を表示する
- `display_card_maxnum`の枚数分のカードを横並びに表示する（あふれた分はスクロール or 長押しで展開する形を将来的に検討）

**`others`フィールドのコンテナ描画:**  
`others: true`のフィールドはコンテナとして描画する。コンテナの`position`・`dimensions`を外枠とし、その内部に`_player_id_order`から自分（`myself`）を除いた他プレイヤーの人数分の子要素をCSSで等間隔（`flex`や均等分割など）に自動配置する。各子要素の中にそのプレイヤーのカードが表示される。

### 9-2. カード操作のDrag & Drop

カード操作の流れ:
1. `mousedown` / `touchstart`: カードをつかむ → `card_lock`をサーバーに送信
2. `mousemove` / `touchmove`: カードをドラッグ → フィールド上をホバーしているときはハイライト表示
3. `mouseup` / `touchend`: カードを離す
   - フィールドの上で離した場合: `card_move`を送信（`from_path`, `to_path`を含む）
   - フィールドの外で離した場合: `card_unlock`を送信（元の位置に戻る）

### 9-3. フィールドデザインエディタ

フィールドデザイン作成ページでは、設計者がフィールドの位置・サイズ・プロパティを設定できる。

**実装フェーズ1（まず作る）:**
- キャンバスエリア: フィールドの配置イメージを確認できる表示エリア。内部座標が`position`の座標系と一致する
- フィールドの追加・削除・選択ができる
- 選択中のフィールドの`position`・`dimensions`は**数値テキストボックスで直接入力**する
- サイドパネル: `card_num_limit`, `reversible`, `display_card_maxnum`, `init_reverse`, `target_player`（Personal/Public・myself/others）を入力・変更できる

**実装フェーズ2（後で追加）:**
- フィールドをドラッグで移動・コーナーハンドルでリサイズできるDnD操作

**Othersフィールドのプレビュー表示:**  
`others: true`のフィールドはコンテナとして点線枠で表示し、内部に「プレイヤーn人分が入るエリア」であることをダミー表示で示す（例: 点線の子枠を2〜3個並べて描画）。

---

## 10. 認証・アクセス制御

- 全ての主要ページはログインが必要（`@login_required`デコレーター）
- 部屋への入室はパスワード認証（`make_password` / `check_password`によるハッシュ化）
- ゲームデザイン・カードセット・フィールドデザインの編集は作成者本人のみ可能
- 部屋の締め切り操作はGameMaster（`_owner`）のみ可能
- WebSocket接続時にも`playing_members`への参加確認を行い、未参加ユーザーは弾く

---

## 11. ゲームログとUndoの仕組み

全てのゲーム操作は`_game_log`に記録される。

```json
[
  {
    "func": "move_card_fromAtoB",
    "args": [10, ["Personal", "Hand", 3], ["Public", "Deck"]],
    "userID": 3,
    "exp": "プレイヤー3が手札を山札に戻した",
    "timestamp": "2026-06-10T12:34:56+00:00"
  }
]
```

`game.rewind()`を呼ぶと、ログの末尾から1件取り出し、その逆の操作を実行する:
- `move_card_fromAtoB(card_id, from, to)` → `move_card_fromAtoB(card_id, to, from)` を実行
- `shuffle(field, direct)` → `shuffle(field, -direct)` を実行

---

## 12. 将来的な課題・未解決問題

- **カードのリアルタイム位置共有**: プレイヤーがカードをドラッグ中の座標をリアルタイムで全員に共有する機能（`card_dragging`メッセージ）は、WebSocketトラフィックが増えるため要検討
- **手札の拡大表示**: `display_card_maxnum`を超えるカードはスクロールまたは長押しで拡大表示する
- **カードの複数枚同時移動**: 現状は1枚ずつの移動のみ対応
- **ゲームルールのスクリプト化**: 現状はカード移動をすべて手動で行うが、将来的にはルールスクリプト（「このフィールドに特定のカードが置かれたとき自動で何かする」）を設定できるようにすることも考えられる
- **カード初期配置の並び順**: 現時点では「どのカードをどのPublicフィールドに入れるか」だけを設定できる。将来的にはスタックの上下関係（順番）も定義できるようにする必要がある
- **フィールドデザインエディタのDnD化**: 現在フェーズ1（数値入力）で実装し、フェーズ2でDnD操作を追加する
