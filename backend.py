import fastapi
import zai
import sqlite3
import uvicorn
import random

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

app = fastapi.FastAPI()
users = fastapi.APIRouter(prefix="/users")
ai = fastapi.APIRouter(prefix="/ai")

@users.post("/register")
def register_user(username: str, password: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        token = ''.join(str(random.randint(0, 9)) for _ in range(32))
        cursor.execute("INSERT INTO users (username, password, token) VALUES (?, ?, ?)", (username, password, token))
        conn.commit()
        return {"message": "register success", "token": token}
    except sqlite3.IntegrityError:
        return {"error": "Username already exists"}
    finally:
        conn.close()

@users.post("/login")
def user_login(username: str, password: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT token FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            return {"message": "login success", "token": user[0]}
        else:
            return {"error": "Invalid username or password"}
    finally:
        conn.close()

@ai.post("/chat")
def chat(message: str, token: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE token=?", (token,))
        user = cursor.fetchone()
        if user:
            pass
        else:
            return {"error": "Invalid token"}
    finally:
        conn.close()

app.include_router(users)

if __name__ == "__main__":
    sqlite_init()
    uvicorn.run(app='backend:app', host='127.0.0.1', port=8100, reload=True)

