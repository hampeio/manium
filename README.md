# Manim 教学动画生成器

Windows 桌面软件第一版：Electron 前端 + Python FastAPI 后端 + Manim Community Edition 渲染。用户可上传图片、输入提示词、选择模型配置，软件会生成教学规划、3-5 个分镜、Manim 代码、字幕文件，并自动运行 Manim。代码导致的渲染失败会持续调用模型修复，直至渲染成功；明确的本地环境错误会停止重试。

## 功能范围

- 图像上传、格式检查、项目内保存。
- 图像理解接口预留，第一版使用基础元信息与模型视觉输入。
- GPT / DeepSeek / 本地 Mock 三种路由，不在业务逻辑写死模型。
- `.env` 与界面配置 API Key / Base URL / 模型名称。
- 生成图像理解结果、教学目标、分镜计划、字幕、代码实现计划，再生成 Manim 代码。
- 输出 `.srt`、`timeline_subtitles.json`、旁白 JSON。
- 自动运行 Manim，捕获 stdout / stderr，失败后发送错误日志与代码进行修复。
- Electron 内嵌视频播放器，支持播放、暂停、进度条、重新播放。
- 每次任务独立生成项目文件夹，不覆盖历史项目。

## 环境要求

- Windows 10/11
- Python 3.11 或 3.12
- Node.js 18+
- Manim Community Edition 依赖
- ffmpeg
- LaTeX 发行版，推荐 MiKTeX 或 TeX Live，用于 `MathTex`

检查环境：

```powershell
.\scripts\check_environment.ps1
```

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
Copy-Item .env.example .env
```

桌面启动器会优先安装 `requirements-backend.txt`，用于打开界面和启动本地 API。完整 Manim 渲染环境仍建议安装 `requirements.txt` 并运行 `.\scripts\check_environment.ps1` 检查。

在 `.env` 中填写需要的模型配置。不要把真实 `.env` 提交或发送给别人。

## 运行

桌面软件：

```powershell
.\scripts\start_app.ps1
```

也可以双击桌面快捷方式：

```text
C:\Users\面\Desktop\Manim 教学动画生成器.lnk
```

该快捷方式绑定到 Windows 自带的 `powershell.exe`，执行 `scripts/desktop_launcher.ps1`。如果首次运行发现没有 Node.js / npm，会提示先安装 Node.js 18+。

仅启动后端：

```powershell
.\scripts\start_backend.ps1
```

后端地址默认是 `http://127.0.0.1:8765`。

## 本地 API

- `GET /health`：后端健康检查。
- `POST /generate`：同步生成接口，适合脚本调试。
- `POST /generate_async`：桌面端使用的后台任务接口，立即返回 `task_id`。
- `GET /tasks/{task_id}`：轮询任务状态、阶段日志和最终结果。
- `GET /video?path=...`：播放生成的 mp4。
- `GET /workflow/node-definitions`：高级模式节点库。
- `GET /workflow/templates`：内置工作流模板列表。
- `GET /workflow/templates/{template_id}`：加载内置模板。
- `POST /workflow/validate`：验证端口、DAG、必填输入和 OutputNode。
- `POST /workflow/run_async`：运行整个工作流，当前第一版会验证 DAG 并委托到稳定生成管线。

## 高级模式：节点工作流

顶部可切换 `Quick Generate` 和 `Node Workflow`。

第一版高级模式已经支持：

- 固定节点库：输入、AI、规划、代码、渲染、输出、注释等 14 类节点。
- 类型化端口：Image、Prompt、ModelConfig、StoryboardJSON、ManimCode、VideoFile 等。
- 画布添加、删除、移动节点。
- 点击输出端口再点击输入端口创建连线。
- 右侧 Inspector 查看端口与编辑参数。
- 保存 / 加载 workflow JSON。
- 内置 3 个模板：数学讲解、图片题目讲解、工程力学简支梁。
- 后端 DAG 验证和拓扑排序。
- 运行整个工作流，并保存 `workflow/`、`workflow_outputs/{node_id}/`。

当前阶段说明：现有桌面端仍是无构建 HTML/JS，节点画布实现为 React Flow 兼容数据结构的轻量原型；后续阶段可迁移为 React + React Flow 正式画布。

## 模型配置

第一版支持：

- `mock`：不调用云端模型，用内置样例逻辑生成可测试 Manim 代码。
- `openai`：OpenAI-compatible `/chat/completions`。
- `deepseek`：DeepSeek OpenAI-compatible `/chat/completions`。

API Key 优先级：

1. 界面输入的 API Key；
2. `.env` 中的服务商 API Key；
3. 未提供时自动使用 `mock` 或触发本地保守生成路径。

安全策略：

- 不硬编码 API Key。
- 不把 API Key 写入生成项目文件夹。
- 日志过滤 `.env` 中已知密钥。
- 前端密码框不会展示明文。

## 输出项目结构

每次生成会创建类似：

```text
generated_projects/20260617_120000_ab12cd34/
  inputs/
    uploaded_image.png
    user_prompt.txt
  image_understanding.txt
  image_understanding.json
  teaching_goal.txt
  teaching_plan.json
  storyboard.json
  code_plan.txt
  original_manim_code.py
  scene.py
  subtitles.srt
  timeline_subtitles.json
  narration.json
  logs/
  repairs/
  outputs/
    animation.mp4
  final_summary.json
```

## 内置测试样例

提示词样例在 `samples/sample_prompt.txt`。

运行轻量检查：

```powershell
python -m compileall backend
python -m pytest backend/tests
```

没有安装 `pytest` 时可先执行：

```powershell
pip install pytest
```

## 架构说明

- `backend/ai`：模型配置、模型路由、提示词、结构化 schema。
- `backend/image_nodes`：图像节点接口、格式检查、压缩/转码预留。
- `backend/rendering`：Manim CLI 渲染、日志捕获、视频定位。
- `backend/services`：项目输出、生成编排、字幕、TTS 占位。
- `electron`：桌面窗口、UI、播放器、任务提交。

## 当前风险

- Manim 的 `MathTex` 依赖本机 LaTeX，缺失时会触发自动修复或简化版本。
- 第一版的图像理解依赖所选模型是否支持视觉输入；不支持时仍会基于图像元信息和提示词生成。
- TTS 与复杂 OCR、目标检测、分割、节点式图像处理界面只预留接口，未在第一版实现。

## 快速生成预览

快速生成模式会在生成完成后自动刷新主视频播放器，新生成的视频会替代旧视频。

生成结果区包含：

- `片段预览`：根据 3-5 个分镜生成 `segment_manifest.json`，当前第一步先把每个分镜映射到完整视频，后续会升级为逐段渲染、逐段预览和最终拼接。
- `暂停生成 / 继续生成`：任务在模型生成、代码保存、渲染后整理等检查点响应暂停；正在执行中的 Manim 渲染进程会等当前阶段结束后再暂停。
- `项目文件`：读取当前项目目录内的 `final_summary.json`、`scene.py`、`storyboard.json`、日志、字幕等文本文件，便于直接检查生成产物。

相关本地 API：

- `POST /tasks/{task_id}/pause`
- `POST /tasks/{task_id}/resume`
- `GET /project/files?project_dir=...`
- `GET /project/file?path=...`

## 中文讲解与讯飞语音

当前版本默认要求 AI 输出中文教学目标、中文分镜、中文字幕、中文屏幕文字。Manim 代码中的中文 `Text` 会优先使用 `Microsoft YaHei` 字体，以适配 Windows。

讯飞在线语音合成使用 WebSocket API：`wss://tts-api.xfyun.cn/v2/tts`。如需启用基础发声，请在 `.env` 中填写：

```env
XUNFEI_TTS_ENABLED=true
XUNFEI_APP_ID=
XUNFEI_API_KEY=
XUNFEI_API_SECRET=
XUNFEI_TTS_VOICE=x4_xiaoyan
```

生成完成后，软件会把每个分镜旁白合成为 `audio/scene_XX.mp3`，再合并为 `audio/narration_combined.mp3`。如果本机可用 `ffmpeg`，会输出带配音的 `outputs/animation_with_audio.mp4`，并让预览播放器优先播放该文件。讯飞密钥不会写入生成项目文件夹，也不会写入日志。
