---
name: bubble-placement
description: Inspect actual comic panel images to place dialogue bubbles in negative space while protecting faces, hands, important objects and action. Return verifiable normalized boxes and speaker targets.
---

# 视觉气泡定位

必须查看所附实际分镜，不凭台词或画面文字描述猜测人脸位置。任务是排版，不改变台词、角色或画面。

1. 标出全部可见人脸、头部、手部、关键道具和叙事动作的保护矩形，适当扩大边界；分别记录 kind。坐标以整幅图片为基准，左上原点，单位均为 0–100 百分比。
2. 根据台词确定说话者；无法确定时不要虚构身份。优先寻找上方、两侧或背景的负空间，保持从上到下阅读顺序。保护区域和气泡主体不得相交，气泡之间留出间隔。
3. 每条输入台词只返回一个 placement，使用其 id；position 是中心，size 是宽高。正文必须能容纳，宁可移动或合理加大，不压缩到不可读字号。禁止修改原台词或漏掉台词。
4. speech 的 tail 指向说话者口部附近或身体边缘，不穿过其他气泡；thought 用圆点链；narration 不指向人物。不能确定说话者时保留原尾尖，注明原因。
5. 检查边界、保护框、气泡之间、阅读顺序和尾尖。如果没有足够空间，返回 fits=false 和具体原因，不伪造可行布局，也不移动人脸保护框来迁就气泡。

严格返回所附 JSON Schema。regions 是实际视觉判断，后端只能校验这些已识别框，无法证明检测没有漏掉人脸；最终仍应人工预览。识别失败应停止，不以随机坐标、固定顶部位置或空保护框假装完成。
