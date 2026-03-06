"""
song_recommender.py
声域・声カテゴリに基づいてカラオケ曲と似ている歌手を推薦するモジュール
"""
import json
import librosa
from pathlib import Path

SONGS_FILE = Path("data/songs.json")

# 声域タイプ別 似ている歌手リスト
SINGER_MAP: dict[str, dict[str, list[str]]] = {
    "male": {
        "low": [
            "長渕剛", "さだまさし", "玉置浩二", "吉田拓郎", "松山千春",
            "福山雅治", "浜田省吾", "尾崎豊", "谷村新司", "甲斐よしひろ",
            "堀内孝雄", "陣内大蔵",
        ],
        "mid": [
            "米津玄師", "草野マサムネ（スピッツ）", "桑田佳祐", "野田洋次郎（RADWIMPS）",
            "藤原基央（BUMP OF CHICKEN）", "優里", "槇原敬之", "山下達郎",
            "清水依与吏（back number）", "常田大希（King Gnu）",
            "はっとり（マカロニえんぴつ）", "北川悠仁（ゆず）",
        ],
        "high": [
            "Eve", "Ayase（YOASOBI）", "藤井風", "Vaundy",
            "山田将司（ブルーエンカウント）", "藤原聡（Official髭男dism）",
            "Taka（ONE OK ROCK）", "imase", "石原慎也（Saucy Dog）", "小田和正",
        ],
    },
    "female": {
        "low": [
            "宇多田ヒカル", "一青窈", "アンジェラ・アキ", "絢香", "Aimer",
            "椎名林檎", "坂本真綾", "大原櫻子", "家入レオ", "土岐麻子",
        ],
        "mid": [
            "LiSA", "中島美嘉", "YUI", "いきものがかり（吉岡聖恵）",
            "Little Glee Monster", "milet", "あいみょん", "ikura（YOASOBI）",
            "長屋晴子（緑黄色社会）", "ACAね（ずっと真夜中でいいのに。）",
            "藤川千愛", "Uru",
        ],
        "high": [
            "高橋洋子", "Superfly（越智志帆）", "MISIA", "倉木麻衣",
            "平原綾香", "Reol", "May'n", "鈴木このみ",
            "南條愛乃（fripSide）", "中川翔子",
        ],
    },
}


def _note_to_midi(note: str) -> int:
    """音符名 (例: 'A3', 'C#4') を MIDI ノート番号に変換する"""
    return int(librosa.note_to_midi(note))


def load_songs() -> list[dict]:
    """songs.json を読み込む"""
    with open(SONGS_FILE, encoding="utf-8") as f:
        return json.load(f)["songs"]


def recommend_songs(
    voice_category: str,
    median_midi: float,
    top_n: int = 12,
) -> list[dict]:
    """
    ユーザーの声カテゴリと中央ピッチから曲を推薦する

    スコア計算:
      - 声種（male/female/any）が一致 → 加点
      - 曲の中央 MIDI と ユーザーの推定歌唱中央 MIDI の距離が近いほど高スコア
    """
    songs = load_songs()

    # 話し声から歌声推定: 男性+10, 女性+5 半音程度上に歌唱中央がくる傾向
    singing_offset = 10 if voice_category == "male" else 5
    singing_midi = median_midi + singing_offset

    scored = []
    for song in songs:
        vtype = song.get("voice_type", "any")
        if vtype not in (voice_category, "any"):
            continue

        low_midi = _note_to_midi(song["lowest_note"])
        high_midi = _note_to_midi(song["highest_note"])
        song_mid = (low_midi + high_midi) / 2

        distance = abs(song_mid - singing_midi)
        # 距離が 0 なら 100 点、12 半音離れたら 64 点、24 半音なら 28 点
        score = max(0.0, 100.0 - distance * 3.0)

        scored.append((score, song))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:top_n]]


def get_singer_recommendations(
    voice_category: str,
    median_hz: float,
) -> list[str]:
    """声域タイプに合う歌手リストを返す"""
    from voice_analyzer import get_voice_sub_category
    sub = get_voice_sub_category(median_hz, voice_category)
    return SINGER_MAP.get(voice_category, {}).get(sub, [])
