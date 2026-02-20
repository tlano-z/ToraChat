import wx
import os
import sys
from pythonosc import udp_client
from google import genai
from google.genai import types
import json
import random
import csv

# APIキーを保持するファイル名
API_KEY_FILE = "api_key.txt"
FIXED_PHRASES_FILE = "preset_messages.csv"
MODEL = 'gemini-2.5-flash'

# OSC で送るパラメータ名（VRChat側の ExpressionParameters と合わせる）
OSC_TALKING_ADDRESS = "/avatar/parameters/ToraChat_OSC_Talking"
OSC_TALKSTYLE_ADDRESS = "/avatar/parameters/ToraChat_OSC_TalkStyle"

# chatbox typing アドレス
CHATBOX_TYPING_ADDRESS = "/chatbox/typing"

# しゃべり時間の計算用パラメータ
TALK_TIME_PER_CHAR = 0.25  # 1文字あたり 0.08秒
MIN_TALK_TIME = 0.5        # 最短 0.5秒
MAX_TALK_TIME = 10.0       # 最長 10秒

# トークスタイルのバリエーション数
NUM_TALK_STYLES = 3

# 定型文の最大数とボタンラベルの最大文字数
MAX_FIXED_PHRASES = 8
FIXED_BUTTON_LABEL_MAX_CHARS = 16


def load_api_key():
    """APIキーを外部ファイルから読み込む"""
    try:
        with open(API_KEY_FILE, "r") as f:
            api_key = f.readline().strip()
            if not api_key or api_key.lower() == "none":
                print(f"APIキーファイルが空です: {API_KEY_FILE}")
                return None
            return api_key
    except FileNotFoundError:
        print(f"APIキーファイルが見つかりません: {API_KEY_FILE}")
        return None
    except Exception as e:
        print(f"APIキーファイルの読み込みに失敗しました: {e}")
        return None


client = None
api_key = load_api_key()
if api_key:
    try:
        # Gemini API のキーを設定
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Gemini初期化に失敗したため、翻訳機能を無効化します: {e}")
else:
    print("APIキー未設定のため、翻訳機能を無効化します。")


class VRChatChatboxFrame(wx.Frame):
    def __init__(self, parent, title):
        super(VRChatChatboxFrame, self).__init__(parent, title=title)
        if getattr(sys, "frozen", False):
            # PyInstaller実行時は exe に埋め込まれたアイコンを使う
            self.SetIcon(wx.Icon(sys.executable, wx.BITMAP_TYPE_ICO))
        else:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.SetIcon(wx.Icon(icon_path, wx.BITMAP_TYPE_ICO))

        self.client = udp_client.SimpleUDPClient("127.0.0.1", 9000)

        # OSC_Talking の終了用タイマー
        self.osc_talk_timer = None
        # /chatbox/typing の状態
        self.is_typing = False
        # /chatbox/typing 再送信用タイマー（3秒ごと）
        self.typing_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_typing_timer, self.typing_timer)

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.fixed_phrases = self.load_fixed_phrases()

        # テキスト入力欄
        text_row = wx.BoxSizer(wx.HORIZONTAL)
        text_row.Add(wx.StaticText(panel, label="テキスト:"),
                     flag=wx.ALIGN_CENTER_VERTICAL)

        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

        self.text_input = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER | wx.TE_RICH2
        )
        self.text_input.SetMinSize((-1, 150))
        # 文字数の変化を検知するイベント
        self.text_input.Bind(wx.EVT_TEXT, self.on_text_change)

        text_row.Add(self.text_input, proportion=1,
                     flag=wx.EXPAND | wx.LEFT, border=5)
        main_sizer.Add(text_row, proportion=1,
                       flag=wx.EXPAND | wx.ALL, border=10)

        # 翻訳オプション
        option_row = wx.BoxSizer(wx.HORIZONTAL)
        option_row.Add(wx.StaticText(panel, label="翻訳:"),
                       flag=wx.ALIGN_CENTER_VERTICAL)

        self.english_checkbox = wx.CheckBox(panel, label="英語")
        self.chinese_checkbox = wx.CheckBox(panel, label="中国語")
        self.custom_checkbox = wx.CheckBox(panel, label="その他:")
        self.custom_lang_input = wx.TextCtrl(panel)
        self.custom_lang_input.Enable(False)
        self.custom_checkbox.Bind(wx.EVT_CHECKBOX, self.on_custom_checkbox)

        option_row.Add(self.english_checkbox,
                       flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)
        option_row.Add(self.chinese_checkbox,
                       flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)
        option_row.Add(self.custom_checkbox,
                       flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)
        option_row.Add(self.custom_lang_input, proportion=1,
                       flag=wx.LEFT | wx.EXPAND, border=10)

        main_sizer.Add(option_row, flag=wx.EXPAND | wx.ALL, border=10)
        if client is None:
            self.english_checkbox.Enable(False)
            self.chinese_checkbox.Enable(False)
            self.custom_checkbox.Enable(False)
            self.custom_lang_input.Enable(False)

        # OSC_Talkingパラメータ有効化チェックボックス
        osc_row = wx.BoxSizer(wx.HORIZONTAL)
        self.osc_talk_checkbox = wx.CheckBox(panel, label="OSC_Talkingパラメータ有効化")
        self.osc_talk_checkbox.SetValue(False)
        osc_row.Add(self.osc_talk_checkbox, flag=wx.LEFT, border=10)
        main_sizer.Add(osc_row, flag=wx.EXPAND | wx.ALL, border=0)

        # ボタン行
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        send_button = wx.Button(panel, label="送信")
        partial_send_button = wx.Button(panel, label="途中送信")
        clear_button = wx.Button(panel, label="クリア")
        send_button.Bind(wx.EVT_BUTTON, self.on_send_button)
        partial_send_button.Bind(wx.EVT_BUTTON, self.on_partial_send_button)
        clear_button.Bind(wx.EVT_BUTTON, self.on_clear_button)

        btn_row.AddStretchSpacer()
        btn_row.Add(send_button)
        btn_row.AddSpacer(20)
        btn_row.Add(partial_send_button)
        btn_row.AddSpacer(20)
        btn_row.Add(clear_button)
        main_sizer.Add(btn_row, flag=wx.EXPAND | wx.ALL, border=10)

        # 定型文ボタンブロック
        fixed_row = wx.StaticBoxSizer(wx.StaticBox(panel, label="定型文送信"), wx.VERTICAL)
        fixed_grid = wx.GridSizer(rows=4, cols=2, vgap=8, hgap=8)
        for i in range(MAX_FIXED_PHRASES):
            if i < len(self.fixed_phrases):
                phrase = self.fixed_phrases[i]
                button = wx.Button(panel, label=self.to_button_label(phrase))
                button.SetToolTip(phrase)
                button.Bind(wx.EVT_BUTTON, lambda event, p=phrase: self.on_fixed_phrase_button(event, p))
            else:
                button = wx.Button(panel, label="(未設定)")
                button.Enable(False)
            fixed_grid.Add(button, flag=wx.EXPAND)
        fixed_row.Add(fixed_grid, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)
        main_sizer.Add(fixed_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        panel.SetSizer(main_sizer)
        main_sizer.SetSizeHints(self)

        # Ctrl+Enter 送信 / Ctrl+Shift+Enter 途中送信 / Ctrl+Shift+Backspace クリア（アクセラレータ）
        send_id = wx.NewIdRef()
        partial_send_id = wx.NewIdRef()
        clear_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, lambda evt: self.send_text(), id=send_id)
        self.Bind(wx.EVT_MENU, lambda evt: self.send_text(clear_input=False, apply_translation=False), id=partial_send_id)
        self.Bind(wx.EVT_MENU, self.on_clear_button, id=clear_id)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_CTRL, wx.WXK_RETURN, send_id),
            (wx.ACCEL_CTRL, wx.WXK_NUMPAD_ENTER, send_id),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_RETURN, partial_send_id),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_NUMPAD_ENTER, partial_send_id),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_BACK, clear_id),
        ]))

        self.Centre()
        self.Show(True)

    # ---------------- UIイベント ----------------

    def on_custom_checkbox(self, event):
        is_checked = event.IsChecked()
        self.custom_lang_input.Enable(is_checked)

    def on_send_button(self, event):
        self.send_text()

    def on_partial_send_button(self, event):
        self.send_text(clear_input=False, apply_translation=False)

    def on_fixed_phrase_button(self, event, phrase):
        self.send_text(text_override=phrase, clear_input=False)

    def on_text_change(self, event):
        """
        テキスト入力欄の内容が変わったときに呼ばれる。
        1文字以上入力されているかどうかで /chatbox/typing を制御。
        入力中は 3 秒間隔で True を再送する。
        """
        text = self.text_input.GetValue()
        currently_typing = len(text) > 0

        # 状態が変わったときだけ制御
        if currently_typing != self.is_typing:
            self.is_typing = currently_typing

            if self.is_typing:
                # 入力開始 → True を送信し、タイマー開始
                self.client.send_message(CHATBOX_TYPING_ADDRESS, True)
                print(f"OSC: {CHATBOX_TYPING_ADDRESS} -> True (start typing)")
                # 3秒ごとに True を再送
                self.typing_timer.Start(3000)
            else:
                # 入力が完全に消えた → False を送信し、タイマー停止
                self.client.send_message(CHATBOX_TYPING_ADDRESS, False)
                print(f"OSC: {CHATBOX_TYPING_ADDRESS} -> False (stop typing)")
                if self.typing_timer.IsRunning():
                    self.typing_timer.Stop()

        event.Skip()

    def on_typing_timer(self, event):
        """
        3秒ごとのタイマーイベント。
        入力中であれば /chatbox/typing True を再送。
        """
        if self.is_typing:
            self.client.send_message(CHATBOX_TYPING_ADDRESS, True)
            print(f"OSC: {CHATBOX_TYPING_ADDRESS} -> True (keep typing)")
        else:
            # 念のため止めておく
            if self.typing_timer.IsRunning():
                self.typing_timer.Stop()

    # ---------------- OSC_Talking制御 ----------------

    def start_npc_talk_osc(self, original_text: str):
        if not original_text:
            return

        # 既存タイマーがあれば停止
        if self.osc_talk_timer is not None:
            try:
                self.osc_talk_timer.Stop()
            except Exception:
                pass
            self.osc_talk_timer = None

        # 改行を除いた文字数で計算
        char_count = len(original_text.replace("\n", ""))
        if char_count <= 0:
            return

        duration = char_count * TALK_TIME_PER_CHAR
        duration = max(MIN_TALK_TIME, min(MAX_TALK_TIME, duration))

        # ランダムなトークスタイル
        if NUM_TALK_STYLES > 0:
            style_index = random.randint(0, NUM_TALK_STYLES - 1)
        else:
            style_index = 0

        self.client.send_message(OSC_TALKSTYLE_ADDRESS, float(style_index))
        print(f"OSC: {OSC_TALKSTYLE_ADDRESS} -> {style_index}")

        self.client.send_message(OSC_TALKING_ADDRESS, True)
        print(f"OSC: {OSC_TALKING_ADDRESS} -> True (duration={duration:.2f} sec, chars={char_count})")

        self.osc_talk_timer = wx.CallLater(int(duration * 1000), self.stop_npc_talk_osc)

    def stop_npc_talk_osc(self):
        self.client.send_message(OSC_TALKING_ADDRESS, False)
        print(f"OSC: {OSC_TALKING_ADDRESS} -> False")
        self.osc_talk_timer = None

    # ---------------- 送信処理 ----------------

    def send_text(self, text_override=None, clear_input=True, apply_translation=True):
        text = text_override if text_override is not None else self.text_input.GetValue()
        if not text:
            print("テキストを入力してください。")
            return

        target_languages = []
        if self.english_checkbox.IsChecked():
            target_languages.append("en")
        if self.chinese_checkbox.IsChecked():
            target_languages.append("zh")
        if self.custom_checkbox.IsChecked():
            custom_lang = self.custom_lang_input.GetValue().strip()
            if custom_lang:
                target_languages.append(custom_lang)
            else:
                print("カスタム言語が入力されていません。")
                return

        if apply_translation and target_languages and client is not None:
            translated_text = self.translate_text(text, target_languages)
            self.client.send_message("/chatbox/input", [translated_text, True, True])
            print(f"Sent: {translated_text}")
        else:
            self.client.send_message("/chatbox/input", [text, True, True])
            print(f"Sent: {text}")

        # 通常送信（入力欄をクリアする場合）のみ typing を解除する
        if clear_input and self.is_typing:
            self.is_typing = False
            self.client.send_message(CHATBOX_TYPING_ADDRESS, False)
            print(f"OSC: {CHATBOX_TYPING_ADDRESS} -> False (after send)")
            if self.typing_timer.IsRunning():
                self.typing_timer.Stop()

        # OSC_Talkingパラメータ送信
        if self.osc_talk_checkbox.IsChecked():
            self.start_npc_talk_osc(text)

        if clear_input:
            self.text_input.Clear()

    def load_fixed_phrases(self):
        phrases = []
        try:
            with open(FIXED_PHRASES_FILE, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    for value in row:
                        phrase = value.strip()
                        if phrase:
                            phrases.append(phrase)
                            if len(phrases) >= MAX_FIXED_PHRASES:
                                return phrases
        except FileNotFoundError:
            print(f"定型文ファイルが見つかりません: {FIXED_PHRASES_FILE}")
        except Exception as e:
            print(f"定型文ファイルの読み込みに失敗しました: {e}")
        return phrases

    def to_button_label(self, phrase):
        one_line = phrase.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
        if len(one_line) <= FIXED_BUTTON_LABEL_MAX_CHARS:
            return one_line
        return one_line[:FIXED_BUTTON_LABEL_MAX_CHARS] + "..."

    # ---------------- Gemini翻訳 ----------------

    def translate_text(self, text, target_languages):
        if client is None:
            return text

        prompt = f"""
        Translate the following Japanese text into the following languages: {', '.join(target_languages)}.
        Return a JSON object with the following format:
        {{
            "translations": {{
                {', '.join(f'"{lang}": "translated text in {lang}"' for lang in target_languages)}
            }}
        }}
        Japanese text: {text}
        """

        generation_config_kwargs = {
            "response_mime_type": "application/json"
        }

        generation_config = types.GenerateContentConfig(**generation_config_kwargs)

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=generation_config
            )
        except Exception as e:
            print(f"Gemini API 呼び出しでエラーが発生しました: {e}")
            return text

        try:
            json_data = json.loads(response.text)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON response.\nRaw response: {response.text}")
            return text

        translated_output = text
        if "translations" in json_data:
            for lang, translated_text in json_data["translations"].items():
                translated_output += f"\n[{lang.upper()}]\n{translated_text}"
        else:
            print(f"Error: Invalid JSON format.\nRaw response:{response.text}")
        return translated_output

    # イベントハンドラ: キーボード入力のフック

    def on_char_hook(self, event):
        key_code = event.GetKeyCode()

        # 入力欄が空の状態で Backspace → Windowsのポロロンを防ぐ
        if key_code == wx.WXK_BACK:
            focused = wx.Window.FindFocus()
            if focused is self.text_input:
                # 選択範囲がなく、内容も空なら「何もしない」で握りつぶす
                sel_from, sel_to = self.text_input.GetSelection()
                if self.text_input.GetValue() == "" and sel_from == sel_to:
                    return  # event.Skip() しない＝OSに渡さない

        event.Skip()

    # ---------------- その他 ----------------

    def on_clear_button(self, event):
        self.text_input.Clear()
        # クリアしたら typing も解除しておく
        if self.is_typing:
            self.is_typing = False
            self.client.send_message(CHATBOX_TYPING_ADDRESS, False)
            print(f"OSC: {CHATBOX_TYPING_ADDRESS} -> False (after clear)")
            if self.typing_timer.IsRunning():
                self.typing_timer.Stop()


if __name__ == '__main__':
    app = wx.App()
    frame = VRChatChatboxFrame(None, "ToraChat")
    app.MainLoop()
