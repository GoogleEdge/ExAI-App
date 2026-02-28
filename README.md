# ExAI-App 易析AI

一个也许对你有用的开源考试分析应用

## 功能特性

### 用户模块 (/users)
- `POST /users/register` - 用户注册
- `POST /users/login` - 用户登录

### AI 分析模块 (/ai)
- `POST /ai/chat/simple` - 智能问答
- `POST /ai/analysis/exam_detection` - 试卷题目检测 (YOLO)
- `POST /ai/analysis/exam_overview` - 试卷概览分析
- `POST /ai/analysis/exam_wrongs/submit` - 错题分析提交
- `GET /ai/analysis/exam_wrongs/result/{task_id}` - 获取错题分析结果

### 工具模块 (/tools)
- `POST /tools/upload/exam_marks` - 上传考试成绩
- `GET /tools/search/exam_marks` - 查询考试成绩
- `POST /tools/upload/wrong_questions` - 上传错题
- `GET /tools/search/wrong_questions` - 查询错题

## 技术栈

- **后端框架**: FastAPI
- **数据库**: SQLite
- **AI 模型**: 智谱 AI (ZhipuAI)
- **目标检测**: YOLO (Ultralytics)
- **向量化**: Sentence Transformers

## 环境要求

- Python 3.9+
- CUDA (可选，用于 YOLO 加速)

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd ExAI-App
```

### 2. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `.env` 文件：

```env
ZHIPU_API_KEY=your_api_key_here
```

或在 `config.yaml` 中配置：

```yaml
zhipu_ai:
  model: glm-4.7-flash
  v_model: glm-4.6v-flash
  api_key: your_api_key_here
```

### 5. 配置文件说明

`config.yaml` 配置文件说明：

```yaml
# 上传文件存储路径
upload_file_path:
  path: uploaded_files

# 数据库路径
users_db:
  path: users.db

# YOLO 模型路径
yolo_model:
  path: yolo_model.pt

# 智谱 AI 配置
zhipu_ai:
  model: glm-4.7-flash      # 文本模型
  v_model: glm-4.6v-flash   # 视觉模型
  api_key: your_api_key     # API 密钥
```

### 6. 启动服务

```bash
python backend.py
```

服务将在 `http://127.0.0.1:8100` 启动。

API 文档: `http://127.0.0.1:8100/docs`

## 目录结构

```
ExAI-App/
├── backend.py           # 后端主程序
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
├── .env                 # 环境变量 (需创建)
├── yolo_model.pt        # YOLO 模型文件
├── uploaded_files/      # 上传文件存储目录 (自动创建)
└── users.db             # SQLite 数据库 (自动创建)
```

## API 调用示例

### 用户注册
```bash
curl -X POST http://127.0.0.1:8100/users/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "123456"}'
```

### 用户登录
```bash
curl -X POST http://127.0.0.1:8100/users/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "123456"}'
```

### 智能问答
```bash
curl -X POST http://127.0.0.1:8100/ai/chat/simple \
  -H "Content-Type: application/json" \
  -H "token: your_token" \
  -d '{"message": "如何提高数学成绩？"}'
```

### 上传错题 (FormData)
```javascript
const formData = new FormData();
formData.append('subject', '数学');
formData.append('difficulty', '中等');
formData.append('grade', '高三');
formData.append('files', fileInput.files[0]);

fetch('/tools/upload/wrong_questions', {
  method: 'POST',
  headers: { 'token': 'your_token' },
  body: formData
});
```

## 生产环境部署

### 使用 uvicorn

```bash
uvicorn backend:app --host 0.0.0.0 --port 8100 --workers 4
```

### 使用 Gunicorn + Uvicorn Workers

```bash
pip install gunicorn
gunicorn backend:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 使用 Docker

创建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8100

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8100"]
```

构建运行:
```bash
docker build -t exai-app .
docker run -d -p 8100:8100 --name exai-app exai-app
```

## 注意事项

1. 首次启动会自动创建数据库和配置
2. `yolo_model.pt` 需要自行下载 YOLO 模型文件
3. 智谱 AI API Key 需要在官网申请: https://open.bigmodel.cn/
4. 生产环境建议使用反向代理 (Nginx) + HTTPS

## 许可证

MIT License
