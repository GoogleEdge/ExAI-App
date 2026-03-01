import flet as ft
import threading
import time
import asyncio
import tkinter as tk
from tkinter import filedialog
import os
import requests
import json
import sqlite3
import datetime
from contextlib import closing

AI_CHAT_URL = "http://127.0.0.1:8100/ai/chat/simple"
AI_HEADERS = {"Token": "your_token_here"}

class StudyDB:
    def __init__(self, db_path="study_app.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("PRAGMA encoding = 'UTF-8'")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS todo_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL COLLATE NOCASE,
                    is_completed INTEGER DEFAULT 0,
                    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pomodoro_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    duration INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('focus', 'rest')),
                    complete_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    def get_all_tasks(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM todo_tasks ORDER BY create_time DESC")
            return [dict(row) for row in cursor.fetchall()]

    def add_task(self, content):
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO todo_tasks (content) VALUES (?)",
                (content.strip(),)
            )
            conn.commit()
            return cursor.lastrowid

    def delete_task(self, task_id):
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM todo_tasks WHERE id = ?",
                (task_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_task_status(self, task_id, is_completed):
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            status = 1 if is_completed else 0
            cursor.execute(
                "UPDATE todo_tasks SET is_completed = ? WHERE id = ?",
                (status, task_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def add_pomodoro_record(self, duration, type_):
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pomodoro_records (duration, type) VALUES (?, ?)",
                (int(duration), type_.lower())
            )
            conn.commit()
            return cursor.lastrowid

    def get_pomodoro_count(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM pomodoro_records WHERE type = ?",
                ('focus',)
            )
            return cursor.fetchone()[0]

def main(page: ft.Page):
    try:
        db = StudyDB()
    except sqlite3.Error as e:
        print(f"数据库初始化错误: {e}")
        error_dialog = ft.AlertDialog(
            title=ft.Text("数据库错误"),
            content=ft.Text(f"无法初始化数据库：{str(e)}"),
            actions=[ft.TextButton("确定", on_click=lambda e: error_dialog.close(page))]
        )
        page.dialog = error_dialog
        error_dialog.open = True
        page.update()
        return
    page.window.height = 800
    page.window.width = 450
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.expand = True
    page.bgcolor = ft.Colors.GREY_900
    try:
        todo_count_val = len(db.get_all_tasks())
        pomodoro_count_val = db.get_pomodoro_count()
    except sqlite3.Error as e:
        todo_count_val = 0
        pomodoro_count_val = 0
        print(f"加载数据错误: {e}")
    
    todo_count = ft.Text(str(todo_count_val), size=40, color=ft.Colors.CYAN, text_align=ft.TextAlign.CENTER)
    pomodoro_cycle = ft.Text(str(pomodoro_count_val), size=40, color=ft.Colors.ORANGE, text_align=ft.TextAlign.CENTER)

    focus_completed = False
    empty_tip = ft.Text(
        "没有未完成任务真棒！",
        size=18,
        color=ft.Colors.GREEN,
        text_align=ft.TextAlign.CENTER,
        visible=todo_count_val == 0
    )

    def update_empty_tip():
        has_tasks = len(tasks_view.controls) > 0
        empty_tip.visible = not has_tasks
        page.update()

    def delete_task(e, task_row, task_id):
        try:
            task_id = int(task_id)
            if db.delete_task(task_id):
                tasks_view.controls.remove(task_row)
                todo_count.value = str(len(tasks_view.controls))
                update_empty_tip()
                page.update()
        except (sqlite3.Error, ValueError) as e:
            print(f"删除任务错误: {e}")
            error_dialog = ft.AlertDialog(
                title=ft.Text("操作错误"),
                content=ft.Text(f"删除任务失败：{str(e)}"),
                actions=[ft.TextButton("确定", on_click=lambda e: error_dialog.close(page))]
            )
            page.dialog = error_dialog
            error_dialog.open = True
            page.update()
        
    def on_task_check(e, task_id):
        """更新待办事项完成状态（同步数据库）"""
        try:
            task_id = int(task_id)
            db.update_task_status(task_id, e.control.value)
        except (sqlite3.Error, ValueError) as e:
            print(f"更新任务状态错误: {e}")
    
    def add_clicked(e):
        """添加待办事项（同步数据库，处理特殊字符）"""
        content = new_task.value.strip()
        if not content:
            return
            
        try:
            task_id = db.add_task(content)
            if task_id:
                task_checkbox = ft.Checkbox(
                    label=content,
                    on_change=lambda e, tid=task_id: on_task_check(e, tid)
                )
                task_row = ft.Row(controls=[])
                delete_btn = ft.IconButton(
                    icon=ft.Icons.DELETE, 
                    icon_color="red", 
                    on_click=lambda e, tr=task_row, tid=task_id: delete_task(e, tr, tid)
                )
                task_row.controls = [task_checkbox, delete_btn]
                task_row.task_id = task_id
                tasks_view.controls.append(task_row)
                todo_count.value = str(len(tasks_view.controls))
                new_task.value = ""
                update_empty_tip()
                page.update()
        except sqlite3.Error as e:
            print(f"添加任务错误: {e}")
            error_dialog = ft.AlertDialog(
                title=ft.Text("操作错误"),
                content=ft.Text(f"添加任务失败：{str(e)}"),
                actions=[ft.TextButton("确定", on_click=lambda e: error_dialog.close(page))]
            )
            page.dialog = error_dialog
            error_dialog.open = True
            page.update()
            
    def load_tasks_from_db():
        """从数据库加载待办事项到UI（添加错误处理）"""
        try:
            tasks = db.get_all_tasks()
            for task in tasks:
                task_id = int(task['id'])
                content = str(task['content'])
                is_completed = bool(task['is_completed'])
                
                task_checkbox = ft.Checkbox(
                    label=content,
                    value=is_completed,
                    on_change=lambda e, tid=task_id: on_task_check(e, tid)
                )
                task_row = ft.Row(controls=[])
                delete_btn = ft.IconButton(
                    icon=ft.Icons.DELETE, 
                    icon_color="red", 
                    on_click=lambda e, tr=task_row, tid=task_id: delete_task(e, tr, tid)
                )
                task_row.controls = [task_checkbox, delete_btn]
                task_row.task_id = task_id
                tasks_view.controls.append(task_row)
            update_empty_tip()
        except sqlite3.Error as e:
            print(f"加载任务错误: {e}")
            error_dialog = ft.AlertDialog(
                title=ft.Text("加载错误"),
                content=ft.Text(f"无法加载待办事项：{str(e)}"),
                actions=[ft.TextButton("确定", on_click=lambda e: error_dialog.close(page))]
            )
            page.dialog = error_dialog
            error_dialog.open = True
            page.update()
    
    new_task = ft.TextField(
        hint_text="What needs to be done?", 
        expand=True, 
        color=ft.Colors.WHITE,
    )
    tasks_view = ft.Column(spacing=10) 
    load_tasks_from_db()
    
    todo_content = ft.Column(
        width=400, 
        expand=True, 
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
        spacing=15,
        controls=[
            ft.Text("待办事项", size=30, color=ft.Colors.WHITE),
            ft.Row([new_task, ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=add_clicked)], spacing=10),
            empty_tip,
            tasks_view 
        ]
    )
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

    def switch_mode(e):
        nonlocal current_mode, timer_seconds, total_seconds, timer_running
        if timer_running:
            timer_running = False
            start_pause_btn.icon = ft.Icons.PLAY_ARROW
        if current_mode == "focus":
            current_mode = "rest"
            total_seconds = timer_seconds = rest_seconds
            focus_btn.bgcolor = ft.Colors.GREY_400
            rest_btn.bgcolor = ft.Colors.GREY_700
        else:
            current_mode = "focus"
            total_seconds = timer_seconds = focus_seconds
            focus_btn.bgcolor = ft.Colors.GREY_700
            rest_btn.bgcolor = ft.Colors.GREY_400
        update_timer()
        page.update()

    def tick():
        nonlocal timer_seconds, timer_running, focus_completed
        while timer_seconds > 0 and timer_running and page.session:
            time.sleep(1)
            if timer_running and page.session:
                timer_seconds -= 1
                update_timer()
        
        if timer_running and page.session:
            try:
                db.add_pomodoro_record(total_seconds, current_mode)
                
                if current_mode == "focus":
                    focus_completed = True
                elif current_mode == "rest" and focus_completed:
                    pomodoro_cycle.value = str(db.get_pomodoro_count())
                    focus_completed = False
            except sqlite3.Error as e:
                print(f"记录番茄钟错误: {e}")
            
        timer_running = False
        if page.session:
            start_pause_btn.icon = ft.Icons.PLAY_ARROW
            page.run_task(async_update)

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

    def reset_timer(e):
        nonlocal timer_seconds, timer_running, focus_completed
        if not page.session: return
        timer_running = False
        timer_seconds = total_seconds
        focus_completed = False
        start_pause_btn.icon = ft.Icons.PLAY_ARROW
        update_timer()

    # 删除：显示操作按钮相关代码
    focus_btn = ft.CupertinoFilledButton("学习",icon=ft.Icons.LIBRARY_BOOKS,on_click=switch_mode, bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE, width=90)
    rest_btn = ft.CupertinoFilledButton("休息",icon=ft.Icons.SPA,on_click=switch_mode, bgcolor=ft.Colors.GREY_400, color=ft.Colors.WHITE, width=90)
    mode_switch_row = ft.Row([focus_btn, rest_btn], spacing=-1, alignment=ft.MainAxisAlignment.CENTER)  # 删除visible=False
    start_pause_btn = ft.CupertinoFilledButton(icon=ft.Icons.PLAY_ARROW,icon_color=ft.Colors.WHITE,bgcolor=ft.Colors.BLACK,on_click=start_pause,width=60,height=50)
    reset_btn = ft.CupertinoFilledButton(icon=ft.Icons.REFRESH,icon_color=ft.Colors.WHITE,bgcolor=ft.Colors.BLACK,on_click=reset_timer,width=60,height=50)
    buttons_row = ft.Row([start_pause_btn, reset_btn], spacing=20, alignment=ft.MainAxisAlignment.CENTER)  # 删除visible=False
    timer_display = ft.Text(f"{25:02d}:{00:02d}", size=40, color=ft.Colors.CYAN, text_align=ft.TextAlign.CENTER)

    pomodoro_content = ft.Column(
        spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
        controls=[
            ft.Text("番茄学习计时器", size=25, color=ft.Colors.WHITE),
            mode_switch_row,
            timer_display,
            buttons_row  # 直接显示按钮，不再通过复选框控制
        ]
    )

    def stat_card(title: str, value: ft.Text, color: ft.Colors) -> ft.Container:
        return ft.Container(
            width=180,height=150,border=ft.Border.all(2, color),border_radius=10,padding=20,
            content=ft.Column(alignment=ft.MainAxisAlignment.CENTER,horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=15,controls=[ft.Text(title, size=20, color=ft.Colors.WHITE),value])
        )
    ai_chat_messages = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=10
    )
    
    ai_chat_container = ft.Container(
        content=ai_chat_messages,
        padding=10,
        expand=True
    )
    
    async def call_ai_api(message):
        """调用AI聊天接口并返回结果"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    AI_CHAT_URL,
                    headers=AI_HEADERS,
                    json={"message": message},
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                if "answer" in result:
                    return result["answer"]
                elif "response" in result:
                    return result["response"]
                elif "message" in result:
                    return result["message"]
                else:
                    return json.dumps(result, ensure_ascii=False)
            else:
                return f"接口返回错误：状态码 {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return "❌ 无法连接到AI服务"
        except requests.exceptions.Timeout:
            return "❌ 请求超时，请稍后重试"
        except Exception as e:
            return f"❌ 发生错误：{str(e)}"
    
    async def send_ai_question_async(e):
        """异步处理AI问题发送"""
        user_input = ai_question_input.value.strip()
        if not user_input:
            return
        user_message = ft.Container(
            content=ft.Text(user_input, color=ft.Colors.WHITE, size=14),
            bgcolor=ft.Colors.BLUE_700,
            padding=10,
            border_radius=10,
            alignment=ft.alignment.Alignment(x=1, y=0),
            width=page.width * 0.6
        )
        ai_chat_messages.controls.append(user_message)
        ai_question_input.value = ""
        loading_reply = ft.Container(
            content=ft.Text("我已收到你的问题，正在思考中...", color=ft.Colors.BLACK, size=14),bgcolor=ft.Colors.GREY_300,padding=10,border_radius=10,alignment=ft.alignment.Alignment(x=-1, y=0),width=page.width * 0.6)

        loading_index = len(ai_chat_messages.controls)
        ai_chat_messages.controls.append(loading_reply)
        page.update()
        ai_response = await call_ai_api(user_input)
        ai_chat_messages.controls[loading_index] = ft.Container(content=ft.Text(ai_response, color=ft.Colors.BLACK, size=14),bgcolor=ft.Colors.GREY_300,padding=10,border_radius=10,alignment=ft.alignment.Alignment(x=-1, y=0),width=page.width * 0.6)
        ai_chat_messages.scroll_to(offset=0, alignment=1.0)
        page.update()
    
    def send_ai_question(e):
        """包装成同步函数供按钮调用"""
        page.run_task(send_ai_question_async, e)
    
    ai_question_input = ft.TextField(
        hint_text="向AI助手提问",
        expand=True,
        color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(color=ft.Colors.GREY_400),
    )
    send_question_btn = ft.CupertinoFilledButton("发送",icon=ft.Icons.SEND,bgcolor=ft.Colors.BLUE,color=ft.Colors.WHITE,on_click=send_ai_question)
    ai_input_row = ft.Row([ai_question_input, send_question_btn], spacing=10)
    ai_input_container = ft.Container(content=ai_input_row, padding=10)
    ai_assistant_card = ft.Container(width=400,height=300,border=ft.Border.all(2, ft.Colors.PURPLE),border_radius=10,padding=10,content=ft.Column(expand=True,controls=[ft.Text("AI学习助手", size=20, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),ai_chat_container,ai_input_container]))
    
    home_content = ft.Column(
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
        alignment=ft.MainAxisAlignment.CENTER,        
        spacing=20,
        controls=[
            ft.Text("学习助手", size=40, color=ft.Colors.WHITE),
            ft.Text("选择下方功能开始使用", size=30, color=ft.Colors.GREY_300),
            ft.Container(content=ft.Divider(color=ft.Colors.GREY_700), width=600),
            ft.Row(
                spacing=40,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[stat_card("待办事项", todo_count, ft.Colors.CYAN),stat_card("番茄循环", pomodoro_cycle, ft.Colors.ORANGE)]
            ),
            ai_assistant_card,
            ft.Image(src="https://img.icons8.com/fluency/200/000000/study.png", width=150, height=150),
        ]
    )

    # ========== 图片上传 ==========
    def upload_image(e):
        root = tk.Tk()
        root.withdraw() 
        root.attributes('-topmost', True) 
        
        file_path = filedialog.askopenfilename(
            title="选择要分析的图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            file_name = os.path.basename(file_path)
            ai_image_status.value = f"✅ 已选择图片：{file_name}"
            ai_analysis_result.value = f"📊 正在分析图片：{file_name}（大小：{os.path.getsize(file_path)//1024}KB）"
        else:
            ai_image_status.value = "❌ 未选择任何图片"
            ai_analysis_result.value = ""
        
        page.update()
    
    upload_image_btn = ft.CupertinoFilledButton("上传图片分析问题",icon=ft.Icons.UPLOAD_FILE,bgcolor=ft.Colors.GREEN,color=ft.Colors.WHITE,on_click=upload_image  )
    
    ai_image_status = ft.Text("", size=16, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)
    ai_analysis_result = ft.Text("", size=16, color=ft.Colors.CYAN, text_align=ft.TextAlign.CENTER)
    ai_content = ft.Column(
        expand=True, 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=30,
        controls=[ft.Text("AI分析", size=30, color=ft.Colors.WHITE),upload_image_btn,ai_image_status,ai_analysis_result,])
    content_container = ft.Container(content=home_content, expand=True, alignment=ft.Alignment(0, 0))
    
    def on_nav_change(e):
        idx = e.control.selected_index
        content_map = {0: home_content, 1: pomodoro_content, 2: todo_content, 3: ai_content}
        content_container.content = content_map[idx]
        page.update()
        
    nav_items = [
        ft.NavigationBarDestination(icon=ft.Icons.HOME, selected_icon=ft.Icons.HOME_ROUNDED, label="主页"),
        ft.NavigationBarDestination(icon=ft.Icons.TIMER, selected_icon=ft.Icons.TIMER_ROUNDED, label="番茄时间"),
        ft.NavigationBarDestination(icon=ft.Icons.CHECKLIST, selected_icon=ft.Icons.CHECKLIST_ROUNDED, label="代办区"),
        ft.NavigationBarDestination(icon=ft.Icons.ANALYTICS, selected_icon=ft.Icons.ANALYTICS_ROUNDED, label="AI分析")
    ]
    
    bottom_nav = ft.NavigationBar(destinations=nav_items, selected_index=0, on_change=on_nav_change, bgcolor=ft.Colors.GREY_800, height=70)
    
    page.add(ft.Column([content_container, bottom_nav], expand=True, spacing=0))

if __name__ == "__main__":
    ft.app(target=main)
