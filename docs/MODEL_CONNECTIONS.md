# 两种图片生成方式

在本机安装并启动完整应用后，进入「创作团队与设置 → 图片模型连接」。GitHub Pages 仅为静态展示，不能存储密钥或执行模型任务。

## 本机 ChatGPT（无 API Key）

选择「本机 ChatGPT · 协作回填」并保存。任务运行到需要文字或图片时会暂停在待办。复制提示词，下载参考图，在自己的 ChatGPT 中完成生成，再上传图片或粘贴结构化结果，流程随即继续。需要使用者自己的 ChatGPT 账户及相应功能权限。安装桌面客户端并不会让网站自动拥有一个 HTTP 接口；本项目不抓取登录会话或调用私有端点。

## 图像模型 API（自动出图）

选择「图像模型 API · 自动生成」，输入服务提供方给出的 API 基础地址（通常以 `/v1` 结尾）、确切模型名及自己的 API Key，然后保存。留空密钥保留原值；勾选清除会删除保存值。可勾选「局部精修同时使用此服务」。保存不会发起付费生成，也不代表已验证账户额度或模型权限。

- 无参考图：POST `/images/generations`，JSON 包含 model、prompt、n、size。
- 有角色或前格参考图：POST `/images/edits`，multipart 的 `image[]` 上传本站 PNG 参考图。
- 局部精修：已有编辑接口上传原图及透明蒙版；回传后执行蒙版合成，未选区保留原图像素。
- 服务必须支持这些 OpenAI 兼容格式，且支持所选尺寸；只有私有格式的服务（例如不同格式的模型网关）需要另外适配，不能只填一个 Key 就通用。
- 返回格式支持 `data[0].b64_json`，普通生图同时支持 `data[0].url`；局部精修当前需要 base64。
- 请求失败会保留失败状态供重试，不会伪装成功，也不会静默转用其他服务。费用、限额与网络由运行者承担。

文字 agent 仍由 AI_PROVIDER 控制，因此可以使用「文字 ChatGPT 回填 + 图片 API 自动生成」的组合。要让文字也自动生成，在服务端配置 `AI_PROVIDER=local_http`、`LOCAL_GPT_BASE_URL`、`LOCAL_GPT_API_KEY` 及支持的文字/视觉模型名。

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
