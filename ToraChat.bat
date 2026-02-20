@echo off
REM ------------------------------------------------------------
REM  汎用 Python ランチャー (自己命名型) - venv フォルダーは同階層
REM
REM  フォルダー構成例
REM  - venv\                 : 仮想環境 (事前に作成必須)
REM  - test.bat              : このランチャー
REM  - test.py               : 実行対象スクリプト
REM
REM  使い方:
REM    1. このファイルをコピーし、スクリプト名に合わせてリネームします。
REM       例: test.bat -> test.py
REM    2. 2つのファイルを同じフォルダーに置き、同階層に venv フォルダーを配置します。
REM    3. venv がない場合は作成します:
REM       python -m venv venv
REM    4. venv を有効化し、必要な依存関係をインストールします。
REM    5. .bat をダブルクリックすると、venv 内で対応する .py を実行します。
REM
REM  必要条件:
REM    - venv\Scripts\activate.bat と venv\Scripts\python.exe が存在すること
REM ------------------------------------------------------------

:: 必須の仮想環境が存在するか確認
if not exist "%~dp0venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found next to this launcher.
    echo         Create one with:  python -m venv venv
    pause
    exit /b 1
)

:: 仮想環境を有効化
call "%~dp0venv\Scripts\activate.bat"

:: 対象の Python ファイル名を決定 (this.bat -> this.py)
set "TARGET=%~dp0%~n0.py"

:: 対象スクリプトを追加引数付きで実行
"%~dp0venv\Scripts\python.exe" "%TARGET%" %*

:: メッセージを読めるようにコンソールを閉じずに待機
echo.
echo ------------------------------------------------------------
echo  Finished. Press any key to close this window...
echo ------------------------------------------------------------
pause >nul
exit /b 0
