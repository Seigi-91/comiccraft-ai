# 模型协议与验证状态

更新：2026-11-02。**协议已接入 ≠ 厂商服务已实测 ≠ 画质已达标。** 设置页现提供五类能力的显式验证入口，每次须确认可能收费；历史记录保留时间和配置匹配状态。这是运行者本机的验证，不自动上传为公开支持承诺。目前自动化测试使用 MockTransport 验证请求路由与返回处理；尚未有有效密钥完成本轮真实付费调用，不列任何“已实测可用”供应商品牌。

| 能力 | 请求协议 | 可配置字段 | 当前证据 |
|---|---|---|---|
| 文字/JSON | POST `/chat/completions`，字符串消息 | AI_PROVIDER、LOCAL_GPT_*、DEFAULT_TEXT_MODEL | 模拟请求、JSON 解析及设置持久化测试通过 |
| 图片理解 | 同上，消息含 `image_url` | DEFAULT_VISION_MODEL；同一文字地址和 Key | 模拟请求验证实际发送图像 data URL 和视觉模型名 |
| 文生图 | POST `/images/generations`，JSON | IMAGE_PROVIDER、IMAGE_API_* | 模拟返回真实格式 PNG 后写入本地；非真实模型创作 |
| 参考图生成 | POST `/images/edits`，multipart `image[]` | 同图片配置 | 模拟请求验证附件和模型路由；服务须接受多图字段 |
| 局部精修 | POST `/images/edits`，原图 + alpha 蒙版 | IMAGE_EDIT_* | 原有模拟接口与蒙版外像素保护测试；未验证真实服务画质 |
| 旧 ChatGPT 回填 | 历史数据 | 不可用于新任务 | 已有待办可改用自动连接继续 |

普通生图接受 `data[0].b64_json` 或 URL；蒙版接口目前要求 base64。服务不支持尺寸、无额度、缺视觉能力或使用其他 JSON 结构时可能失败，不静默降级或返回占位图。

## 提交真实兼容报告

使用 [Provider compatibility 模板](https://github.com/Seigi-91/comiccraft-ai/issues/new/choose)，包含：日期、项目提交、服务名、模型确切名称、测试能力、图片尺寸、状态码与脱敏结果。建议从最小单次请求开始，不使用私人漫画验证。先确认服务费用和隐私政策。

请不要提交 Key、Authorization、含令牌的 URL、.env 或私人参考图。维护者可根据可复现证据补上已验证清单；没有运行证据就继续保留未验证状态。社区报告也需标注报告者、日期和对应 Issue，不能自动当作官方支持承诺。
