using System;

// ========== MazeGameクラス (親クラス) ==========
public class MazeGame
{
    // ★変更点: private -> protected にし、readonly を外す
    protected string[] _map = {
        "####################",
        "#S#  #      #    G#",
        "# # ## #### # ### ##",
        "# #  # #  # # # #  #",
        "# ## # ## ### # ####",
        "#    #   #   #   # #",
        "#### ### # ##### # #",
        "# #      #       # #",
        "# # ######## ##### #",
        "#                  #",
        "####################"
    };

    // ★変更点: private -> protected に変更
    protected int _playerX;
    protected int _playerY;

    // コンストラクタ: 変更なし
    public MazeGame()
    {
        _playerX = 1;
        _playerY = 1;
    }

    // DrawMapメソッド: 変更なし
    private void DrawMap()
    {
        Console.WriteLine("--------------------");
        for (int y = 0; y < _map.Length; y++)
        {
            string line = "";
            for (int x = 0; x < _map[y].Length; x++)
            {
                if (x == _playerX && y == _playerY)
                {
                    line += '@';
                }
                else
                {
                    line += _map[y][x];
                }
            }
            Console.WriteLine(line);
        }
    }

    // ★変更点: private -> protected virtual に変更
    protected virtual void MovePlayer(string direction)
    {
        int nextX = _playerX;
        int nextY = _playerY;

        switch (direction.ToLower())
        {
            case "e": nextY--; break;
            case "s": nextX--; break;
            case "d": nextY++; break;
            case "f": nextX++; break;
            default: return;
        }

        if (nextY >= 0 && nextY < _map.Length &&
            nextX >= 0 && nextX < _map[nextY].Length &&
            _map[nextY][nextX] != '#')
        {
            _playerX = nextX;
            _playerY = nextY;
        }
    }

    // Runメソッド: 変更なし
    public void Run()
    {
        while (true)
        {
            DrawMap();

            if (_map[_playerY][_playerX] == 'G')
            {
                Console.WriteLine("\n🎉 おめでとうございます！ゴールに到達しました！ 🎉");
                break;
            }

            Console.WriteLine("\n操作: [e]上 [s]左 [d]下 [f]右");
            Console.Write("入力してください > ");
            string input = Console.ReadLine();

            MovePlayer(input); // ここで呼ばれるMovePlayerが、インスタンスに応じて切り替わる
        }
    }
}

// ========== WarpMazeGameクラス (子クラス) ==========
// MazeGameクラスを継承
public class WarpMazeGame : MazeGame
{
    // コンストラクタ
    public WarpMazeGame() : base() // 親クラスのコンストラクタを呼び出す
    {
        // ★追加点: ワープポイント'A'を含むマップで親の_mapを上書き
        _map = new string[] {
            "####################",
            "#S#  #      #    G#",
            "# # ## #### # ### ##",
            "# #  # # A# # # #  #",
            "# ## # ## ### # ####",
            "#    #   #   #   # #",
            "#### ### # ##### # #",
            "# #      #     A # #",
            "# # ######## ##### #",
            "#                  #",
            "####################"
        };
    }

    // ★追加点: 親のMovePlayerメソッドをオーバーライドして、ワープ機能を追加
    protected override void MovePlayer(string direction)
    {
        // まず、親クラスの基本的な移動処理をそのまま実行する
        base.MovePlayer(direction);

        // その後、ワープの追加処理を行う
        // 移動した結果、現在地がワープポイント'A'かどうかをチェック
        if (_map[_playerY][_playerX] == 'A')
        {
            Console.WriteLine("\n✨ ワープ！ ✨");
            System.Threading.Thread.Sleep(1000); // 1秒待機

            // マップ全体を走査して、もう一方の'A'を探す
            for (int y = 0; y < _map.Length; y++)
            {
                for (int x = 0; x < _map[y].Length; x++)
                {
                    // 'A'を見つけ、かつ、それが現在のプレイヤーの位置と異なる場合
                    if (_map[y][x] == 'A' && (x != _playerX || y != _playerY))
                    {
                        // プレイヤーの位置をワープ先の座標に更新
                        _playerX = x;
                        _playerY = y;
                        return; // ワープ完了
                    }
                }
            }
        }
    }
}





// ========== メインプログラムのエントリーポイント ==========
public class Program
{
    public static void Main(string[] args)
    {
        // MazeGameクラスのインスタンスを作成し、ゲームを開始する
        MazeGame game = new MazeGame();
        game.Run();
    }
}