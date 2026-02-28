import base64
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import TypedDict
import uuid

from dotenv import load_dotenv
import fastapi
from fastapi.staticfiles import StaticFiles
import numpy as np
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from ultralytics import YOLO
import uvicorn
import yaml
import zai
    

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

class _TaskInfo(TypedDict):
    status: TaskStatus
    result: dict[str, any] | None 
    error: str | None

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str

class ExamMarksRequest(BaseModel):
    username: str
    exam_names: str
    subject: str
    difficulty: str
    grade: str
    marks: int

type TaskDict = dict[str, _TaskInfo]
tasks: TaskDict = {}
ml_models = {}
embedding_model = None

def get_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return str(uuid.uuid4())

def sqlite_init():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    print("用户表检查成功！")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            exam_names TEXT NOT NULL,
            subject TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            grade TEXT NOT NULL,
            marks INTEGER NOT NULL
        )
    ''')
    conn.commit()
    print("考试成绩表检查成功！")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wrong_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            wrong_reason TEXT NOT NULL,
            grade TEXT NOT NULL,
            source TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            subject TEXT NOT NULL,
            file_name TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding_json TEXT,
            next_review_date TEXT,
            review_count INTEGER DEFAULT 0,
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    print("错题表检查成功！")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            grade TEXT NOT NULL,
            question_text TEXT NOT NULL,
            similar_question TEXT,
            similar_answer TEXT,
            embedding_json TEXT
        )
    ''')
    conn.commit()
    print("题库表检查成功！")
    conn.close()

def config_init():
    config = {
        'users_db': {
            'path': 'users.db'
        },
        'zhipu_ai': {
            'model': 'glm-4.7-flash',
            'v_model': 'glm-4.6v-flash',
        },
        'upload_file_path': {
            'path': 'uploaded_files'
        },
        'yolo_model': {
            'path': 'yolo_model.pt'
        }
    }
    
    if not os.path.exists('config.yaml'):
        with open('config.yaml', 'w') as yaml_file:
            yaml.dump(config, yaml_file)
            print("配置文件创建成功！")
    
    upload_dir = config['upload_file_path']['path']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
        print(f"创建上传目录: {upload_dir}")

def read_config():
    with open('config.yaml', 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
        print("配置文件读取成功！")
    return config

def verify_token(token: str, conn: sqlite3.Connection) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE token=?", (token,))
    result = cursor.fetchone()
    return result is not None

def calculate_ebbinghaus(review_count: int, ease_factor: float, interval_days: int, quality: int):
    if quality < 3:
        new_review_count = 0
        interval_days = 1
    else:
        new_review_count = review_count + 1
        if review_count == 0:
            interval_days = 1
        elif review_count == 1:
            interval_days = 6
        else:
            interval_days = int(interval_days * ease_factor)
        
        ease_factor = max(1.3, ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    
    next_date = (datetime.now() + timedelta(days=interval_days)).strftime('%Y-%m-%d')
    
    return next_date, new_review_count, ease_factor, interval_days
    
allowed_image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
allowed_image_types = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}
max_file_size = 10 * 1024 * 1024 

def is_allowed_image(filename: str, content_type: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in allowed_image_extensions and content_type in allowed_image_types

def get_embedding(text: str) -> list[float]:
    if not text or not embedding_model:
        return []
    emb = embedding_model.encode(text, normalize_embeddings=True)
    return emb.tolist()

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def find_similar_in_db(query_emb: list[float], subject: str, conn: sqlite3.Connection, threshold=0.85) -> dict | None:  # 定义函数：查询数据库中相似的题目
    cursor = conn.cursor()  # 获取数据库游标
    cursor.execute("SELECT question_text, similar_question, similar_answer, embedding_json FROM questions WHERE subject=?", (subject,))  # SQL查询：根据科目查找题目
    rows = cursor.fetchall()  # 获取所有匹配的行
    
    best_score = 0.0  # 初始化最高相似度分数
    best_match = None  # 初始化最佳匹配结果
    
    for row in rows:  # 遍历每一道题目
        q_text, sim_q, sim_a, emb_json = row  # 解包行数据
        if not emb_json:  # 如果没有嵌入向量，跳过
            continue
        try:  # 尝试执行
            db_emb = json.loads(emb_json)  # 解析JSON字符串
            score = cosine_similarity(query_emb, db_emb)  # 计算余弦相似度
            if score > best_score:  # 如果分数更高
                best_score = score  # 更新最高分数
                best_match = {  # 记录最佳匹配
                    "question_text": q_text,
                    "similar_question": sim_q,
                    "similar_answer": sim_a,
                    "score": score
                }
        except:  # 如果发生异常
            continue  # 跳过这道题
            
    if best_score >= threshold:  # 如果最高分数 >= 阈值
        print(f"命中题库！相似度: {best_score:.4f}")  # 打印日志
        return best_match  # 返回匹配结果
    return None  # 没有找到匹配的题目


async def analyze_wrong_question_task(task_id: str, files_content: list, config: dict):
    conn = sqlite3.connect('users.db')
    try:
        tasks[task_id]['status'] = TaskStatus.PROCESSING
        client = zai.ZhipuAiClient(api_key=os.getenv('ZHIPU_API_KEY'))
        content_list = []
        for content in files_content:
            image_data = base64.b64encode(content).decode("utf-8")
            content_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
            })
        
        extraction_prompt = """请分析这张错题图片。
请以JSON格式输出：
1. original_question: 图片中题目的原文内容（尽量准确提取，用于检索）
2. subject: 图片中的题目的科目（如数学，英语）
3. grade: 图片中的题目的等级（如高中，初中）
3. wrong_reason: 学生犯错的原因（简洁）
4. suggestion: 针对性学习建议（简洁）
只输出JSON。"""

        content_list.append({"type": "text", "text": extraction_prompt})

        response = client.chat.completions.create(
            model=config['zhipu_ai']['v_model'],
            messages=[{"role": "user", "content": content_list}],
            response_format={"type": "json_object"}
        )
        
        analysis_result = json.loads(response.choices[0].message.content)
        original_question = analysis_result.get("original_question", "")
        wrong_reason = analysis_result.get("wrong_reason", "")
        suggestion = analysis_result.get("suggestion", "")
        subject = analysis_result.get("subject", "")
        grade = analysis_result.get("grade", "")

        task_result = {}
        
        if original_question and embedding_model:
            query_emb = get_embedding(original_question)
            match = find_similar_in_db(query_emb, subject, conn) 
            
            if match:
                task_result = {
                    "wrong_reason": wrong_reason,
                    "suggestion": suggestion,
                    "likely_question": match['similar_question'],
                    "likely_question_answer": match['similar_answer'],
                    "source": "DB"
                }
        
        if not task_result:
            print("题库未命中，调用AI生成新题...")
            gen_prompt = f"""基于以下题目，生成一道考察相同知识点但数值或情境不同的新题目。
原题目：{original_question}

请以JSON格式输出：
1. likely_question: 生成的新题目
2. likely_question_answer: 新题目的解答
只输出JSON。"""

            gen_content_list = content_list[:-1] 
            gen_content_list.append({"type": "text", "text": gen_prompt})
            
            gen_response = client.chat.completions.create(
                model=config['zhipu_ai']['model'],
                messages=[{"role": "user", "content": gen_content_list}],
                response_format={"type": "json_object"}
            )
            
            gen_result = json.loads(gen_response.choices[0].message.content)
            
            new_question = gen_result.get("likely_question")
            new_answer = gen_result.get("likely_question_answer")
            
            if new_question and query_emb:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO questions (subject, grade, question_text, similar_question, similar_answer, embedding_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (subject, grade, original_question, new_question, new_answer, json.dumps(query_emb)))
                conn.commit()
                print("新题目已存入题库！")

            task_result = {
                "wrong_reason": wrong_reason,
                "suggestion": suggestion,
                "likely_question": new_question,
                "likely_question_answer": new_answer,
                "source": "AI" 
            }

        tasks[task_id]['status'] = TaskStatus.SUCCESS
        tasks[task_id]['result'] = task_result
        
    except Exception as e:
        tasks[task_id]['status'] = TaskStatus.FAILED
        tasks[task_id]['error'] = str(e)
        print(f"任务执行失败: {e}")
    finally:
        conn.close()

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    global embedding_model
    config_init()
    sqlite_init()
    load_dotenv()
    config = read_config()
    ml_models["yolo"] = YOLO(config['yolo_model']['path'])
    print("YOLO模型加载完成")
    embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("向量模型加载完成")
    yield
    ml_models.clear()

app = fastapi.FastAPI(lifespan=lifespan)
users = fastapi.APIRouter(prefix="/users")
ai = fastapi.APIRouter(prefix="/ai")
tools = fastapi.APIRouter(prefix="/tools")

@users.post("/register")
def register_user(request: RegisterRequest, conn: sqlite3.Connection = fastapi.Depends(get_db)):
    cursor = conn.cursor()
    try:
        token = generate_token()
        hashed_password = hash_password(request.password)
        cursor.execute("INSERT INTO users (username, password, token) VALUES (?, ?, ?)", 
                       (request.username, hashed_password, token))
        conn.commit()
        return {"message": "register success", "token": token}
    except sqlite3.IntegrityError:
        return {"error": "Username already exists"}

@users.post("/login")
def user_login(request: LoginRequest, conn: sqlite3.Connection = fastapi.Depends(get_db)):
    cursor = conn.cursor()
    hashed_password = hash_password(request.password)
    cursor.execute("SELECT token FROM users WHERE username=? AND password=?", 
                   (request.username, hashed_password))
    user = cursor.fetchone()
    if user:
        return {"message": "login success", "token": user[0]}
    else:
        return {"error": "Invalid username or password"}

@ai.post("/chat/simple")
def chat(token: str = fastapi.Header(...), request: ChatRequest = fastapi.Body(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    try:
        client = zai.ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY")) 
        response = client.chat.completions.create(
            model=read_config()['zhipu_ai']['model'],
            messages=[
                {"role": "user", "content": "作为一名专业的教育家，你需要科学、合理地解答学生提出的问题，并提出相应的建议。尽量简短。"},
                {"role": "assistant", "content": "当然，请告诉我一些您在学习上的疑惑"},
                {"role": "user", "content": request.message}
            ],
            thinking={
                "type": "disabled",    
            },
            max_tokens=65536,         
            temperature=1.0           
        )
        return {"message": response.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

@ai.post("/analysis/exam_detection")
async def upload_file(token: str = fastapi.Header(...), files: list[fastapi.UploadFile] = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not token or not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    results_list = []
    for file in files:
        if not is_allowed_image(file.filename, file.content_type):
            continue
        
        content = await file.read()
        if len(content) > max_file_size:
            continue
        
        ext = Path(file.filename).suffix.lower()
        file_path = os.path.join(read_config()['upload_file_path']['path'], str(time.time()) + "_" + token + ext)
        with open(file_path, "wb") as f:
            f.write(content)
        
        model = ml_models["yolo"]
        results = model(file_path)
        
        bboxes = []
        for result in results:
            for box in result.boxes.xyxy.cpu().numpy():
                bboxes.append(box.tolist())
        
        results_list.append({
            "filename": file.filename,
            "bboxes": bboxes
        })
    
    return {"results": results_list}

@ai.post("/analysis/exam_overview")
async def analysis_exam_paper_overview(token: str = fastapi.Header(...), files: list[fastapi.UploadFile] = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    client = zai.ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY"))

    content_list = []
    for file in files:
        if not is_allowed_image(file.filename, file.content_type):
            continue
        
        ext = Path(file.filename).suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp"
        }.get(ext, "image/jpeg")
        
        content = await file.read()
        img_base = base64.b64encode(content).decode("utf-8")
        
        content_list.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{img_base}"
            }
        })
    
    content_list.append({
        "type": "text",
        "text": """请分析这些试卷图片，识别并提取以下信息：

请以JSON格式输出，包含以下字段：
- subject: 试卷科目（如：语文、数学、英语、物理、化学、生物、历史、地理、政治等）
- difficulty: 试卷难度（简单、中等、困难）
- grade: 适用年级（如：小学一年级、初中二年级、高中三年级等）
- num: 上传的试卷页数（如：1、2、3等）

只输出JSON，不要添加任何其他文字。"""
    })

    try:
        response = client.chat.completions.create(
            model=read_config()['zhipu_ai']['v_model'],
            messages=[
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        return json.loads(result)
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return {"error": "AI返回格式错误", "raw_content": result if 'result' in dir() else None}
    except Exception as e:
        print(f"分析失败: {e}")
        return {"error": str(e)}

@ai.post("/analysis/exam_wrongs/submit")
async def submit_wrong_question(token: str = fastapi.Header(...), background_tasks: fastapi.BackgroundTasks = fastapi.BackgroundTasks(), files: list[fastapi.UploadFile] = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    task_id = str(uuid.uuid4())
    files_content = []
    for file in files:
        content = await file.read()
        files_content.append(content)
    config = read_config()
    tasks[task_id] = {
        'status': TaskStatus.PENDING,
        'result': None,
        'error': None
    }
    background_tasks.add_task(analyze_wrong_question_task, task_id, files_content, config)
    
    return {
        "message": "任务已提交，正在后台处理",
        "task_id": task_id,
        "status": TaskStatus.PENDING.value
    }

@ai.get("/analysis/exam_wrongs/result/{task_id}")
async def get_analysis_result(token: str = fastapi.Header(...), task_id: str = fastapi.Path(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")

    if task_id not in tasks:
        raise fastapi.HTTPException(status_code=404, detail="任务不存在或已过期")
    task = tasks[task_id]
    response = {
        "task_id": task_id,
        "status": task['status'].value,
        "result": task.get('result'),
        "error": task.get('error')
    } 
    return response

@tools.post("/upload/exam_marks")
async def upload_exam_marks(token: str = fastapi.Header(...), request: ExamMarksRequest = fastapi.Body(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exam_marks (username, exam_names, subject, difficulty, grade, marks) VALUES (?, ?, ?, ?, ?, ?)",
                   (request.username, request.exam_names, request.subject, request.difficulty, request.grade, request.marks))
    conn.commit()
    return {"message": "考试成绩上传成功"}

@tools.get("/search/exam_marks")
async def search_exam_marks(token: str = fastapi.Header(...), username: str = fastapi.Query(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    cursor = conn.cursor()
    cursor.execute("SELECT exam_names, subject, difficulty, grade, marks FROM exam_marks WHERE username = ?", (username,))
    rows = cursor.fetchall()
    return {"exam_marks": rows}

@tools.post("/upload/wrong_questions")
async def upload_wrong_questions(token: str = fastapi.Header(...), username: str = fastapi.Form(...), wrong_reason: str = fastapi.Form(...), grade: str = fastapi.Form(...), source: str = fastapi.Form(...), difficulty: str = fastapi.Form(...), subject: str = fastapi.Form(...), files: list[fastapi.UploadFile] = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    cursor = conn.cursor()
    for file in files:
        content = await file.read()
        content_base64 = base64.b64encode(content).decode("utf-8")
        cursor.execute(
            "INSERT INTO wrong_questions (username, wrong_reason, grade, source, difficulty, subject, file_name, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, wrong_reason, grade, source, difficulty, subject, file.filename, content_base64)
        )
    conn.commit()
    return {"message": "错题上传成功"}

@tools.get("/search/wrong_questions")
async def search_wrong_questions(token: str = fastapi.Header(...), username: str = fastapi.Query(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, wrong_reason, grade, source, difficulty, subject, content FROM wrong_questions WHERE username = ?", (username,))
    rows = cursor.fetchall()
    return {"wrong_questions": rows}

@tools.get("/review/wrong_questions/today")
async def get_today_review_questions(token: str = fastapi.Header(...), username: str = fastapi.Query(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, wrong_reason, grade, source, difficulty, subject, file_name, content, 
               review_count, ease_factor, interval_days, next_review_date
        FROM wrong_questions 
        WHERE username = ? AND (next_review_date IS NULL OR next_review_date <= ?)
    """, (username, today))
    rows = cursor.fetchall()
    
    review_list = []
    for row in rows:
        review_list.append({
            "id": row[0],
            "wrong_reason": row[1],
            "grade": row[2],
            "source": row[3],
            "difficulty": row[4],
            "subject": row[5],
            "file_name": row[6],
            "content": row[7],
            "review_count": row[8],
            "ease_factor": row[9],
            "interval_days": row[10],
            "next_review_date": row[11]
        })
    
    return {"today_review": review_list, "count": len(review_list)}

@tools.post("/review/wrong_questions/{question_id}")
async def review_wrong_question(question_id: int, token: str = fastapi.Header(...), quality: int = fastapi.Form(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    if quality < 0 or quality > 5:
        raise fastapi.HTTPException(status_code=400, detail="quality must be between 0 and 5")
    
    today = datetime.now().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT review_count, ease_factor, interval_days, next_review_date 
        FROM wrong_questions WHERE id = ?
    """, (question_id,))
    row = cursor.fetchone()
    
    if not row:
        raise fastapi.HTTPException(status_code=404, detail="错题不存在")
    
    if row[3] and row[3] > today:
        raise fastapi.HTTPException(status_code=400, detail="今日已复习，请明天再来")
    
    review_count, ease_factor, interval_days, _, _ = row
    
    next_date, new_review_count, new_ease_factor, new_interval_days = calculate_ebbinghaus(review_count, ease_factor, interval_days, quality)
    
    cursor.execute("""
        UPDATE wrong_questions 
        SET review_count = ?, ease_factor = ?, interval_days = ?, next_review_date = ?
        WHERE id = ?
    """, (new_review_count, new_ease_factor, new_interval_days, next_date, question_id))
    conn.commit()
    
    return {
        "message": "复习完成",
        "next_review_date": next_date,
        "interval_days": new_interval_days,
        "review_count": new_review_count
    }

app.include_router(tools)
app.include_router(users)
app.include_router(ai)
swagger_js_url = "/static/swagger-ui/swagger-ui-bundle.js"
swagger_css_url = "/static/swagger-ui/swagger-ui.css"

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app='backend:app', host='127.0.0.1', port=8100, reload=True)

