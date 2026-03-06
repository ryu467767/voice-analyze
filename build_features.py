"""
build_features.py
Renderにデプロイする前に、ローカルで特徴量（.npy）を生成するスクリプト

使い方:
    python build_features.py

生成された data/features/*.npy を git add してコミット → Render にプッシュ
"""
from voice_actor_db import build_database
from pathlib import Path

if __name__ == "__main__":
    print("特徴量を計算中（初回は時間がかかります）...")
    db = build_database(force_rebuild=True)

    if db:
        print(f"\n完了: {len(db)} 名分の特徴量を生成しました")
        for name in db:
            npy_path = Path("data/features") / f"{name}.npy"
            size_kb = npy_path.stat().st_size // 1024
            print(f"  {name}: {npy_path} ({size_kb} KB)")
        print("\n次のコマンドでGitにコミットしてください:")
        print("  git add data/features/")
        print("  git commit -m 'feat: 声優特徴量を追加'")
        print("  git push")
    else:
        print("\ndata/voice_actors/ に音声ファイルがありません。")
        print("先にスクレイピングを実行してください: python scraper.py")
