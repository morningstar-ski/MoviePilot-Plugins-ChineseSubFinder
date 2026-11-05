# MoviePilot-Plugins-ChineseSubFinder

MoviePilot ChineseSubFinder 字幕下载增强版插件。

## 功能特性
- **入库自动通知**：在影视整理转移完成时，自动调用 ChineseSubFinder 任务接口添加字幕下载任务。
- **中文影视剧多重过滤（核心防护）**：
  - 自动识别原始语言（`zh`, `cn`, `zho`, `yue` 等），对华语片直接放行拦截推送。
  - 识别影视分类（国产剧、华语电影、国漫等）。
  - 识别目标归档目录（如 `/国产剧/`, `/华语电影/` 等）。
  - 杜绝中文影视剧进入 ChineseSubFinder 误下载或触发 LLM 翻译死循环。
- **路径映射**：支持本地路径与 ChineseSubFinder 容器远端路径映射。

## 安装方法
在 MoviePilot 的 `PLUGIN_MARKET` 环境变量中添加本仓库：
`https://github.com/morningstar-ski/MoviePilot-Plugins-ChineseSubFinder`
重启 MoviePilot 并在插件市场中安装或更新即可。
