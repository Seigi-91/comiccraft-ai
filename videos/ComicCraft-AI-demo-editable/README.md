# ComicCraft AI 网站与漫画演示

45 秒，1920×1080，30fps；HyperFrames 可编辑 HTML 工程。

## 内容

1. 用《雨夜留灯》成稿开场。
2. 展示真实网站的剧情大纲、分镜脚本和台词页。
3. 展示六个 agent、许可明确的上游来源与项目原创规则；视频主要展示初始创作流程。
4. 连续呈现全部六幅漫画，每格约 3 秒。
5. 回到完整作品与品牌，并明确当前为 ChatGPT 结果回填协作模式。

无配音；背景音乐使用 Kevin MacLeod 的 Dream Culture，许可与完整署名见 MUSIC-CREDITS.txt。音乐被截取、调节音量并淡入淡出。点击音效来自 HyperFrames 自带素材。中文字体为 SIL OFL 授权的 Noto Sans CJK SC，许可在 assets/fonts/OFL.txt。

## 打开和编辑

要求 Node.js 22+。在这个目录执行：

```powershell
npm run dev
```

命令会给出 HyperFrames 编辑预览地址。运行端口和项目地址以命令输出为准。

根文件 index.html 挂载各个场景；compositions/ 中可分别修改开场、创作工作区、团队、漫画和结尾。截图、漫画、字体、GSAP 与剪辑后的音乐都在 assets/，渲染不依赖在线媒体。

工程文字可在 HTML 或 HyperFrames 中修改。字体为本片子集，增加全新汉字时请替换为完整的 Noto Sans CJK SC 字体并更新 CSS。日常剪辑、换图、修改已有字词无需重新构建。

## 检查与导出

需 FFmpeg 和 FFprobe 在 PATH 上。本机工作目录已保留 tools/ 下的独立工具；交付 ZIP 不包含这些大体积通用程序，可自行安装 FFmpeg。

```powershell
npm run check
npm run render -- --quality delivery --output renders/ComicCraft-AI-demo.mp4
```

也可以使用 run-demo.ps1，自动识别本目录下的独立 FFmpeg。

## 来源与复现

- assets/screens/ 保存实际网站的全新 Edge 截图。
- assets/ASSET-LEDGER.json 记录媒体来源。
- DESIGN.md、SCRIPT.md、STORYBOARD.md、SPEC.md 是视觉和时间线说明。
- 本包是可直接编辑的成品工程，不需要运行生成脚本。
- compositions/components/agent-cursor.html 保留 HyperFrames 注册表原始组件，demo-cursor.html 为本片的实际适配。
- REVIEW.md 记录检查与视觉复核结果。音频响度通过工具测量，不声称人工听审。
