# 前端开发任务说明

## 项目概述

这是一个智能教育助手应用，用户可以通过 AI 聊天获取学习建议，也可以上传试卷图片进行分析。

## 后端 API 基础信息

- **服务器地址**: `http://127.0.0.1:8100`
- **所有请求都需要在 HTTP Header 中携带 token 进行身份验证**
- **Token 获取方式**: 用户登录成功后，后端返回 token，前端需要保存并在后续请求中使用

---

## 功能一：用户注册和登录

### 1.1 用户注册

**接口**: `POST /users/register`

**请求参数** (JSON Body):
```json
{
  "username": "用户名",
  "password": "密码"
}
```

**响应**:
- 成功: `{"message": "register success", "token": "32位数字token"}`
- 失败: `{"error": "Username already exists"}`

**前端任务**:
- 创建注册表单，包含用户名和密码输入框
- 发送注册请求
- 保存返回的 token

---

### 1.2 用户登录

**接口**: `POST /users/login`

**请求参数** (JSON Body):
```json
{
  "username": "用户名",
  "password": "密码"
}
```

**响应**:
- 成功: `{"message": "login success", "token": "32位数字token"}`
- 失败: `{"error": "Invalid username or password"}`

**前端任务**:
- 创建登录表单
- 发送登录请求
- 保存返回的 token
- 登录成功后跳转到主界面

---

## 功能二：AI 聊天助手

### 2.1 发送消息

**接口**: `POST /ai/chat/simple`

**请求参数** (JSON Body):
```json
{
  "message": "用户的问题",
  "token": "用户的token"
}
```

**响应**:
```json
{
  "message": "AI的回复内容"
}
```

**前端任务**:
- 创建聊天界面，包含消息输入框和发送按钮
- 发送消息时携带 token
- 显示聊天记录（用户消息和 AI 回复）

---

## 功能三：试卷分析（核心功能）

### 3.1 试卷概况分析

**接口**: `POST /ai/analysis/overview`

**请求方式**: `multipart/form-data`

**请求参数**:
- **Header**: `token: 用户的token`
- **Files**: `files` (多张试卷图片)

**响应**:
```json
{
  "subject": "数学",
  "difficulty": "中等",
  "grade": "初中二年级"
}
```

**前端任务**:
- 提供图片选择功能（支持多选）
- 上传试卷图片
- 显示分析结果（科目、难度、年级）

---

### 3.2 题目分割检测

**接口**: `POST /ai/analysis/detection`

**请求方式**: `multipart/form-data`

**请求参数**:
- **Header**: `token: 用户的token`
- **Files**: `files` (试卷图片)

**响应**:
```json
{
  "results": [
    {
      "filename": "image1.jpg",
      "bboxes": [
        [x1, y1, x2, y2],
        [x1, y1, x2, y2]
      ]
    }
  ]
}
```

**bbox 说明**: `[x1, y1, x2, y2]` 表示题目框的左上角和右下角坐标

**前端任务**:
- 上传试卷图片
- 在图片上绘制检测到的题目框
- 让用户点击选择错题的框

---

### 3.3 错题分析

**接口**: `POST /ai/analysis/wrong_questions`

**请求方式**: `multipart/form-data`

**请求参数**:
- **Header**: `token: 用户的token`
- **Files**: `files` (裁剪后的错题图片，可以多张)

**响应**:
```json
{
  "wrong_reason": "学生犯错的原因分析",
  "suggestion": "针对性的学习建议",
  "likely_question": "生成的相似题目",
  "likely_question_answer": "生成的相似题目的解答"
}
```

**前端任务**:
- 根据用户选择的 bbox，从原图中裁剪出错题图片
- 将裁剪后的图片上传到后端
- 显示分析结果（错误原因、学习建议、相似题目及解答）

---

## 完整流程示例（试卷分析）

```
1. 用户登录 → 获取 token
   ↓
2. 用户选择试卷图片 → 调用 /analysis/overview
   ↓
3. 显示试卷概况（科目、难度、年级）
   ↓
4. 用户确认开始分析 → 调用 /analysis/detection
   ↓
5. 在图片上绘制题目框，让用户选择错题
   ↓
6. 根据选择的框裁剪图片 → 调用 /analysis/wrong_questions
   ↓
7. 显示错题分析结果
```

---

## 技术要点

### Token 管理
- 登录/注册成功后保存 token
- 所有 API 请求都需要在 Header 中携带 token
- Token 过期或无效时，返回 401 状态码

### 图片处理
- 支持的图片格式: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`
- 单张图片最大 10MB

### 错误处理
- 401 Unauthorized: Token 无效或过期
- 422 Unprocessable Entity: 请求参数格式错误
- 其他错误: 响应中包含 `{"error": "错误信息"}`

---

## 开发建议

1. **先实现登录注册功能**，确保 token 能正确获取和保存
2. **再实现 AI 聊天功能**，验证 token 传递是否正确
3. **最后实现试卷分析功能**，按顺序实现三个接口
4. **图片裁剪功能**：使用前端图片处理库（如 Canvas API）根据 bbox 坐标裁剪图片
5. **用户体验优化**：添加加载状态、错误提示、进度显示等
