"""
voice_actor_db.py
声優サンプル音声から特徴量を計算・キャッシュし、類似度を比較するモジュール

ディレクトリ構造:
    data/voice_actors/
        花澤香菜/
            sample1.wav
            sample2.mp3
        梶裕貴/
            sample.wav
"""
import os
import numpy as np
from pathlib import Path
from scipy.spatial.distance import cosine
from typing import Optional

from voice_analyzer import load_audio, extract_mfcc_features

VOICE_ACTORS_DIR = Path("data/voice_actors")
FEATURES_DIR = Path("data/features")

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}


def get_actor_dirs() -> list[Path]:
    """声優ディレクトリの一覧を返す"""
    if not VOICE_ACTORS_DIR.exists():
        return []
    return [d for d in sorted(VOICE_ACTORS_DIR.iterdir()) if d.is_dir()]


def compute_actor_features(actor_dir: Path) -> Optional[np.ndarray]:
    """
    1人の声優のサンプル音声から平均MFCCベクトルを計算する
    複数ファイルがある場合は平均を取る
    """
    audio_files = [
        f for f in actor_dir.iterdir()
        if f.suffix.lower() in AUDIO_EXTENSIONS
    ]
    if not audio_files:
        return None

    all_features = []
    for audio_file in audio_files:
        try:
            y, sr = load_audio(str(audio_file))
            feat = extract_mfcc_features(y, sr)
            all_features.append(feat)
        except Exception as e:
            print(f"  [警告] {audio_file.name} の処理中にエラー: {e}")

    if not all_features:
        return None
    return np.mean(all_features, axis=0)


def build_database(force_rebuild: bool = False) -> dict[str, np.ndarray]:
    """
    全声優の特徴量データベースを構築する
    キャッシュ (data/features/*.npy) がある場合はそれを使用する

    Returns:
        {声優名: 特徴量ベクトル} の辞書
    """
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    VOICE_ACTORS_DIR.mkdir(parents=True, exist_ok=True)

    database: dict[str, np.ndarray] = {}
    actor_dirs = get_actor_dirs()

    if not actor_dirs:
        print("声優データが見つかりません。data/voice_actors/ にサンプルを追加してください。")
        return database

    for actor_dir in actor_dirs:
        name = actor_dir.name
        feature_file = FEATURES_DIR / f"{name}.npy"

        if not force_rebuild and feature_file.exists():
            database[name] = np.load(feature_file)
        else:
            print(f"  計算中: {name} ...")
            features = compute_actor_features(actor_dir)
            if features is not None:
                np.save(feature_file, features)
                database[name] = features
            else:
                print(f"  [スキップ] {name}: 音声ファイルなし")

    return database


def find_similar_actors(
    user_features: np.ndarray,
    database: dict[str, np.ndarray],
    top_n: int = 3,
) -> list[tuple[str, float]]:
    """
    ユーザーの MFCC ベクトルと声優DBを比較し、上位N件を返す

    Returns:
        [(声優名, 類似度0〜1), ...] 類似度降順
    """
    if not database:
        return []

    similarities = []
    for name, actor_features in database.items():
        try:
            sim = 1.0 - cosine(user_features, actor_features)
            sim = max(0.0, min(1.0, sim))  # 0〜1にクリップ
            similarities.append((name, sim))
        except Exception:
            continue

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_n]


def delete_actor_cache(actor_name: str) -> bool:
    """特定の声優のキャッシュを削除する（再計算を強制したい場合）"""
    feature_file = FEATURES_DIR / f"{actor_name}.npy"
    if feature_file.exists():
        feature_file.unlink()
        return True
    return False
