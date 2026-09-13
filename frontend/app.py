"""Run separately with python -m frontend.app. All domain access uses HTTP."""

from nicegui import app, ui

from frontend.api import APIClient, APIError
from frontend.components import (
    button,
    illustration,
    scroll_top,
    sources,
    speech_button,
    stop_speech,
)
from frontend.config import ROOT, FrontendSettings, storage_secret
from frontend.speech_proxy import create_speech_proxy

settings = FrontendSettings()
api = APIClient(settings.api_url)
app.include_router(create_speech_proxy(settings.api_url))
app.add_static_files("/voice-assets", ROOT / "frontend" / "static")


@ui.page("/", title="慢慢來 · 手機小幫手")
async def index():
    # NiceGUI 只負責畫面與互動；所有教學、搜尋和進度資料都透過 HTTP API 取得。
    ui.add_css((ROOT / "frontend" / "styles.css").read_text(encoding="utf-8"))
    ui.add_head_html('<script src="/voice-assets/voice.js?v=4"></script>')
    ui.colors(primary="#29674f", secondary="#a4bb92", accent="#c39952", positive="#29674f")
    memory = app.storage.user
    state = {
        # 這些是目前瀏覽器分頁的暫存狀態，不會取代後端 SQLite 進度。
        "session": None,
        "selected": None,
        "results": None,
        "suggestions": [],
        "help": None,
        "error": "",
        "screen": "home",
        "busy": False,
        "voice_text": "",
    }

    async def execute(job):
        if state["busy"]:
            return
        state["busy"] = True
        busy_spinner.set_visibility(True)
        try:
            await job()
            state["error"] = ""
        except APIError as exc:
            state["error"] = str(exc)
            if exc.status == 409 and state["session"]:
                try:
                    state["session"] = await api.request(
                        "GET", f"/api/sessions/{state['session']['id']}"
                    )
                except APIError:
                    pass
        finally:
            state["busy"] = False
            busy_spinner.set_visibility(False)
            content.refresh()

    async def load():
        if memory.get("session_id"):
            try:
                state["session"] = await api.request("GET", f"/api/sessions/{memory['session_id']}")
                state["screen"] = memory.get("screen", "home")
            except APIError as exc:
                if exc.status != 404:
                    raise
                memory.pop("session_id", None)
                memory["screen"] = "home"
                state["screen"] = "home"

    def go_home():
        stop_speech()
        state.update(screen="home", results=None, suggestions=[], error="", help=None)
        memory["screen"] = "home"
        content.refresh()
        scroll_top()

    def choose_input(mode):
        state["screen"] = "voice" if mode == "voice" else "text"
        content.refresh()
        scroll_top()

    def show_intro(guide):
        stop_speech()
        state.update(selected=guide, screen="intro", help=None, error="")
        content.refresh()
        scroll_top()

    async def start():
        async def job():
            state["session"] = await api.request(
                "POST", "/api/sessions", {"guide_id": state["selected"]["id"], "platform": "ios"}
            )
            memory["session_id"] = state["session"]["id"]
            memory["screen"] = "guide"
            state.update(screen="guide", help=None)

        await execute(job)
        scroll_top()

    async def search(query):
        if not query.strip():
            ui.notify("可以直接點下面的教學，或輸入想做的事。", type="info")
            return

        async def job():
            result = await api.request("POST", "/api/search", {"query": query, "platform": "ios"})
            state.update(
                results=[hit["guide"] for hit in result["hits"]],
                suggestions=[hit["guide"] for hit in result.get("suggestions", [])],
                screen="result",
            )

        await execute(job)

    async def act(action):
        stop_speech()

        async def job():
            session = state["session"]
            state["session"] = await api.request(
                "POST",
                f"/api/sessions/{session['id']}/actions",
                {"action": action, "expected_revision": session["revision"]},
            )
            state["help"] = None

        await execute(job)
        ui.run_javascript("document.getElementById('step-title')?.focus()")

    async def ask(question="這一步找不到，請幫幫我"):
        async def job():
            state["help"] = await api.request(
                "POST", f"/api/sessions/{state['session']['id']}/help", {"question": question}
            )

        await execute(job)
        ui.run_javascript("document.getElementById('help-panel')?.focus()")

    with ui.element("header").classes("site-header"):
        with ui.row().classes("header-inner"):
            with ui.row().classes("brand"):
                ui.icon("spa", size="28px").classes("brand-icon")
                with ui.column().classes("gap-0"):
                    ui.label("慢慢來").classes("brand-title")
                    ui.label("手機小幫手").classes("brand-sub")
            with ui.row().classes("header-actions"):

                def toggle_size():
                    memory["large_type"] = not memory.get("large_type", False)
                    shell.classes(
                        add="large-type" if memory["large_type"] else "",
                        remove="" if memory["large_type"] else "large-type",
                    )
                    size_button.set_text("恢復原字級" if memory["large_type"] else "字再大一點")

                size_button = (
                    button(
                        "恢復原字級" if memory.get("large_type") else "字再大一點",
                        icon="text_increase",
                        on_click=toggle_size,
                    )
                    .props("flat no-caps")
                    .classes("text-button")
                )

    shell = ui.column().classes(
        "main-shell large-type" if memory.get("large_type") else "main-shell"
    )
    with shell:
        busy_spinner = (
            ui.row().classes("items-center gap-3").props('role="status" aria-live="polite"')
        )
        with busy_spinner:
            ui.spinner(size="26px", color="primary")
            ui.label("正在準備，請稍等一下…").classes("small-copy")
        busy_spinner.set_visibility(False)

        @ui.refreshable
        def content():
            if state["error"]:
                with ui.column().classes("error-panel").props('role="alert"'):
                    ui.label(state["error"])
                    button("重新連線", icon="refresh", on_click=lambda: execute(load)).classes(
                        "secondary-button"
                    )
            if state["screen"] == "intro":
                render_intro()
            elif state["screen"] == "voice":
                render_voice()
            elif state["screen"] == "text":
                render_text()
            elif state["screen"] == "result":
                render_result()
            elif state["screen"] == "guide" and state["session"]:
                render_learning()
            else:
                render_home()

        def render_home():
            with ui.column().classes("search-section"):
                ui.label("你遇到什麼困難？").classes("search-title")
                ui.label("請選擇你比較方便的方式").classes("small-copy")
                with ui.column().classes("input-choice-list"):
                    button("用語音說", icon="mic", on_click=lambda: choose_input("voice")).classes(
                        "primary-button choice-button"
                    )
                    button(
                        "用文字打字", icon="keyboard", on_click=lambda: choose_input("text")
                    ).props("outline").classes("secondary-button choice-button")

        def render_result():
            with ui.column().classes("input-page"):
                button("重新輸入", icon="arrow_back", on_click=go_home).props("flat")
                if state["results"]:
                    guide = state["results"][0]
                    ui.label("最接近這份教學").classes("small-copy")
                    ui.label(guide["title"]).classes("page-title")
                    ui.label(guide["summary"]).classes("guide-copy")
                    button("開始教學", on_click=lambda: show_intro(guide)).classes("primary-button")
                    alternatives = state["results"][1:] + state["suggestions"]
                    if alternatives:
                        render_suggestions(alternatives)
                elif state["suggestions"]:
                    ui.label("你是不是要找這些？").classes("page-title")
                    ui.label("請選一份最接近你想做的事的教學。").classes("small-copy")
                    render_suggestions(state["suggestions"], show_heading=False)
                else:
                    ui.label("還沒找到合適的教學").classes("page-title")
                    ui.label("請換個說法，再試一次。").classes("small-copy")

        def render_suggestions(guides, show_heading=True):
            with ui.column().classes("suggestion-list"):
                if show_heading:
                    ui.label("你是不是要找？").classes("search-title suggestion-heading")
                for guide in guides:
                    with ui.card().classes("suggestion-card"):
                        ui.label(guide["title"]).classes("guide-title")
                        ui.label(guide["summary"]).classes("guide-copy")
                        button(
                            "查看這份教學",
                            icon="arrow_forward",
                            on_click=lambda g=guide: show_intro(g),
                        ).props("outline").classes("secondary-button")

        def render_voice():
            state["voice_text"] = ""
            with ui.column().classes("input-page").props('id="voice-page"') as voice_page:
                button("回上一頁", icon="arrow_back", on_click=go_home).props("flat").classes(
                    "back-link"
                )
                ui.label("用語音告訴我").classes("page-title")
                ui.label("請按下麥克風開始").classes("voice-status").props('id="voice-status"')
                with (
                    ui.element("div")
                    .classes("voice-wave")
                    .props('id="voice-wave" aria-label="語音接收狀態"')
                ):
                    for _ in range(18):
                        ui.element("span")
                button("開始錄音", icon="mic").classes("primary-button record-button").props(
                    'id="voice-start"'
                ).on("click", js_handler="() => window.ElderVoice.toggle()")
                ui.element("audio").props('id="voice-audio" preload="metadata" hidden')
                button("播放剛才錄音", icon="play_arrow").classes(
                    "secondary-button playback-button"
                ).props('id="voice-playback" hidden').on(
                    "click", js_handler="() => window.ElderVoice.play()"
                )
                ui.label("").classes("voice-transcript").props(
                    'id="voice-transcript" aria-live="polite" hidden'
                )
                search_button = button(
                    "找教學", icon="search", on_click=lambda: search(state["voice_text"])
                ).classes("primary-button")
                search_button.set_visibility(False)

                def on_transcribed(event):
                    state["voice_text"] = str(event.args["detail"].get("text", ""))
                    search_button.set_visibility(bool(state["voice_text"]))

                voice_page.on("voice-result", on_transcribed, args=["detail"])

        def render_text():
            with ui.column().classes("input-page"):
                button("回上一頁", icon="arrow_back", on_click=go_home).props("flat").classes(
                    "back-link"
                )
                ui.label("用文字告訴我").classes("page-title")
                ui.label("請輸入你想解決的困難。").classes("input-help")
                query = (
                    ui.input(placeholder="例如：LINE 的字太小")
                    .props('outlined aria-label="想學的手機功能" maxlength=200')
                    .classes("text-query")
                )
                query.on("keydown.enter", lambda: search(query.value or ""))
                button("找教學", icon="search", on_click=lambda: search(query.value or "")).classes(
                    "primary-button"
                )

        def render_intro():
            guide = state["selected"]
            button("回到所有教學", icon="arrow_back", on_click=go_home).props("flat").classes(
                "back-link"
            )
            with ui.column().classes("intro-card"):
                ui.icon(guide["icon"], size="36px").classes("guide-icon")
                ui.label(guide["title"]).classes("page-title")
                ui.label(
                    f"約 {guide['estimated_minutes']} 分鐘 · 共 {len(guide['steps'])} 步 · iPhone"
                ).classes("small-copy")
                ui.label("開始前，先準備一下").classes("search-title")
                for note in guide["prerequisites"]:
                    with ui.row().classes("intro-item"):
                        ui.icon("check_circle_outline", size="24px")
                        ui.label(note)
                ui.label("一次只看一步。做好後按「做到了」，找不到就按「這一步找不到」。").classes(
                    "guide-copy"
                )
                button("準備好了，開始第一步", icon="play_arrow", on_click=start).classes(
                    "primary-button intro-action"
                )
                sources(guide)

        def render_learning():
            session = state["session"]
            guide = session["guide"]
            with ui.row().classes("learning-top"):
                ui.label(guide["title"]).classes("learning-title")
                button("先休息，保留進度", icon="pause_circle_outline", on_click=go_home).props(
                    "flat"
                ).classes("back-link")
            if session["status"] == "completed":
                with ui.column().classes("completion"):
                    ui.icon("check", size="54px").classes("complete-icon")
                    ui.label("你已經走完這份教學了！").classes("page-title").props(
                        'id="step-title" tabindex="-1"'
                    )
                    ui.label(guide["outcome"]).classes("instruction")
                    ui.label("完成記錄來自你按下的確認；請再看一下手機上的實際效果。").classes(
                        "small-copy"
                    )
                    button("再練習一次", icon="replay", on_click=lambda: act("restart")).classes(
                        "primary-button"
                    )
                    button("看看其他教學", on_click=go_home).props("outline").classes(
                        "secondary-button"
                    )
                sources(guide)
                return
            step = session["current_step"]
            with ui.column().classes("learning-shell"):
                with ui.row().classes("step-meta"):
                    ui.label(
                        f"第 {session['step_index'] + 1} 步，共 {session['total_steps']} 步"
                    ).classes("step-count")
                    with ui.element("div").classes("progress-track").props('aria-hidden="true"'):
                        for i in range(session["total_steps"]):
                            ui.element("div").classes(
                                "progress-segment "
                                + (
                                    "done"
                                    if i < session["step_index"]
                                    else "current"
                                    if i == session["step_index"]
                                    else ""
                                )
                            )
                with ui.element("div").classes("learning-grid"):
                    with ui.column().classes("step-content"):
                        ui.label(step["title"]).classes("step-title").props(
                            'id="step-title" tabindex="-1" role="heading" aria-level="1"'
                        )
                        ui.label(step["instruction"]).classes("instruction")
                        with ui.row().classes("step-tools"):
                            speech_button(
                                step["title"]
                                + "。"
                                + step["instruction"]
                                + "。"
                                + step["checkpoint"]
                            )
                            button("停止朗讀", on_click=stop_speech).props("flat").classes(
                                "back-link"
                            )
                        ui.label("按「唸給我聽」，就能聽這一步的說明。").classes(
                            "voice-status"
                        ).props('id="voice-status" role="status" aria-live="polite"')
                        with ui.row().classes("checkpoint"):
                            ui.icon("task_alt", size="26px")
                            ui.label(step["checkpoint"])
                    with ui.column().classes("desktop-illustration"):
                        illustration(step["illustration"])
                    with ui.expansion("看圖找按鈕", icon="image").classes("mobile-illustration"):
                        illustration(step["illustration"])
                with ui.row().classes("learning-actions"):
                    label = (
                        "做到了，完成教學"
                        if session["step_index"] == session["total_steps"] - 1
                        else "做到了，下一步"
                    )
                    button(label, icon="check", on_click=lambda: act("next")).classes(
                        "primary-button next-button"
                    )
                    button("這一步找不到", icon="help_outline", on_click=lambda: ask()).classes(
                        "help-button"
                    )
                with ui.row().classes("section-row"):
                    back = (
                        button("回上一步", icon="arrow_back", on_click=lambda: act("back"))
                        .props("flat")
                        .classes("step-back")
                    )
                    back.set_enabled(session["step_index"] > 0)
                    ui.label("慢慢來，完成了再往下走。").classes("learning-reminder")
            if state["help"]:
                answer = state["help"]
                with (
                    ui.column()
                    .classes("help-panel")
                    .props("id=help-panel tabindex=-1")
                    .props('role="status" aria-live="polite"')
                ):
                    ui.label("沒關係，我們一起找找看").classes("help-title")
                    ui.label(answer["answer"]).classes("help-answer")
                    if answer["mode"] == "ai":
                        ui.label("AI 補充說明，請以這一步的教學為準。").classes("small-copy")
                        with ui.expansion("查看參考內容").classes("w-full"):
                            for passage in answer["passages"]:
                                ui.label(passage["text"]).classes("small-copy")
                    elif answer["mode"] == "fallback":
                        ui.label("先用教學裡的提示陪你操作。").classes("small-copy")
                    question = (
                        ui.input("想再問問這份教學", placeholder="例如：字太大可以改回來嗎？")
                        .props("outlined maxlength=300")
                        .classes("help-question")
                    )
                    button(
                        "看看說明",
                        icon="question_answer",
                        on_click=lambda: ask(question.value or "這一步找不到"),
                    ).classes("secondary-button")
                    ui.label("如果畫面一直不同，可以先保留進度，請家人一起看。").classes(
                        "small-copy"
                    )
            sources(guide)

        content()
    await execute(load)


def main():
    ui.run(
        host=settings.ui_host,
        port=settings.ui_port,
        reload=False,
        show=False,
        title="慢慢來 · 手機小幫手",
        favicon="🌿",
        language="zh-TW",
        storage_secret=storage_secret(settings),
    )


if __name__ == "__main__":
    main()
