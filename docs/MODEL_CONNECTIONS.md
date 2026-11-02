# 模型连接：官方 Codex、API 与人工回填

在本机安装并启动完整应用后，进入「创作团队与设置 → 图片模型连接」。GitHub Pages 仅为静态展示，不能存储密钥或执行模型任务。

## 官方 Codex 自动连接（ChatGPT 登录）

设置页下载安装/登录助手，安装官方CLI并使用自己的ChatGPT登录；随后可在文字或图片下拉独立选择Codex。文字与视觉自动返回JSON，图片模式要求真实生成附件；设置向导可完成官方登录、验证和启用。v2.5本机向导实测文字、视觉和真实生图通过，使用原生生成事件导入图片；新用户须验证自己的账号，API和人工回填保留。运行使用账户额度，不是离线模型，也不自动操控聊天窗口。已有人工回填模式继续保留。

[完整安装、实测结果与执行边界](CODEX_CONNECTION.md)。

## 本机 ChatGPT（无 API Key）

选择「本机 ChatGPT · 协作回填」并保存。任务运行到需要文字或图片时会暂停在待办。复制提示词，下载参考图，在自己的 ChatGPT 中完成生成，再上传图片或粘贴结构化结果，流程随即继续。需要使用者自己的 ChatGPT 账户及相应功能权限。安装桌面客户端并不会让网站自动拥有一个 HTTP 接口；本项目不抓取登录会话或调用私有端点。

## 文字与视觉模型 API（自动写作）

在「文字与视觉模型连接」选择「文字模型 API · 自动生成」，填写 API 基础地址、文字模型、视觉模型和文字专用 API Key，点击「保存文字设置」。文字与图片分开保存，密钥不要求相同。留空保留原密钥，勾选清除可删除；无鉴权本地服务可留空。

文字请求使用 OpenAI 兼容 `POST /chat/completions`，用于大纲、分镜、台词和文本推理。视觉审核和气泡定位使用同一个接口地址和 Key，但读取单独的视觉模型名，并发送 `image_url` 图片输入。若使用同一个多模态模型，可在两个模型框填写同一名称。模型必须支持对应能力，并能按提示词返回 JSON；不兼容该协议的厂商需要额外适配。

可组合「文字 API + 图片 API」「文字 API + ChatGPT 图片回填」「文字 ChatGPT 回填 + 图片 API」或全流程 ChatGPT 回填。保存后新的执行阶段采用所选服务；现有待办不会被自动删除或转换，应先完成或按任务恢复流程处理。正在生成时禁止切换。

例如在服务端设置：

```dotenv
AI_PROVIDER=local_http
LOCAL_GPT_BASE_URL=https://你的服务地址/v1
LOCAL_GPT_API_KEY=你的文字密钥
DEFAULT_TEXT_MODEL=服务支持的文字模型
DEFAULT_INFERENCE_MODEL=服务支持的文字模型
DEFAULT_VISION_MODEL=服务支持的视觉模型
```

## 图像模型 API（自动出图）

选择「图像模型 API · 自动生成」，输入服务提供方给出的 API 基础地址（通常以 `/v1` 结尾）、确切模型名及自己的 API Key，然后保存。留空密钥保留原值；勾选清除会删除保存值。可勾选「局部精修同时使用此服务」。保存不会发起付费生成，也不代表已验证账户额度或模型权限。

- 无参考图：POST `/images/generations`，JSON 包含 model、prompt、n、size。
- 有角色或前格参考图：POST `/images/edits`，multipart 的 `image[]` 上传本站 PNG 参考图。
- 局部精修：已有编辑接口上传原图及透明蒙版；回传后执行蒙版合成，未选区保留原图像素。
- 服务必须支持这些 OpenAI 兼容格式，且支持所选尺寸；只有私有格式的服务（例如不同格式的模型网关）需要另外适配，不能只填一个 Key 就通用。
- 返回格式支持 `data[0].b64_json`，普通生图同时支持 `data[0].url`；局部精修当前需要 base64。
- 请求失败会保留失败状态供重试，不会伪装成功，也不会静默转用其他服务。费用、限额与网络由运行者承担。

文字 agent 仍由 AI_PROVIDER 控制，因此可以使用「文字 ChatGPT 回填 + 图片 API 自动生成」的组合。要让文字也自动生成，可在网页设置面板保存，或在服务端配置 `AI_PROVIDER=local_http`、`LOCAL_GPT_BASE_URL`、`LOCAL_GPT_API_KEY` 及支持的文字/视觉模型名。

## 环境变量

```dotenv
AI_PROVIDER=chatgpt_desktop
IMAGE_PROVIDER=openai
IMAGE_API_BASE_URL=https://api.openai.com/v1
IMAGE_API_MODEL=gpt-image-1
IMAGE_API_KEY=你的密钥（仅写入本机文件）
IMAGE_EDIT_PROVIDER=openai
IMAGE_EDIT_BASE_URL=https://api.openai.com/v1
IMAGE_EDIT_MODEL=gpt-image-1
IMAGE_EDIT_API_KEY=你的密钥（仅写入本机文件）
```

如不设置 IMAGE_PROVIDER，将兼容旧版 AI_PROVIDER 和 LOCAL_GPT_* 图片配置。新安装者建议明确配置 IMAGE_PROVIDER。本机网页保存后即刻生效；手动修改环境文件则需重启。已有待办保留原来的提示词和结果，切换服务不会自动清空待办。

## 密钥和部署边界

网页写入的是运行后端电脑的 `.env`，不是 GitHub、浏览器本地存储或云端保管库。密钥不会通过配置读取接口返回。配置写入口检查本机连接、Host 与 Origin，远程请求禁止写入；远程部署还应设置 `ENABLE_LOCAL_SETTINGS=false`，由管理员使用环境变量配置，且增加独立的身份认证、HTTPS 和每用户密钥隔离。本项目当前不是开放给陌生人共用管理员密钥的多租户服务。

协议依据：[OpenAI Images API](https://developers.openai.com/api/reference/resources/images/methods/edit)。兼容协议测试通过不等同于每一家第三方服务已通过实际付费生成验证。


## 验证与请求上限

设置页的「服务验证与请求上限」可以检查五类能力，须先勾选费用确认，每次最多一个模型请求。通过只表示协议返回可解析，尚不代表画质达标。请求上限是每任务持久次数保护，未知金额不作估算。详见 [生产控制与恢复](PRODUCTION_SAFETY.md)。

## 专业知识库

六个 agent 的任务提示词会读取对应的原创知识卡；分镜师包含景别、轴线、动作衔接和格间时间方法。不需要另配 embedding API。详见 [知识库接入](../knowledge/README.md)。

## 不配置 API：本机 ChatGPT 知识对照实验

在「创作团队与设置」选择 Agent，展开「ChatGPT 知识对照实验」。输入同一个具体场景，创建成对任务后，将 A/B 完整提示词分别复制到同一界面模型的两个新对话；粘回真实 JSON，填写界面模型名、日期与附件条件。网站不会自动操纵桌面 ChatGPT，也不会为此发起模型 API 请求。

按任务相关性、可执行性、证据与不确定性、约束遵守逐项打 0–4 分并写具体观察；未检查保留未知。完整评分后才显示知识条件映射。生成者可从提示词推断条件，不能自称严格盲评；另给独立评审者发送「仅盲评包」，输出本身也可能暴露条件。模型名称是运行者声明，不是后端身份验证。此实验只比较文字建议，不验证漫画画质。

导出包可能包含私人输入和输出，先自行审阅再分享；不含网站模型密钥。[完整协议](../benchmarks/CHATGPT_AB_PROTOCOL.md)。
