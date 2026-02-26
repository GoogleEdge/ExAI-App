import fastapi
import zai
import sqlite3
import uvicorn
import random
import hashlib
import yaml
import os
import time
import base64
import json
from ultralytics import YOLO
from pathlib import Path
from pydantic import BaseModel

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    token: str

class ExamMarksRequest(BaseModel):
    username: str
    exam_names: str
    subject: str
    difficulty: str
    grade: str
    marks: int

def get_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return ''.join(str(random.randint(0, 9)) for _ in range(32))

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
    print("用户表创建成功！")
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
    print("考试成绩表创建成功！")
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
            content TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("错题表创建成功！")

def config_init():
    config = {
        'users_db': {
            'path': 'users.db'
        },
        'zhipu_ai': {
            'model': 'glm-4.7-flash',
            'v_model': 'glm-4.6v-flash',
            'api_key': 'sk-1234567890abcdef1234567890abcdef'
        },
        'upload_file_path': {
            'path': 'uploaded_files'
        },
        'yolo_model_path': {
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
    
allowed_image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
allowed_image_types = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}
max_file_size = 10 * 1024 * 1024 

def is_allowed_image(filename: str, content_type: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in allowed_image_extensions and content_type in allowed_image_types

app = fastapi.FastAPI()
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
        client = zai.ZhipuAiClient(api_key=read_config()['zhipu_ai']['api_key']) 
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

@ai.post("/analysis/detection")
async def upload_file(token: str = fastapi.Header(...), files: list[fastapi.UploadFile] = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not token or not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="Invalid token")
    
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
        
        model = YOLO(read_config()['yolo_model']['path'])
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

@ai.post("/analysis/overview")
async def analysis_exam_paper_overview(token: str = fastapi.Header(...), files: list[fastapi.UploadFile] = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="Invalid token")
    
    client = zai.ZhipuAiClient(api_key=read_config()['zhipu_ai']['api_key'])

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

@ai.post("/analysis/wrong_questions")
async def analysis_wrong_question(token: str = fastapi.Header(...), files: list[fastapi.UploadFile] = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="Invalid token")
    
    client = zai.ZhipuAiClient(api_key=read_config()['zhipu_ai']['api_key'])
    
    content_list = []
    for file in files:
        content = await file.read()
        image_data = base64.b64encode(content).decode("utf-8")
        
        ext = Path(file.filename).suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp"
        }.get(ext, "image/jpeg")
        
        content_list.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{image_data}"
            }
        })
    
    content_list.append({
        "type": "text",
        "text": """作为一名专业的教育家，你需要科学、合理地分析为什么学生会犯这种错误，并提出相应的建议。

请以JSON格式输出，包含以下字段：
- wrong_reason: 分析学生犯错的原因，简洁，一般情况下不超过30字
- suggestion: 针对性的学习建议，简洁，一般情况下不超过30字
- likely_question: 一条与之考点一致的题目。
- likely_question_answer: 生成的相似题目的解答

只输出JSON，不要添加任何其他文字。例如犯错原因：对有理数与绝对值的理解不透彻，没有考虑到0的绝对值不是正数。学习建议：重新复习相关内容。"""
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

@tools.post("/upload/examMarks")
async def upload_exam_marks(token: str = fastapi.Header(...), request: ExamMarksRequest = fastapi.Body(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exam_marks (username, exam_names, subject, difficulty, grade, marks) VALUES (?, ?, ?, ?, ?, ?)",
                   (request.username, request.exam_names, request.subject, request.difficulty, request.grade, request.marks))
    conn.commit()
    return {"message": "考试成绩上传成功"}

@tools.get("/search/examMarks")
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
async def search_wrong_questions(
    token: str = fastapi.Header(...),
    username: str = fastapi.Query(...),
    conn: sqlite3.Connection = fastapi.Depends(get_db)
):
    if not verify_token(token, conn):
        raise fastapi.HTTPException(status_code=401, detail="token验证失败")
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, wrong_reason, grade, source, difficulty, subject, content FROM wrong_questions WHERE username = ?", (username,))
    rows = cursor.fetchall()
    return {"wrong_questions": rows}

app.include_router(tools)
app.include_router(users)
app.include_router(ai)
swagger_js_url = "/static/swagger-ui/swagger-ui-bundle.js"
swagger_css_url = "/static/swagger-ui/swagger-ui.css"
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    config_init()
    sqlite_init()
    uvicorn.run(app='backend:app', host='127.0.0.1', port=8100, reload=True)

