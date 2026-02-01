import fastapi
import zai
import sqlite3
import uvicorn
import random
import hashlib
import yaml
import os
import time
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
    conn.close()
    print("用户表创建成功！")

def config_init():
    config = {
        'users_db': {
            'path': 'users.db'
        },
        'zhipu_ai': {
            'model': 'glm-4.7-flash',
            'api_key': 'sk-1234567890abcdef1234567890abcdef'
        },
        'upload_file_path': {
            'path': 'uploaded_files'
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
    cursor.execute("SELECT id FROM users WHERE token=?", (token,))
    return cursor.fetchone() is not None

app = fastapi.FastAPI()
users = fastapi.APIRouter(prefix="/users")
ai = fastapi.APIRouter(prefix="/ai")

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
def chat(request: ChatRequest, conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(request.token, conn):
        return {"error": "Invalid token"}
    
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

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def is_allowed_image(filename: str, content_type: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS and content_type in ALLOWED_IMAGE_TYPES

@ai.post("/analysis/upload")
async def upload_file(token: str, file: fastapi.UploadFile = fastapi.File(...), conn: sqlite3.Connection = fastapi.Depends(get_db)):
    if not verify_token(token, conn):
        return {"error": "Invalid token"}
    
    if not is_allowed_image(file.filename, file.content_type):
        return {"error": f"只支持图片格式: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"}
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return {"error": f"文件大小超过限制 (最大 {MAX_FILE_SIZE // (1024*1024)}MB)"}
    
    file_path = os.path.join(read_config()['upload_file_path']['path'], str(time.time()) + "_" + token)
    with open(file_path, "wb") as f:
        f.write(content)
    
    return {"filename": file.filename, "content_type": file.content_type, "size": len(content)}

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

