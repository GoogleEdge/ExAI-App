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

### 复习模块 (/review) - 艾宾浩斯遗忘曲线
- `GET /tools/review/wrong_questions/today` - 获取今日复习任务
- `POST /tools/review/wrong_questions/{question_id}` - 提交复习结果（评分0-5）

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
├── yolo_model.pt        # YOLO 模型文件 (试卷题目检测)
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
formData.append('username', 'testuser');
formData.append('subject', '数学');
formData.append('grade', '高三');
formData.append('wrong_reason', '计算错误');
formData.append('source', '月考试卷');
formData.append('difficulty', '中等');
formData.append('files', fileInput.files[0]);

fetch('/tools/upload/wrong_questions', {
  method: 'POST',
  headers: { 'token': 'your_token' },
  body: formData
});
```

### 获取今日复习任务
```bash
curl -X GET "http://127.0.0.1:8100/tools/review/wrong_questions/today?username=testuser" \
  -H "token: your_token"
```

### 提交复习结果 (评分0-5)
```bash
curl -X POST "http://127.0.0.1:8100/tools/review/wrong_questions/1" \
  -H "token: your_token" \
  -d "username=testuser&quality=4"
```

**quality 说明**：
- 0-2: 忘记，需要重新学习（1天后复习）
- 3: 勉强记住
- 4: 记得较牢
- 5: 完全记住（按艾宾浩斯曲线延长间隔）

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

## YOLO 模型训练指南

如果你需要重新训练 YOLO 模型用于试卷题目检测，按以下步骤操作：

### 1. 安装依赖

```bash
pip install ultralytics labelme
```

### 2. 准备数据集

使用 [labelme](https://github.com/wkentaro/labelme) 标注工具标注试卷图片，生成 JSON 标注文件。

标注完成后，将标注的 JSON 文件转换为 YOLO 格式：

```python
# convert_labelme.py
import json
import os
from pathlib import Path

def convert_labelme_to_yolo(json_file, output_dir, image_width, image_height):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    txt_file = os.path.join(output_dir, Path(json_file).stem + '.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        for shape in data.get('shapes', []):
            label = shape['label']
            points = shape['points']
            
            # 转换为 YOLO 格式 (中心点坐标 + 宽高，归一化)
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            
            x_center = ((x_min + x_max) / 2) / image_width
            y_center = ((y_min + y_max) / 2) / image_height
            width = (x_max - x_min) / image_width
            height = (y_max - y_min) / image_height
            
            f.write(f"{label} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
```

### 3. 创建数据集目录结构

```
dataset/
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

### 4. 创建数据集配置文件

创建 `dataset.yaml`:

```yaml
path: ./dataset
train: images/train
val: images/val

nc: 1  # 类别数量
names: ['question']  # 类别名称
```

### 5. 训练模型

```bash
from ultralytics import YOLO

# 使用预训练模型
model = YOLO('yolov8n.pt')

# 训练
model.train(
    data='dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='exam_detection',
    exist_ok=True
)
```

### 6. 导出模型

训练完成后，导出为 PyTorch 格式：

```bash
# 导出为 .pt 文件
model.export(format='pt')
```

生成的模型文件在 `runs/detect/exam_detection/weights/best.pt`，将其重命名为 `yolo_model.pt` 并放置在项目根目录。

### 7. 类别说明

当前模型检测的类别：
- `question` - 试卷题目区域

如需添加新类别，修改数据集配置中的 `nc` 和 `names`。

## 注意事项

1. 首次启动会自动创建数据库和配置
2. `yolo_model.pt` 已放置在项目根目录（用于试卷题目检测）
3. 智谱 AI API Key 需要在官网申请: https://open.bigmodel.cn/
4. 生产环境建议使用反向代理 (Nginx) + HTTPS

## 许可证

Apache License 2.0
