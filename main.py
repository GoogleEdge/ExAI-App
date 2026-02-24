import flet as ft
import threading
import time
import asyncio

def main(page: ft.Page):
    page.window.height, page.window.width = 800, 450
    page.horizontal_alignment, page.expand, page.bgcolor = ft.CrossAxisAlignment.CENTER, True, ft.Colors.GREY_900

    # 全局变量：主页统计
    todo_count = ft.Text("0", size=40, color=ft.Colors.CYAN, text_align=ft.TextAlign.CENTER)
    pomodoro_cycle = ft.Text("0", size=40, color=ft.Colors.ORANGE, text_align=ft.TextAlign.CENTER)
    
    # 新增：标记学习阶段是否完成
    focus_completed = False

    # 代办事项功能
    def delete_task(e, task_row):
        tasks_view.controls.remove(task_row)
        todo_count.value = str(len(tasks_view.controls))
        page.update()
    def add_clicked(e):
        if new_task.value.strip():
            task_checkbox = ft.Checkbox(label=new_task.value)
            task_row = ft.Row(controls=[])
            delete_btn = ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", on_click=lambda e, tr=task_row: delete_task(e, tr))
            task_row.controls = [task_checkbox, delete_btn]
            tasks_view.controls.append(task_row)
            todo_count.value = str(len(tasks_view.controls))
            new_task.value = ""
            page.update()
    new_task = ft.TextField(hint_text="What needs to be done?", expand=True, color=ft.Colors.WHITE)
    tasks_view = ft.Column()
    todo_content = ft.Column(
        width=400, expand=True, scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20,
        controls=[ft.Text("待办事项", size=30, color=ft.Colors.WHITE),ft.Row([new_task, ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=add_clicked)], spacing=10),tasks_view]
    )

    # 番茄钟核心：学习/休息双模式
    focus_seconds = 25 * 60
    rest_seconds = 5 * 60
    current_mode = "focus"
    timer_seconds = total_seconds = focus_seconds
    timer_running = False
    timer_thread = None

    async def async_update():
        page.update()
    def update_timer():
        if not page.session: return
        mins, secs = divmod(timer_seconds, 60)
        timer_display.value = f"{mins:02d}:{secs:02d}"
        page.run_task(async_update)

    # 切换学习/休息模式
    def switch_mode(e):
        nonlocal current_mode, timer_seconds, total_seconds, timer_running
        if timer_running:
            timer_running = False
            start_pause_btn.icon = ft.Icons.PLAY_ARROW
        # 模式切换+样式+时间+输入框提示更新
        if current_mode == "focus":
            current_mode = "rest"
            total_seconds = timer_seconds = rest_seconds
            focus_btn.bgcolor = ft.Colors.GREY_400
            rest_btn.bgcolor = ft.Colors.GREY_700
            time_input.hint_text = "输入休息时间（分钟）"
        else:
            current_mode = "focus"
            total_seconds = timer_seconds = focus_seconds
            focus_btn.bgcolor = ft.Colors.GREY_700
            rest_btn.bgcolor = ft.Colors.GREY_400
            time_input.hint_text = "输入学习时间（分钟）"
        update_timer()
        page.update()

    def set_timer(e):
        nonlocal total_seconds, timer_seconds, focus_seconds, rest_seconds
        try:
            mins = int(time_input.value.strip())
            if 1 <= mins <= 120:
                if current_mode == "focus":
                    focus_seconds = mins * 60
                else:
                    rest_seconds = mins * 60
                total_seconds = timer_seconds = mins * 60
                update_timer()
                time_input.value = ""
            else:
                if page.session:
                    timer_display.value = "请输入1-120"
                    page.update()
        except ValueError:
            if page.session:
                timer_display.value = "输入无效（需数字）"
                page.update()

    # 计时核心：修改为学习+休息都完成才计数（核心改动，新增约8行）
    def tick():
        nonlocal timer_seconds, timer_running, focus_completed
        while timer_seconds > 0 and timer_running and page.session:
            time.sleep(1)
            if timer_running and page.session:
                timer_seconds -= 1
                update_timer()
        if timer_running and page.session:
            # 学习阶段自然结束：标记完成
            if current_mode == "focus":
                focus_completed = True
            # 休息阶段自然结束：且学习阶段已完成 → 计数+1，重置标记
            elif current_mode == "rest" and focus_completed:
                pomodoro_cycle.value = str(int(pomodoro_cycle.value) + 1)
                focus_completed = False  # 重置标记
        timer_running = False
        if page.session:
            start_pause_btn.icon = ft.Icons.PLAY_ARROW
            page.run_task(async_update)

    # 启动/暂停一体化（修复线程创建语法，避免多线程加速）
    def start_pause(e):
        nonlocal timer_running, timer_thread
        if total_seconds <= 0 or not page.session:
            timer_display.value = "请先设置时间"
            page.update()
            return
        if not timer_running:
            timer_running = True
            if timer_thread is None or not timer_thread.is_alive():
                timer_thread = threading.Thread(target=tick, daemon=True)
                timer_thread.start()
            start_pause_btn.icon = ft.Icons.PAUSE
        else:
            timer_running = False
            start_pause_btn.icon = ft.Icons.PLAY_ARROW
        page.update()

    # 重置当前模式的时间：新增重置标记
    def reset_timer(e):
        nonlocal timer_seconds, timer_running, focus_completed
        if not page.session: return
        timer_running = False
        timer_seconds = total_seconds
        focus_completed = False  # 重置学习完成标记（1行新增）
        start_pause_btn.icon = ft.Icons.PLAY_ARROW
        update_timer()

    # 控制操作按钮显隐：修改逻辑为控制所有按钮组
    def toggle_buttons(e):
        if page.session:
            # 控制所有操作按钮的可见性
            mode_switch_row.visible = show_buttons_checkbox.value
            set_timer_row.visible = show_buttons_checkbox.value
            buttons_row.visible = show_buttons_checkbox.value
            page.update()

    # 基础控件/样式定义
    # 复选框默认值改为False
    show_buttons_checkbox = ft.Checkbox(
        label="显示操作按钮",
        value=False,  # 核心改动：默认隐藏
        label_style=ft.TextStyle(color=ft.Colors.WHITE),
        on_change=toggle_buttons
    )
    btn_rect_style = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=0))
    # 学习/休息切换按钮
    focus_btn = ft.CupertinoFilledButton("学习",icon=ft.Icons.LIBRARY_BOOKS,on_click=switch_mode, bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE, width=90)
    rest_btn = ft.CupertinoFilledButton("休息",icon=ft.Icons.SPA,on_click=switch_mode, bgcolor=ft.Colors.GREY_400, color=ft.Colors.WHITE, width=90)
    # 学习/休息按钮组默认隐藏
    mode_switch_row = ft.Row([focus_btn, rest_btn], spacing=-1, alignment=ft.MainAxisAlignment.CENTER, visible=False)
    
    # 番茄钟图标按钮+输入/显示控件
    start_pause_btn = ft.CupertinoFilledButton(icon=ft.Icons.PLAY_ARROW,icon_color=ft.Colors.WHITE,bgcolor=ft.Colors.BLACK,on_click=start_pause,width=60,height=50)
    reset_btn = ft.CupertinoFilledButton(icon=ft.Icons.REFRESH,icon_color=ft.Colors.WHITE,bgcolor=ft.Colors.BLACK,on_click=reset_timer,width=60,height=50)
    # 启动/重置按钮组默认隐藏
    buttons_row = ft.Row([start_pause_btn, reset_btn], spacing=20, alignment=ft.MainAxisAlignment.CENTER, visible=False)
    time_input = ft.TextField(hint_text="输入学习时间（分钟）", width=150, keyboard_type=ft.KeyboardType.NUMBER,color=ft.Colors.WHITE, hint_style=ft.TextStyle(color=ft.Colors.GREY_400))
    timer_display = ft.Text(f"{25:02d}:{00:02d}", size=40, color=ft.Colors.CYAN, text_align=ft.TextAlign.CENTER)

    # 设置时间按钮行（单独封装，便于控制显隐）
    set_timer_row = ft.Row(
        [time_input,ft.CupertinoFilledButton("设置时间",icon=ft.Icons.TIMER, on_click=set_timer, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)], 
        spacing=10, 
        alignment=ft.MainAxisAlignment.CENTER,
        visible=False  # 默认隐藏
    )

    # 番茄钟整体布局
    pomodoro_content = ft.Column(
        spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
        controls=[
            ft.Text("番茄学习计时器", size=25, color=ft.Colors.WHITE),
            mode_switch_row,  # 学习/休息切换按钮
            set_timer_row,    # 设置时间按钮行（替换原有Row）
            timer_display,
            ft.Row(controls=[show_buttons_checkbox], alignment=ft.MainAxisAlignment.CENTER),
            buttons_row
        ]
    )

    # 带边框的统计卡片组件
    def stat_card(title: str, value: ft.Text, color: ft.Colors) -> ft.Container:
        return ft.Container(
            width=180,height=150,border=ft.border.all(2, color),border_radius=10,padding=20,
            content=ft.Column(alignment=ft.MainAxisAlignment.CENTER,horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=15,controls=[ft.Text(title, size=20, color=ft.Colors.WHITE),value])
        )
    
    # 主页布局（带统计卡片）
    home_content = ft.Column(
        expand=True,horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=30,
        controls=[
            ft.Text("学习助手", size=40, color=ft.Colors.WHITE),
            ft.Text("选择下方功能开始使用", size=18, color=ft.Colors.GREY_300),
            ft.Divider(height=20, color=ft.Colors.GREY_700),
            ft.Row(spacing=40,alignment=ft.MainAxisAlignment.CENTER,controls=[stat_card("待办事项", todo_count, ft.Colors.CYAN),stat_card("番茄循环", pomodoro_cycle, ft.Colors.ORANGE)]),
            ft.Image(src="https://img.icons8.com/fluency/200/000000/study.png", width=150, height=150)
        ]
    )

    # AI分析+底部导航栏
    ai_content = ft.Column(expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,controls=[ft.Text("AI分析", size=30, color=ft.Colors.WHITE), ft.Text("功能开发中...", size=20, color=ft.Colors.GREY_300)])
    content_container = ft.Container(content=home_content, expand=True, alignment=ft.Alignment(0, 0))
    def on_nav_change(e):
        idx = e.control.selected_index
        content_map = {0: home_content, 1: pomodoro_content, 2: todo_content, 3: ai_content}
        content_container.content = content_map[idx]
        page.update()
    nav_items = [ft.NavigationBarDestination(icon=ft.Icons.HOME, selected_icon=ft.Icons.HOME_ROUNDED, label="主页"),ft.NavigationBarDestination(icon=ft.Icons.TIMER, selected_icon=ft.Icons.TIMER_ROUNDED, label="番茄时间"),ft.NavigationBarDestination(icon=ft.Icons.CHECKLIST, selected_icon=ft.Icons.CHECKLIST_ROUNDED, label="代办区"),ft.NavigationBarDestination(icon=ft.Icons.ANALYTICS, selected_icon=ft.Icons.ANALYTICS_ROUNDED, label="AI分析")]
    bottom_nav = ft.NavigationBar(destinations=nav_items, selected_index=0, on_change=on_nav_change, bgcolor=ft.Colors.GREY_900, height=70)
    page.add(ft.Column([content_container, bottom_nav], expand=True, spacing=0))

ft.app(target=main)