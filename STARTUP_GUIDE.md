# VidGo 项目启动指南

本文档基于 Windows 环境，详细说明了 VidGo 项目的完整启动流程。项目由 Django 后端、Vue 前端和 Electron 桌面端组成。

## 1. 环境要求

确保您的系统已安装以下软件：

*   **Node.js**: (推荐 v16 或更高版本)
*   **Python**: (推荐 3.10 或更高版本)
*   **Git Bash** 或 **PowerShell**

## 2. 后端启动 (Django)

后端服务负责处理业务逻辑、数据库交互和 AI 模型调用。

### 步骤 2.1: 进入后端目录

```bash
cd backend
```

### 步骤 2.2: 创建并激活虚拟环境

如果尚未创建虚拟环境：

```bash
python -m venv venv
```

激活虚拟环境：

*   **PowerShell**:
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
*   **CMD**:
    ```cmd
    .\venv\Scripts\activate.bat
    ```

### 步骤 2.3: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 2.4: 数据库迁移

初始化数据库表结构：

```bash
python manage.py makemigrations
python manage.py migrate
```

### 步骤 2.5: 启动后端服务

默认运行在 `9000` 端口：

```bash
python manage.py runserver 0.0.0.0:9000
```

看到类似 `Watching for file changes with StatReloader` 的输出即表示启动成功。

---

## 3. 前端启动 (Vue + Electron)

前端分为 Vue 开发服务器和 Electron 主进程。需要同时运行多个命令或使用多个终端窗口。

### 步骤 3.1: 进入前端目录

```bash
cd frontend
```

### 步骤 3.2: 安装依赖

```bash
npm install
```

### 步骤 3.3: 启动开发环境

你需要**同时**运行以下命令（建议在不同的终端窗口中运行）：

#### 窗口 1: 启动 Vue 开发服务器
此命令启动 Vite 开发服务器，通常运行在 `http://localhost:8080`。

```bash
npm run dev
```

#### 窗口 2: 编译 Electron 主进程
此命令监控并编译 Electron 的主进程文件 (`electron/main.ts`)。

```bash
npm run electron:build-main
```

#### 窗口 3: 启动 Electron 应用
此命令启动 Electron 窗口并加载 Vue 页面。

```bash
npx electron dist-electron/main.js
```

> **注意**: 如果遇到 Electron 启动白屏或连接错误，请确保 "窗口 1 (npm run dev)" 已经完全启动并显示了 Local URL。

---

## 4. 快速启动脚本 (可选)

为了方便，你可以创建一个 PowerShell 脚本一次性启动所有服务。

在项目根目录创建 `start_all.ps1`:

```powershell
# 启动后端
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; python manage.py runserver 0.0.0.0:9000"

# 等待几秒确保后端初始化
Start-Sleep -Seconds 3

# 启动前端开发服务器
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

# 启动 Electron 编译
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run electron:build-main"

# 启动 Electron 窗口
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; Start-Sleep -Seconds 5; npx electron dist-electron/main.js"
```

## 5. 常见问题排查

### Q1: 后端提示 "未找到字幕文件" 或 "400 Bad Request"
*   **原因**: 视频对应的 .srt 字幕文件不存在，或者文件名与视频 ID/URL 不匹配。
*   **解决**: 确保字幕文件位于 `backend/media/saved_srt/` 目录下，且命名格式正确（如 `1_zh.srt` 或 `[VideoURL].srt`）。

### Q2: 笔记生成失败，提示 API Key 未配置
*   **原因**: 未在系统设置中配置大模型 API Key。
*   **解决**: 在应用首页点击“设置”，在 LLM 配置中填入正确的 API Key 和 Base URL。

### Q3: Electron 启动报错 "Unable to load ..."
*   **原因**: 前端开发服务器 (`npm run dev`) 还没启动完成。
*   **解决**: 等待 `npm run dev` 显示 "Local: http://localhost:8080" 后再运行 Electron 启动命令。

### Q4: 端口占用
*   **解决**: 
    *   后端默认使用 9000，如果被占用，修改启动命令 `python manage.py runserver 0.0.0.0:9001`。
    *   前端默认使用 8080，Vite 会自动尝试下一个可用端口（如 8081），此时需要同步修改 Electron 的加载地址。

## 6. 目录结构说明

*   `backend/`: Django 后端代码
    *   `media/`: 存储视频、音频、字幕、截图和生成的笔记图片
    *   `video/`: 核心业务逻辑 App
    *   `config/`: 配置文件 (config.ini)
*   `frontend/`: Vue 前端代码
    *   `src/`: 页面与组件源码
    *   `electron/`: Electron 主进程源码
