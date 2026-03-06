"""
app.py
カラオケ声分析 Web アプリ (Gradio)

起動方法:
    pip install -r requirements.txt
    python app.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import gradio as gr

from voice_analyzer import analyze_audio
from voice_actor_db import build_database, find_similar_actors
from song_recommender import recommend_songs, get_singer_recommendations

# 起動時に声優DBを読み込む
ACTOR_DB: dict = {}


def refresh_database() -> str:
    global ACTOR_DB
    print("声優データベースを更新中...")
    ACTOR_DB = build_database(force_rebuild=False)
    if ACTOR_DB:
        names = "、".join(ACTOR_DB.keys())
        return f"✅ {len(ACTOR_DB)}名 読み込み完了: {names}"
    return "⚠️ data/voice_actors/ に音声フォルダが見つかりません。README を参照してください。"


def create_pitch_chart(voiced_f0: np.ndarray) -> plt.Figure:
    """F0 の時系列グラフを作成する"""
    import librosa

    fig, ax = plt.subplots(figsize=(9, 3))
    ax.plot(voiced_f0, color="#4CAF50", linewidth=1.2, alpha=0.85, label="検出ピッチ")

    # 参考音符の横線
    ref_notes = ["C3", "G3", "C4", "G4", "C5", "G5"]
    ref_hz = [librosa.note_to_hz(n) for n in ref_notes]
    y_min, y_max = np.min(voiced_f0) * 0.85, np.max(voiced_f0) * 1.15

    for hz, note in zip(ref_hz, ref_notes):
        if y_min <= hz <= y_max:
            ax.axhline(y=hz, color="gray", linestyle="--", alpha=0.4, linewidth=0.7)
            ax.text(
                len(voiced_f0) * 0.99, hz, note,
                va="center", ha="right", fontsize=7, color="gray"
            )

    ax.set_ylim(y_min, y_max)
    ax.set_yscale("log")
    ax.set_ylabel("Pitch (Hz)")
    ax.set_xlabel("フレーム")
    ax.set_title("検出ピッチの推移")
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout()
    return fig


def format_voice_result(result: dict) -> str:
    """声域分析結果を Markdown 文字列にフォーマットする"""
    r = result
    octaves = r["range_semitones"] / 12

    # カラオケキー調整のヒント
    median_note = r["median_note"]
    low_note = r["low_note"]
    high_note = r["high_note"]

    md = f"""## 声の分析結果

| 項目 | 結果 |
|------|------|
| **声域タイプ** | {r["voice_type"]} |
| **低音** | {low_note} ({r["low_hz"]:.1f} Hz) |
| **高音** | {high_note} ({r["high_hz"]:.1f} Hz) |
| **中央音** | {median_note} ({r["median_hz"]:.1f} Hz) |
| **音域の広さ** | {r["range_semitones"]:.0f} 半音（約 {octaves:.1f} オクターブ） |

### カラオケキーの目安
中央音 **{median_note}** を基準に、カラオケのキー調整機能でプラス・マイナスしながら歌いやすいキーを探してください。
"""
    return md


def format_actor_result(result: dict) -> str:
    """声優マッチング結果を Markdown 文字列にフォーマットする"""
    if not ACTOR_DB:
        return """## 似ている声優

> **声優データ未設定**
>
> `data/voice_actors/声優名/` フォルダに音声ファイル（WAV/MP3 等）を入れ、
> 「データベースを更新」ボタンを押してください。
>
> 例: `data/voice_actors/花澤香菜/sample.wav`
"""

    similar = find_similar_actors(result["mfcc_features"], ACTOR_DB, top_n=3)
    if not similar:
        return "## 似ている声優\n\n類似声優が見つかりませんでした。"

    medals = ["🥇", "🥈", "🥉"]
    md = "## 似ている声優\n\n"
    for i, (name, sim) in enumerate(similar):
        medal = medals[i] if i < 3 else f"{i + 1}."
        bar = "█" * int(sim * 20) + "░" * (20 - int(sim * 20))
        md += f"### {medal} {name}\n類似度: **{sim:.1%}** `{bar}`\n\n"

    md += "\n> ※ 類似度は MFCC（音色特徴量）のコサイン類似度です。\n> 録音環境や読み上げ内容が違うと精度が下がります。"
    return md


def format_song_result(result: dict) -> str:
    """曲・歌手レコメンド結果を Markdown 文字列にフォーマットする"""
    category = result["voice_category"]
    median_hz = result["median_hz"]
    median_midi = result["median_midi"]

    singers = get_singer_recommendations(category, median_hz)
    songs = recommend_songs(category, median_midi, top_n=12)

    md = "## おすすめカラオケ曲\n\n"

    if singers:
        md += f"**あなたに似た声の歌手**: {' / '.join(singers)}\n\n---\n\n"

    diff_icon = {"easy": "🟢 易", "medium": "🟡 中", "hard": "🔴 難"}

    if songs:
        md += "| 難易度 | 曲名 | アーティスト | 出典 |\n"
        md += "|--------|------|-------------|------|\n"
        for song in songs:
            icon = diff_icon.get(song["difficulty"], "⚪")
            source = song.get("source", "")
            notes = song.get("notes", "")
            md += f"| {icon} | **{song['title']}** | {song['artist']} | {source} |\n"
        md += "\n> 🟢=歌いやすい　🟡=普通　🔴=難しめ\n"
        md += "\n**各曲の補足**\n"
        for song in songs:
            if song.get("notes"):
                md += f"- **{song['title']}**: {song['notes']}\n"
    else:
        md += "おすすめ曲が見つかりませんでした。"

    return md


def analyze_voice(audio_file):
    """Gradio から呼ばれるメイン解析関数"""
    if audio_file is None:
        empty = "音声を録音またはアップロードしてください。"
        return None, empty, "", ""

    try:
        result = analyze_audio(audio_file)
    except Exception as e:
        msg = f"解析エラー: {e}"
        return None, msg, "", ""

    if "error" in result:
        return None, result["error"], "", ""

    # ピッチグラフ
    chart = None
    if len(result["voiced_f0"]) > 10:
        try:
            chart = create_pitch_chart(result["voiced_f0"])
        except Exception:
            pass

    voice_md = format_voice_result(result)
    actor_md = format_actor_result(result)
    song_md = format_song_result(result)

    return chart, voice_md, actor_md, song_md


# ========================
# Gradio UI
# ========================
with gr.Blocks(
    title="カラオケ声分析アプリ",
    theme=gr.themes.Soft(),
    css="""
    .result-box { background: #f8f9fa; border-radius: 8px; padding: 16px; }
    h2 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 4px; }
    """,
) as demo:

    gr.Markdown("""# 🎤 カラオケ声分析アプリ
声を録音すると **声域タイプ・似ている声優・おすすめカラオケ曲** を分析します。
""")

    with gr.Row():
        with gr.Column(scale=1):
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="声を録音 / 音声ファイルをアップロード（5〜30秒推奨）",
            )
            with gr.Row():
                analyze_btn = gr.Button("分析する", variant="primary", scale=2)
                refresh_btn = gr.Button("DBを更新", variant="secondary", scale=1)
            db_status = gr.Textbox(
                label="声優データベース",
                value="起動後に「DBを更新」を押すと声優データを読み込みます",
                interactive=False,
                lines=2,
            )

        with gr.Column(scale=1):
            pitch_chart = gr.Plot(label="ピッチの推移")

    with gr.Row():
        voice_output = gr.Markdown(elem_classes=["result-box"])

    with gr.Row():
        with gr.Column():
            actor_output = gr.Markdown(elem_classes=["result-box"])
        with gr.Column():
            song_output = gr.Markdown(elem_classes=["result-box"])

    analyze_btn.click(
        fn=analyze_voice,
        inputs=[audio_input],
        outputs=[pitch_chart, voice_output, actor_output, song_output],
    )

    refresh_btn.click(
        fn=refresh_database,
        outputs=[db_status],
    )

    gr.Markdown("""---
### 使い方
1. マイクで声を録音、または WAV/MP3 をアップロード
2. **「分析する」** をクリック → 声域・おすすめ曲・似ている声優が表示されます

### 声優データの追加方法
事務所サイト等から音声サンプルを取得し、以下の構造で配置してください:
```
data/
└── voice_actors/
    ├── 花澤香菜/
    │   ├── sample1.wav
    │   └── sample2.mp3
    └── 梶裕貴/
        └── sample.wav
```
配置後に **「DBを更新」** を押すと自動で特徴量を計算します。
次回起動時はキャッシュを使うので高速です。

### 精度を上げるコツ
- 声優サンプルはセリフ・会話音声（歌でなく話し声）が理想的
- 自分の録音も同じく **話し声** か **地声で歌った声** で録音すると比較精度が上がります
- 5〜20 秒程度の長さが最適です
""")


if __name__ == "__main__":
    import os
    print("起動中...")
    ACTOR_DB = build_database()

    # Render など本番環境は PORT 環境変数でポートが指定される
    port = int(os.environ.get("PORT", 7860))
    # Render は 0.0.0.0 で受け付ける必要がある。ローカルは 127.0.0.1
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    # start.bat 経由の起動時はブラウザを自動で開かない
    auto_open = os.environ.get("KARAOKE_NO_BROWSER", "0") != "1" and host == "127.0.0.1"

    demo.launch(
        share=False,
        inbrowser=auto_open,
        server_name=host,
        server_port=port,
    )
