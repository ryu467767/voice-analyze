"""
voice_analyzer.py
音声ファイルからピッチ・MFCC特徴量を抽出するモジュール
"""
import numpy as np
import librosa
from typing import Optional


NOTE_NAMES_JA = {
    'C': 'ド', 'C#': 'ド#', 'D': 'レ', 'D#': 'レ#',
    'E': 'ミ', 'F': 'ファ', 'F#': 'ファ#', 'G': 'ソ',
    'G#': 'ソ#', 'A': 'ラ', 'A#': 'ラ#', 'B': 'シ',
}

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def hz_to_note_name(hz: float) -> str:
    """Hz を音符名に変換 (例: 'A4', 'C3')"""
    if hz <= 0 or np.isnan(hz):
        return "不明"
    midi = 12 * np.log2(hz / 440.0) + 69
    idx = int(round(midi)) % 12
    octave = int(round(midi)) // 12 - 1
    return f"{NOTE_NAMES[idx]}{octave}"


def hz_to_midi(hz: float) -> float:
    """Hz を MIDI ノート番号に変換"""
    if hz <= 0:
        return 0.0
    return 12 * np.log2(hz / 440.0) + 69


def load_audio(file_path: str, sr: int = 22050):
    """音声ファイルをロードして正規化する"""
    y, sr = librosa.load(file_path, sr=sr, mono=True)
    if np.max(np.abs(y)) > 0:
        y = y / np.max(np.abs(y))
    return y, sr


def extract_mfcc_features(y: np.ndarray, sr: int, n_mfcc: int = 20) -> np.ndarray:
    """
    MFCC + デルタ特徴量を抽出して1次元ベクトルとして返す
    声優マッチングに使用する音色の特徴量
    """
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    mfcc_delta = librosa.feature.delta(mfcc)
    mfcc_delta2 = librosa.feature.delta(mfcc, order=2)

    features = np.concatenate([
        np.mean(mfcc, axis=1),
        np.std(mfcc, axis=1),
        np.mean(mfcc_delta, axis=1),
        np.mean(mfcc_delta2, axis=1),
    ])
    return features


def detect_pitch(y: np.ndarray, sr: int) -> np.ndarray:
    """pyin アルゴリズムで基本周波数 (F0) を検出し、有声部分のみ返す"""
    f0, voiced_flag, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C7'),
        sr=sr,
    )
    voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]
    return voiced_f0


def determine_voice_type(median_hz: float) -> str:
    """中央ピッチから声域タイプを判定する"""
    if median_hz < 120:
        return "男性低音 (バス)"
    elif median_hz < 155:
        return "男性中音 (バリトン)"
    elif median_hz < 190:
        return "男性高音 (テナー)"
    elif median_hz < 230:
        return "女性低音 (アルト〜メゾソプラノ)"
    elif median_hz < 300:
        return "女性中音 (ソプラノ)"
    else:
        return "女性高音 (ハイソプラノ)"


def get_voice_category(median_hz: float) -> str:
    """male / female の2値分類"""
    return "male" if median_hz < 185 else "female"


def get_voice_sub_category(median_hz: float, category: str) -> str:
    """low / mid / high の3値分類"""
    if category == "male":
        if median_hz < 130:
            return "low"
        elif median_hz < 165:
            return "mid"
        else:
            return "high"
    else:
        if median_hz < 230:
            return "low"
        elif median_hz < 280:
            return "mid"
        else:
            return "high"


def analyze_audio(file_path: str) -> dict:
    """
    音声ファイルを総合解析する

    Returns:
        dict: 解析結果。'error' キーがある場合は解析失敗。
    """
    y, sr = load_audio(file_path)

    mfcc_features = extract_mfcc_features(y, sr)
    voiced_f0 = detect_pitch(y, sr)

    result: dict = {"mfcc_features": mfcc_features, "voiced_f0": voiced_f0}

    if len(voiced_f0) < 15:
        result["error"] = (
            "ピッチが十分に検出できませんでした。\n"
            "声をはっきりと録音してください（5秒以上推奨）。"
        )
        return result

    low_hz = float(np.percentile(voiced_f0, 10))
    high_hz = float(np.percentile(voiced_f0, 90))
    median_hz = float(np.median(voiced_f0))
    range_semitones = hz_to_midi(high_hz) - hz_to_midi(low_hz)

    category = get_voice_category(median_hz)
    sub_category = get_voice_sub_category(median_hz, category)

    result.update({
        "low_hz": low_hz,
        "high_hz": high_hz,
        "median_hz": median_hz,
        "low_note": hz_to_note_name(low_hz),
        "high_note": hz_to_note_name(high_hz),
        "median_note": hz_to_note_name(median_hz),
        "range_semitones": range_semitones,
        "voice_type": determine_voice_type(median_hz),
        "voice_category": category,
        "voice_sub_category": sub_category,
        "median_midi": hz_to_midi(median_hz),
    })
    return result
