# memorAIze

将你与 AI 大模型（ChatGPT / Gemini）的对话记录导出为**优雅的网页相册**和**可打印的 PDF 小册子**，像封装时间胶囊一样，把珍贵的对话永远保存下来。

> memorAIze = memorize + AI —— 记住与AI的每一段对话，在未来某天重温依然鲜活。

## 功能

- **🖥️ Web 相册**：左侧时间轴 + 右侧对话流，像刷社交媒体一样浏览历史对话
- **📖 LaTeX 小册子**：一键编译为 PDF，按月分章，按时间排列所有问答单元
- **📁 Session 管理**：每个导出文件为一个 session，跨日期的对话按实际日期拆分
- **🏷️ 分类筛选**：按主题分类、按 AI 模型筛选、关键词全文搜索
- **🔍 全文搜索**：实时搜索对话内容
- **🌙 暗色主题**：护眼模式

## 快速开始

### 1. 导出对话数据

在 Edge 浏览器中安装 [AI Exporter](https://microsoftedge.microsoft.com/addons/detail/lmedefdihnoklhacbmbnchokjilglbcd) 插件：

1. 打开 ChatGPT 或 Gemini 等AI的对话页面
2. 点击插件图标，选择导出格式为 **JSON**
3. 将导出的 JSON 文件放入 `chat_data/microsoft_edge_extention/chatGPT/` 或 `chat_data/microsoft_edge_extention/gemini/` 目录

> 支持 ChatGPT 和 Gemini 两种来源，后续可扩展更多平台。

### 2. 安装依赖

本项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 虚拟环境：

```bash
uv venv
```

### 3. 处理数据

```bash
uv run python scripts/process_data.py
```

这会扫描 `chat_data/` 下所有 JSON 文件，统一输出到 `data/conversations.json`。

### 4. 生成网页相册

```bash
uv run python scripts/generate_html.py
```

然后启动 HTTP 服务器，用浏览器打开：

```bash
python -m http.server 8080
# 浏览器访问 http://localhost:8080
```

### 5. 生成 PDF 小册子

```bash
uv run python scripts/generate_book.py
cd book && bash compile.sh
```

输出文件：`book/main.pdf`

> 编译需要 XeLaTeX（TeX Live 或 MacTeX），中文显示需要 Songti SC 字体。

## 项目结构

```
├── scripts/
│   ├── _template.html          # 网页模板
│   ├── process_data.py         # 数据归一化（JSON → 统一格式）
│   ├── generate_html.py        # 生成网页相册
│   └── generate_book.py        # 生成 LaTeX 小册子
├── chat_data/                  # 原始导出数据（放入你的 JSON 文件）
│   └── microsoft_edge_extention/
│       ├── chatGPT/
│       └── gemini/
├── .gitignore
└── README.md
```

> `index.html`、`book/`、`data/` 均由脚本生成，不在仓库中。

## 数据更新

新增或删除对话后，重新运行：

```bash
uv run python scripts/process_data.py   # 重新归一化
uv run python scripts/generate_html.py  # 重新生成网页
uv run python scripts/generate_book.py  # 重新生成 LaTeX
cd book && bash compile.sh              # 重新编译 PDF
```

## 数据来源

对话数据通过 [AI Exporter](https://microsoftedge.microsoft.com/addons/detail/lmedefdihnoklhacbmbnchokjilglbcd) 浏览器插件导出：

- 平台：Microsoft Edge 扩展商店
- 功能：一键将 ChatGPT / Gemini 等 AI 网页对话导出为 JSON / Markdown 格式
- 用法：打开 AI 对话页面 → 点击插件图标 → 选择导出格式

## 许可证

MIT
