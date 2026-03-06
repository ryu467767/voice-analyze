"""
scraper.py
声優事務所サイトからボイスサンプルを収集するスクリプト

対応サイト:
  - VIMS (https://www.vims.co.jp/talent/)
  - Arts Vision (https://www.artsvision.co.jp/talent_all/)

使い方:
    pip install requests beautifulsoup4
    python scraper.py

注意:
  - 個人利用のみ。再配布・商用利用は禁止。
  - サーバーに負荷をかけないよう、リクエスト間に待機時間を設けています。
"""
import re
import time
import os
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ========================
# 設定
# ========================
OUTPUT_DIR = Path("data/voice_actors")
REQUEST_DELAY = 1.5       # リクエスト間隔（秒）
MAX_SAMPLES_PER_ACTOR = 3  # 1人あたり最大ダウンロード数（多すぎると重いので3枚程度）
TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ========================
# 共通ユーティリティ
# ========================
def fetch(url: str) -> BeautifulSoup | None:
    """URL を取得して BeautifulSoup を返す。失敗時は None。"""
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  [エラー] {url}: {e}")
        return None


def extract_mp3_urls(html_text: str, base_url: str) -> list[str]:
    """HTML/JS テキストから mp3 URL を正規表現で全抽出する"""
    pattern = r'https?://[^\s\'"<>]+\.mp3'
    urls = re.findall(pattern, html_text)
    return list(dict.fromkeys(urls))  # 重複除去・順序保持


def download_file(url: str, dest: Path) -> bool:
    """ファイルをダウンロードして保存する。成功したら True。"""
    if dest.exists():
        print(f"    スキップ（既存）: {dest.name}")
        return True
    try:
        resp = SESSION.get(url, timeout=TIMEOUT, stream=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"    保存: {dest.name} ({dest.stat().st_size // 1024} KB)")
        return True
    except Exception as e:
        print(f"    [エラー] DL失敗 {url}: {e}")
        return False


def sanitize_name(name: str) -> str:
    """ファイルシステムで使えない文字を除去する"""
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


# ========================
# VIMS
# ========================
VIMS_BASE = "https://www.vims.co.jp"
VIMS_LIST = "https://www.vims.co.jp/talent/"


def get_vims_talent_urls() -> list[tuple[str, str]]:
    """VIMS のタレント一覧から (名前, URL) のリストを返す"""
    soup = fetch(VIMS_LIST)
    if not soup:
        return []
    results = []
    for a in soup.select("a[href*='/talent/']"):
        href = a["href"]
        # /talent/数字/ の形式のみ
        if re.search(r"/talent/\d+", href):
            url = urljoin(VIMS_BASE, href)
            name = a.get_text(strip=True)
            if name:
                results.append((name, url))
    # 重複除去
    seen = set()
    unique = []
    for name, url in results:
        if url not in seen:
            seen.add(url)
            unique.append((name, url))
    return unique


def scrape_vims_actor(name: str, url: str) -> int:
    """1人分の VIMS 声優サンプルをダウンロード。ダウンロード数を返す。"""
    soup = fetch(url)
    if not soup:
        return 0
    time.sleep(REQUEST_DELAY)

    mp3_urls = extract_mp3_urls(str(soup), url)

    # 名前クレジット（0:02程度）は除外して実演サンプルを優先
    filtered = [u for u in mp3_urls if "クレジット" not in u and "credit" not in u.lower()]
    if not filtered:
        filtered = mp3_urls

    actor_dir = OUTPUT_DIR / sanitize_name(name)
    count = 0
    for i, mp3_url in enumerate(filtered[:MAX_SAMPLES_PER_ACTOR]):
        filename = Path(mp3_url).name
        dest = actor_dir / filename
        if download_file(mp3_url, dest):
            count += 1
        time.sleep(0.5)
    return count


def run_vims(limit: int = 0):
    """VIMS から全声優のサンプルを収集する。limit=0 で全員。"""
    print("=" * 50)
    print("VIMS スクレイピング開始")
    print("=" * 50)

    talents = get_vims_talent_urls()
    if limit > 0:
        talents = talents[:limit]
    print(f"{len(talents)} 名のタレントを検出")

    for i, (name, url) in enumerate(talents, 1):
        print(f"\n[{i}/{len(talents)}] {name}")
        n = scrape_vims_actor(name, url)
        print(f"  → {n} ファイル取得")
        time.sleep(REQUEST_DELAY)

    print("\nVIMS 完了")


# ========================
# Arts Vision
# ========================
AV_BASE = "https://www.artsvision.co.jp"
AV_LIST = "https://www.artsvision.co.jp/talent_all/"


def get_artsvision_talent_urls() -> list[tuple[str, str]]:
    """Arts Vision のタレント一覧から (名前, URL) のリストを返す"""
    soup = fetch(AV_LIST)
    if not soup:
        return []
    results = []
    for a in soup.select("a[href*='/talent/']"):
        href = a["href"]
        if re.search(r"/talent/\d+/", href):
            url = urljoin(AV_BASE, href)
            name = a.get_text(strip=True)
            if name:
                results.append((name, url))
    seen = set()
    unique = []
    for name, url in results:
        if url not in seen:
            seen.add(url)
            unique.append((name, url))
    return unique


def scrape_artsvision_actor(name: str, url: str) -> int:
    """1人分の Arts Vision 声優サンプルをダウンロード。ダウンロード数を返す。"""
    soup = fetch(url)
    if not soup:
        return 0
    time.sleep(REQUEST_DELAY)

    mp3_urls = extract_mp3_urls(str(soup), url)

    # 01（名前クレジット）を除外
    filtered = [u for u in mp3_urls if not re.search(r"_01\.mp3$", u)]
    if not filtered:
        filtered = mp3_urls

    actor_dir = OUTPUT_DIR / sanitize_name(name)
    count = 0
    for mp3_url in filtered[:MAX_SAMPLES_PER_ACTOR]:
        filename = Path(mp3_url).name
        dest = actor_dir / filename
        if download_file(mp3_url, dest):
            count += 1
        time.sleep(0.5)
    return count


def run_artsvision(limit: int = 0):
    """Arts Vision から全声優のサンプルを収集する。limit=0 で全員。"""
    print("=" * 50)
    print("Arts Vision スクレイピング開始")
    print("=" * 50)

    talents = get_artsvision_talent_urls()
    if limit > 0:
        talents = talents[:limit]
    print(f"{len(talents)} 名のタレントを検出")

    for i, (name, url) in enumerate(talents, 1):
        print(f"\n[{i}/{len(talents)}] {name}")
        n = scrape_artsvision_actor(name, url)
        print(f"  → {n} ファイル取得")
        time.sleep(REQUEST_DELAY)

    print("\nArts Vision 完了")


# ========================
# メイン
# ========================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="声優ボイスサンプル収集スクリプト")
    parser.add_argument(
        "--site",
        choices=["vims", "artsvision", "both"],
        default="both",
        help="対象サイト (default: both)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="テスト用: 各サイト何人まで取得するか (0=全員)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.site in ("vims", "both"):
        run_vims(limit=args.limit)

    if args.site in ("artsvision", "both"):
        run_artsvision(limit=args.limit)

    print("\n全完了。data/voice_actors/ を確認してください。")
    print("その後 app.py を起動して「DBを更新」ボタンを押してください。")
