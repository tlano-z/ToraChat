# ToraChat
<img width="353" height="461" alt="image" src="https://github.com/user-attachments/assets/b189739b-a55e-4bd5-8455-8d65d289d10d" /> <br>

VRChatのChatboxへテキストをOSC送信するデスクトップツールです。<br>
主に無言勢の日本語チャットを目的として作成しています。<br>
バーチャルデスクトップからSteamVRを起動し、XSOverlayでオーバーレイ表示して使うことを想定しています。

VRゴーグルしたままじゃキーボードの位置わかんないよ！という私のために、[カメラアプリ](https://github.com/tlano-z/SimpleCamera)もあります。 <br>

## かんたんなつかいかた
1. ToraChat.exeをダウンロード<br>
   （翻訳機能を使う場合はapi_key.txt、定型文機能を使う場合はpreset_messages.csvもいっしょに）
2. VRChatでOSCを有効にする
3. ToraChatを起動して、テキスト入力後にCtrl+Enterで送信

## 注意事項
1. 翻訳機能はGeminiAPIを利用するものです。<br>
   ここでは詳細に説明しませんが、よく理解した上で自己責任で使用お願いします。
2. 自家用ツールとして作ったものなので、様々な環境や条件下では試せていません。<br>
   なので、動かなかったらすみません。

## License
MIT License


# ここから先は詳細な説明です

## 主な機能
- Chatboxへの送信（通常送信 / 途中送信）
- 入力中の `/chatbox/typing` 自動送信
- Gemini APIを使った翻訳送信（英語 / 中国語 / カスタム言語）
- 定型文ボタン送信（`preset_messages.csv` から最大8件）
- 任意で `ToraChat_OSC_Talking` / `ToraChat_OSC_TalkStyle` を送信

- `ToraChat.py` と `ToraChat.exe` は同等機能です。

## 動作要件
- Windows
- VRChat（OSC有効）
- Pythonで実行する場合:
  - Python 3.10+
  - `requirements.txt` に記載のライブラリ

## ファイル構成
- `ToraChat.py`: Python版本体
- `ToraChat.exe`: 実行ファイル版本体（`ToraChat.py` と同等）
- `ToraChat.bat`: Python版ランチャー
- `requirements.txt`: 依存ライブラリ
- `preset_messages.csv`: 定型文
- `api_key.txt`: Gemini APIキー（任意。未設定時は翻訳機能のみ無効）
- `ToraChat.unitypackage`: 連動用アバターギミック（任意）

## セットアップ（Pythonで実行する場合）
1. 仮想環境を作成
   ```powershell
   python -m venv venv
   ```
2. 仮想環境を有効化
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. 依存ライブラリをインストール
   ```powershell
   pip install -r requirements.txt
   ```
4. 翻訳機能を使う場合のみ `api_key.txt` を作成し、1行目に Gemini APIキーを記載

## 実行方法
### 1. Pythonで実行
- 直接実行:
  ```powershell
  python ToraChat.py
  ```
- または `ToraChat.bat` を実行（同名 `.py` を `venv` のPythonで起動）

### 2. exeで実行
- `ToraChat.exe` をダブルクリックして起動
- 機能は `ToraChat.py` と同じです

## VRChat側の設定（OSC有効化）
本ツールを利用するには、VRChat側でOSCを有効にする必要があります。

1. VRChatを起動
2. `Main Menu` → `Options` → `OSC`
3. OSCを `Enabled` に設定

## ショートカットキー
- `Ctrl + Enter`: 送信（通常送信）
- `Ctrl + Shift + Enter`: 途中送信（入力欄を保持して送信）
- `Ctrl + Shift + Backspace`: 入力欄クリア

## ToraChat.unitypackage について（任意）
`ToraChat.unitypackage` はこのツールと連動するアバターギミックです。必須ではありません。<br>

導入時はPrefabをアバター直下に入れてください。<br>
Modular Avatarが必要です。

受信パラメータ:
- `ToraChat_OSC_Talking`
- `ToraChat_OSC_TalkStyle`

動作:
- `ToraChat_OSC_Talking` が `True -> False` になるまでの間、設定した音を再生します。
- `ToraChat_OSC_TalkStyle` に従って、3種類の音をランダムで鳴らします。
- デフォルトでは、ピッチ違いの猫の鳴き声が設定されています。

改変方法:
TalkSound_0, TalkSound_1, TalkSound_2それぞれのAudioClipを変更してください。<br>
初期状態ではそれぞれピッチの値もいじっているので気をつけてください。<br>
Audio Sourceの初期位置は原点（足元）になっています。口元に移動した方が自然かもしれません。

## 補足
- 翻訳機能は `api_key.txt` が未設定でも本体利用に影響しません（翻訳のみ無効）。
- 定型文は `preset_messages.csv` から読み込みます（空行は無視されます）。
