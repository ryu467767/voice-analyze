@echo off
REM カラオケ声分析アプリ 起動スクリプト
REM ここにngrokの固定ドメインを貼り付けてください（例: karaoke-voice.ngrok-free.app）
set NGROK_DOMAIN=ここにngrokのドメインを貼り付け

REM アプリのディレクトリに移動
cd /d "%~dp0"

REM Python仮想環境があれば有効化（venvを使っていない場合は次の2行を削除）
REM call .venv\Scripts\activate.bat

REM Pythonアプリをバックグラウンドで起動（ngrok経由なのでブラウザ自動起動しない）
set KARAOKE_NO_BROWSER=1
start "KaraokeApp" /min python app.py

REM ngrokが起動するまで少し待つ（Gradioが立ち上がる時間）
timeout /t 8 /nobreak > nul

REM ngrokトンネルを起動（固定ドメインを使用）
start "ngrok" /min ngrok http --domain=%NGROK_DOMAIN% 7860

echo.
echo アプリが起動しました。
echo ローカル: http://localhost:7860
echo 外部URL:  https://%NGROK_DOMAIN%
echo.
echo このウィンドウを閉じてもアプリは動き続けます。
pause
