"""Reusable presentation components; illustrations are intentionally schematic."""

import json

from nicegui import ui


def button(*args, **kwargs):
    """Let the shared stylesheet own button colors, including focus/contrast states."""
    return ui.button(*args, color=None, **kwargs)


def scroll_top():
    ui.run_javascript("window.scrollTo({top: 0, behavior: 'instant'})")


def speech_button(text: str):
    # Browser-side click preserves the user gesture required by mobile Safari.
    script = """() => {
      const status = document.getElementById('voice-status');
      if (!('speechSynthesis' in window)) {
        if (status) status.textContent = '這個瀏覽器無法朗讀，請看下方的大字教學。';
        return;
      }
      speechSynthesis.cancel();
      const speech = new SpeechSynthesisUtterance(TEXT);
      speech.lang = 'zh-TW'; speech.rate = 0.8;
      const voices = speechSynthesis.getVoices();
      const voice = voices.find(v => v.lang === 'zh-TW') ||
                    voices.find(v => v.lang.startsWith('zh'));
      if (voice) speech.voice = voice;
      speech.onstart = () => { if(status) status.textContent = '正在朗讀這一步…'; };
      speech.onend = () => { if(status) status.textContent = '朗讀完了，慢慢操作就好。'; };
      speech.onerror = () => {
        if(status) status.textContent = '朗讀已停止；沒有聲音時請檢查音量或看文字。';
      };
      window.elderGuideSpeech = speech;
      speechSynthesis.speak(speech);
    }""".replace("TEXT", json.dumps(text, ensure_ascii=False))
    button("唸給我聽", icon="volume_up").props("outline no-caps").classes("secondary-button").on(
        "click", js_handler=script
    )


def stop_speech():
    ui.run_javascript("if ('speechSynthesis' in window) speechSynthesis.cancel()")


def illustration(data: dict):
    with ui.column().classes("illustration-wrap"):
        with ui.column().classes("phone"):
            with ui.row().classes("phone-status"):
                ui.label("9:41")
                ui.icon("signal_cellular_alt", size="18px")
                ui.icon("battery_full", size="18px")
            ui.label(data["screen"]).classes("phone-heading")
            kind, target = data["kind"], data["target"]
            if kind == "app":
                with ui.column().classes("phone-app-area"):
                    ui.icon("chat_bubble" if target == "LINE" else "settings", size="50px").classes(
                        "app-icon line-icon" if target == "LINE" else "app-icon"
                    )
                    ui.label(target).classes("phone-app-name")
                    ui.icon("touch_app", size="36px").classes("pointing-hand")
            elif kind == "slider":
                ui.label("看得清楚，\n讀起來更輕鬆。").classes("phone-sample")
                with ui.row().classes("slider-labels"):
                    ui.label("小" if "文字" in target else "暗")
                    ui.label("大" if "文字" in target else "亮")
                with ui.element("div").classes("sample-slider"):
                    ui.element("div").classes("sample-thumb")
                ui.label("向右慢慢移動 →").classes("slider-caption")
            elif kind == "toggle":
                ui.label(target).classes("phone-target-text")
                with ui.element("div").classes(
                    "sample-toggle off" if "關閉" in target else "sample-toggle"
                ):
                    ui.element("div").classes("toggle-dot")
                ui.label("關閉" if "關閉" in target else "開啟").classes("slider-caption")
            else:
                for row in data["rows"]:
                    with ui.row().classes(
                        "phone-row highlighted" if row == target else "phone-row"
                    ):
                        ui.label(row)
                        ui.icon("check_circle" if row == target else "chevron_right", size="22px")
                ui.icon("touch_app", size="32px").classes("pointing-hand")
            ui.element("div").classes("home-indicator")
        ui.label("操作示意圖 · 請在自己的手機上操作").classes("illustration-caption")


def sources(guide: dict):
    with ui.expansion("教學來源與適用版本", icon="info_outline").classes("source-panel w-full"):
        ui.label(guide["version_note"]).classes("small-copy")
        for source in guide["sources"]:
            ui.link(source["title"], source["url"], new_tab=True).classes("source-link")
            ui.label(f"官方文件核對：{source['checked_at']}").classes("small-copy")
