# Backend API 文档

## 概述

本文档描述了 backend.py 中所有可用的 API 端点。该后端服务使用 FastAPI 框架构建，提供用户管理、AI 对话、试卷分析和错题复习等功能。

## 基础信息

- **Base URL**: `http://127.0.0.1:8100`
- **认证方式**: Token 验证（通过 HTTP Header 传递）

## 通用说明

### 认证

除 `/users/register` 和 `/users/login` 外，所有 API 端点都需要在请求头中传递 `token` 参数：

```
Token: your_token_here
```

### 响应格式

所有 API 响应均为 JSON 格式。

### 错误响应

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | Token 验证失败 |
| 404 | 资源不存在 |

---

## 用户模块 (prefix: /users)

### 1. 用户注册

**端点**: `POST /users/register`

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应示例**:
```json
{
  "message": "register success",
  "token": "uuid-string"
}
```

**错误响应**:
```json
{
  "error": "Username already exists"
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/users/register"
data = {
    "username": "test_user",
    "password": "password123"
}
response = requests.post(url, json=data)
print(response.json())
# 输出: {"message": "register success", "token": "..."}
```

---

### 2. 用户登录

**端点**: `POST /users/login`

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应示例**:
```json
{
  "message": "login success",
  "token": "uuid-string"
}
```

**错误响应**:
```json
{
  "error": "Invalid username or password"
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/users/login"
data = {
    "username": "test_user",
    "password": "password123"
}
response = requests.post(url, json=data)
print(response.json())
# 输出: {"message": "login success", "token": "..."}
```

---

## AI 模块 (prefix: /ai)

### 3. 简单对话

**端点**: `POST /ai/chat/simple`

**请求头**:
```
Token: your_token_here
```

**请求体**:
```json
{
  "message": "string"
}
```

**响应示例**:
```json
{
  "message": "AI 的回复内容"
}
```

**错误响应**:
```json
{
  "error": "错误信息"
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/ai/chat/simple"
headers = {"Token": "your_token_here"}
data = {"message": "请解释一下勾股定理"}
response = requests.post(url, headers=headers, json=data)
print(response.json())
# 输出: {"message": "AI 的回复内容"}
```

---

### 4. 试卷题目检测

**端点**: `POST /ai/analysis/exam_detection`

**请求头**:
```
Token: your_token_here
```

**请求参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| files | File[] | 试卷图片文件（支持 jpg, jpeg, png, gif, bmp, webp） |

**响应示例**:
```json
{
  "results": [
    {
      "filename": "exam1.jpg",
      "bboxes": [[x1, y1, x2, y2], ...]
    }
  ]
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/ai/analysis/exam_detection"
headers = {"Token": "your_token_here"}
files = [
    ("files", ("exam1.jpg", open("exam1.jpg", "rb"), "image/jpeg")),
    ("files", ("exam2.jpg", open("exam2.jpg", "rb"), "image/jpeg"))
]
response = requests.post(url, headers=headers, files=files)
print(response.json())
# 输出: {"results": [{"filename": "exam1.jpg", "bboxes": [...]}, ...]}
```

---

### 5. 试卷概览分析

**端点**: `POST /ai/analysis/exam_overview`

**请求头**:
```
Token: your_token_here
```

**请求参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| files | File[] | 试卷图片文件 |

**响应示例**:
```json
{
  "subject": "数学",
  "difficulty": "中等",
  "grade": "高中一年级",
  "num": 2
}
```

**错误响应**:
```json
{
  "error": "AI返回格式错误",
  "raw_content": "原始返回内容"
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/ai/analysis/exam_overview"
headers = {"Token": "your_token_here"}
files = [
    ("files", ("math_exam.jpg", open("math_exam.jpg", "rb"), "image/jpeg"))
]
response = requests.post(url, headers=headers, files=files)
print(response.json())
# 输出: {"subject": "数学", "difficulty": "中等", "grade": "高中一年级", "num": 1}
```

---

### 6. 错题分析提交

**端点**: `POST /ai/analysis/exam_wrongs/submit`

**说明**: 异步提交错题分析任务，后台处理

**请求头**:
```
Token: your_token_here
```

**请求参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| files | File[] | 错题图片文件 |

**响应示例**:
```json
{
  "message": "任务已提交，正在后台处理",
  "task_id": "uuid-string",
  "status": "pending"
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/ai/analysis/exam_wrongs/submit"
headers = {"Token": "your_token_here"}
files = [
    ("files", ("wrong_question.jpg", open("wrong_question.jpg", "rb"), "image/jpeg"))
]
response = requests.post(url, headers=headers, files=files)
print(response.json())
# 输出: {"message": "任务已提交，正在后台处理", "task_id": "...", "status": "pending"}
task_id = response.json()["task_id"]
```

---

### 7. 错题分析结果查询

**端点**: `GET /ai/analysis/exam_wrongs/result/{task_id}`

**说明**: 查询错题分析任务的结果

**请求头**:
```
Token: your_token_here
```

**路径参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| task_id | string | 任务 ID |

**响应示例**:
```json
{
  "task_id": "uuid-string",
  "status": "success",
  "result": {
    // 分析结果
  },
  "error": null
}
```

**任务状态值**:
- `pending`: 待处理
- `processing`: 处理中
- `success`: 成功
- `failed`: 失败

**Python 代码示例**:
```python
import requests

task_id = "之前获取的task_id"
url = f"http://127.0.0.1:8100/ai/analysis/exam_wrongs/result/{task_id}"
headers = {"Token": "your_token_here"}
response = requests.get(url, headers=headers)
print(response.json())
# 输出: {"task_id": "...", "status": "success", "result": {...}, "error": null}
```

---

## 工具模块 (prefix: /tools)

### 8. 上传考试成绩

**端点**: `POST /tools/upload/exam_marks`

**请求头**:
```
Token: your_token_here
```

**请求体**:
```json
{
  "username": "string",
  "exam_names": "string",
  "subject": "string",
  "difficulty": "string",
  "grade": "string",
  "marks": 100
}
```

**响应示例**:
```json
{
  "message": "考试成绩上传成功"
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/tools/upload/exam_marks"
headers = {"Token": "your_token_here"}
data = {
    "username": "test_user",
    "exam_names": "期末考试",
    "subject": "数学",
    "difficulty": "中等",
    "grade": "高一",
    "marks": 95
}
response = requests.post(url, headers=headers, json=data)
print(response.json())
# 输出: {"message": "考试成绩上传成功"}
```

---

### 9. 查询考试成绩

**端点**: `GET /tools/search/exam_marks`

**请求头**:
```
Token: your_token_here
```

**查询参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| username | string | 用户名 |

**响应示例**:
```json
{
  "exam_marks": [
    ["期末考试", "数学", "中等", "高一", 95],
    ["月考", "物理", "困难", "高二", 88]
  ]
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/tools/search/exam_marks"
headers = {"Token": "your_token_here"}
params = {"username": "test_user"}
response = requests.get(url, headers=headers, params=params)
print(response.json())
# 输出: {"exam_marks": [["期末考试", "数学", "中等", "高一", 95], ...]}
```

---

### 10. 上传错题

**端点**: `POST /tools/upload/wrong_questions`

**请求头**:
```
Token: your_token_here
```

**表单参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| username | string | 用户名 |
| wrong_reason | string | 错题原因 |
| grade | string | 年级 |
| source | string | 来源 |
| difficulty | string | 难度 |
| subject | string | 科目 |
| files | File[] | 错题图片文件 |

**响应示例**:
```json
{
  "message": "错题上传成功"
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/tools/upload/wrong_questions"
headers = {"Token": "your_token_here"}
data = {
    "username": "test_user",
    "wrong_reason": "计算错误",
    "grade": "高一",
    "source": "期末考试",
    "difficulty": "中等",
    "subject": "数学"
}
files = [
    ("files", ("wrong1.jpg", open("wrong1.jpg", "rb"), "image/jpeg"))
]
response = requests.post(url, headers=headers, data=data, files=files)
print(response.json())
# 输出: {"message": "错题上传成功"}
```

---

### 11. 查询错题

**端点**: `GET /tools/search/wrong_questions`

**请求头**:
```
Token: your_token_here
```

**查询参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| username | string | 用户名 |

**响应示例**:
```json
{
  "wrong_questions": [
    {
      "id": 1,
      "wrong_reason": "计算错误",
      "grade": "高一",
      "source": "期末考试",
      "difficulty": "中等",
      "subject": "数学",
      "content": "base64编码的图片内容"
    }
  ]
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/tools/search/wrong_questions"
headers = {"Token": "your_token_here"}
params = {"username": "test_user"}
response = requests.get(url, headers=headers, params=params)
print(response.json())
# 输出: {"wrong_questions": [{...}, ...]}
```

---

### 12. 获取今日复习错题

**端点**: `GET /tools/review/wrong_questions/today`

**说明**: 获取今日需要复习的错题（基于艾宾浩斯遗忘曲线）

**请求头**:
```
Token: your_token_here
```

**查询参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| username | string | 用户名 |

**响应示例**:
```json
{
  "today_review": [
    {
      "id": 1,
      "wrong_reason": "计算错误",
      "grade": "高一",
      "source": "期末考试",
      "difficulty": "中等",
      "subject": "数学",
      "file_name": "wrong1.jpg",
      "content": "base64编码的图片内容",
      "review_count": 3,
      "ease_factor": 2.5,
      "interval_days": 4,
      "next_review_date": "2024-01-15"
    }
  ],
  "count": 1
}
```

**Python 代码示例**:
```python
import requests

url = "http://127.0.0.1:8100/tools/review/wrong_questions/today"
headers = {"Token": "your_token_here"}
params = {"username": "test_user"}
response = requests.get(url, headers=headers, params=params)
print(response.json())
# 输出: {"today_review": [{...}], "count": 1}
```

---

### 13. 提交错题复习结果

**端点**: `POST /tools/review/wrong_questions/{question_id}`

**说明**: 提交错题复习结果，更新艾宾浩斯遗忘曲线参数

**请求头**:
```
Token: your_token_here
```

**路径参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| question_id | int | 错题 ID |

**表单参数**:
| 参数名 | 类型 | 说明 |
|--------|------|------|
| quality | int | 复习质量评分 (0-5) |

**质量评分说明**:
| 分数 | 说明 |
|------|------|
| 0 | 完全不记得 |
| 1 | 印象模糊 |
| 2 | 记住一部分 |
| 3 | 记住大部分 |
| 4 | 几乎记住 |
| 5 | 完全记住 |

**响应示例**:
```json
{
  "message": "复习完成",
  "next_review_date": "2024-01-20",
  "interval_days": 7,
  "review_count": 4
}
```

**错误响应**:
```json
{
  "detail": "今日已复习，请明天再来"
}
```

**Python 代码示例**:
```python
import requests

question_id = 1  # 错题ID
url = f"http://127.0.0.1:8100/tools/review/wrong_questions/{question_id}"
headers = {"Token": "your_token_here"}
data = {"quality": 4}  # 复习质量评分 0-5
response = requests.post(url, headers=headers, data=data)
print(response.json())
# 输出: {"message": "复习完成", "next_review_date": "2024-01-20", "interval_days": 7, "review_count": 4}
```

---

## 数据模型

### RegisterRequest
```json
{
  "username": "string",
  "password": "string"
}
```

### LoginRequest
```json
{
  "username": "string",
  "password": "string"
}
```

### ChatRequest
```json
{
  "message": "string"
}
```

### ExamMarksRequest
```json
{
  "username": "string",
  "exam_names": "string",
  "subject": "string",
  "difficulty": "string",
  "grade": "string",
  "marks": 100
}
```

---

## 附录

### 艾宾浩斯遗忘曲线

错题复习功能基于艾宾浩斯遗忘曲线算法，系统会自动计算下次复习时间：

- **ease_factor**: 难度系数，初始值为 2.5
- **interval_days**: 间隔天数
- **review_count**: 复习次数

每次复习后，系统会根据复习质量调整参数，并计算下次最佳复习时间。
