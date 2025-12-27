# ExAI 易析AI
![Status](https://img.shields.io/badge/status-Planning-important)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Android-lightgrey)
![Flet](https://img.shields.io/badge/Flet-Python-blue)
> **ExAI (易析)** 是一款基于 Flet + Python 的跨平台智能学习助手。通过 AI 深度分析试卷与答题卡，结合 RAG（检索增强生成）技术，为学生提供精准的薄弱点诊断与个性化学习建议，并集成错题本、TODO 和番茄钟等学习工具，实现从“发现问题”到“解决问题”的闭环。
---
## 📑 目录
- [1. 项目愿景](#1-项目愿景)
- [2. 技术架构](#2-技术架构)
- [3. 核心功能模块](#3-核心功能模块)
- [4. 数据库设计](#4-数据库设计)
- [5. AI 与 RAG 系统设计](#5-ai-与-rag-系统设计)
- [6. 开源协议](#6-开源协议)
---
## 1. 项目愿景
打造一个 **"懂你的私教"**。用户只需拍照上传试卷，ExAI 不仅能批改，还能像老师一样告诉你哪里错了、为什么错、怎么补，并自动安排复习任务。本项目旨在降低个性化学习的门槛，利用 LLM 技术普惠大众。
### 关键目标
- **跨平台**：一套代码，同时运行在 Windows 和 Android 上。
- **智能化**：利用 RAG 技术挂载教材知识库，提供有据可依的学习建议。
- **闭环化**：连接“试卷分析 → 错题归档 → 任务规划 → 专注执行”的全流程。
---
## 2. 技术架构
### 2.1 技术栈选型
| 分类 | 技术选型 | 理由 |
| :--- | :--- | :--- |
| **前端框架** | **Flet** (Python) | 基于 Flutter，高性能，一套代码双端运行，Python 生态丰富。 |
| **后端语言** | **Python 3.10+** | AI 生态最佳选择，方便集成 OCR 和 LLM 库。 |
| **数据库** | **SQLite** (关系) + **ChromaDB** (向量) | SQLite 轻量嵌入式；Chroma 用于本地 RAG 向量检索。 |
| **大模型 (LLM)** | **ChatGLM** | 在线 API（高质量）。 |
| **文档解析** | **PyMuPDF**, **Pillow** | 处理 PDF 转图片及图像预处理。 |
| **状态管理** | **Provider** (Flet 内置) | 管理全局用户状态和页面间通信。 |
---
## 3. 核心功能模块
### 3.1 试卷智能分析
- **上传与识别**：支持拍照或上传图片/PDF，自动进行 OCR 文字提取。
- **AI 诊断**：
  - 判定题目对错，计算分数。
  - 提取错误原因（概念不清、计算失误等）。
  - 映射至具体的知识点。
- **RAG 增强建议**：
  - 根据错误知识点，检索教材中的相关章节。
  - 推荐类似例题。
  - 生成个性化复习计划。
### 3.2 学习追踪仪表盘
- **成绩趋势图**：使用 Plotly 绘制历史考试成绩折线图，直观展示进步/退步。
- **薄弱点雷达图**：可视化展示各科或各知识点的掌握程度。
- **今日概览**：展示今日待办、错题复习数、番茄钟时长。
### 3.3 错题本
- **自动归档**：分析后的错题一键加入错题本。
- **艾宾浩斯复习**：根据遗忘曲线自动计算下次复习日期。
- **多维度筛选**：按科目、掌握程度、日期筛选错题。
### 3.4 学习工具箱
- **TODO (待办事项)**：创建学习任务，支持优先级和截止日期。AI 分析后自动生成针对性 TODO。
- **番茄钟**：专注计时，关联具体 TODO 任务，统计专注时长。
- **联动机制**：在 AI 分析报告页面，提供“加入错题本”、“创建复习任务”、“开始专注”的快捷操作。
---
## 4. 数据库设计
采用 SQLite 作为主数据库，主要包含以下核心表：
| 表名 | 用途 | 关键字段 |
| :--- | :--- | :--- |
| `exams` | 考试记录 | id, subject_id, score, total_score, ocr_result, ai_analysis(JSON) |
| `knowledge_points` | 知识点树 | id, name, parent_id |
| `weak_points` | 薄弱点记录 | exam_id, point_id, confidence (薄弱度) |
| `error_questions` | 错题本 | id, question_text, image_path, review_status, next_review_date |
| `todos` | 待办任务 | id, title, priority, status, due_date |
| `pomodoro_sessions` | 番茄钟记录 | id, todo_id, duration, completed |
---
## 5. AI 与 RAG 系统设计
### 5.1 处理流程
1. **Image Preprocessing**: 灰度化、降噪、二值化。
2. **OCR**: 使用 PaddleOCR 提取文本，保留版面信息。
3. **LLM Analysis**:
   - Prompt Engineering：引导 LLM 识别错题并映射知识点。
   - 输出结构化 JSON：包含错题列表、对应知识点、错误原因。
4. **RAG Retrieval**:
   - 将识别出的薄弱知识点作为 Query。
   - 在 ChromaDB 中检索教材片段和类似错题。
5. **Final Generation**:
   - 结合检索内容，生成包含教材页码参考、具体建议的最终报告。
### 5.2 Prompt 策略
采用 **CoT (Chain of Thought)** 提示词策略，强制模型输出 JSON 格式，确保程序能准确解析并执行“联动操作”（如自动创建 TODO）。
---

### 6. 开源协议
本项目采用 **Apache-2.0** 协议。这允许大家在保留版权声明的前提下自由使用和修改，同时也为我们未来的商业化保留了灵活性。
---
## 📜 License
Copyright 2025 GoogleEdge. Licensed under the Apache License, Version 2.0
