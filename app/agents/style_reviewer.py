from app.agents.base import VisionAgent
from app.agents.skills import instructions
from app.models.schemas import ReviewResult


class StyleReviewerAgent(VisionAgent):
    async def review_panels(self, panels, style_ref_urls=None, characters=None):
        if not panels:
            raise ValueError("没有可审核的图片")
        results = []
        identity_refs = [
            c["reference_image_url"] for c in characters or [] if c.get("reference_image_url")
        ]
        for position, panel in enumerate(panels):
            references = [panel["image_url"], *identity_refs]
            if position:
                references.extend([panels[0]["image_url"], panels[position - 1]["image_url"]])
            references = list(dict.fromkeys(references))[:6]
            prompt = instructions("style_reviewer") + "\n分镜要求：" + panel.get("prompt", "")
            prompt += (
                "\n第一张为待审面板，其余为角色表及已生成的开场/前一格参考。"
                "必须跨图对比脸型、发型、服装、道具、动物花纹、天气和场景结构。镜头变化不等于连续性错误。"
                "实际附图路径顺序：" + str(references)
            )
            review = ReviewResult.model_validate(
                await self.llm_client.review_images(references, prompt)
            ).model_dump()
            review["passed"] = bool(
                review["passed"]
                and review["score"] >= 80
                and not any(i["severity"] == "high" for i in review["issues"])
            )
            review["panel_index"] = panel["index"]
            results.append(review)
        passed = all(r["passed"] for r in results)
        return {
            "passed": passed,
            "overall_passed": passed,
            "overall_score": sum(r["score"] for r in results) / len(results),
            "panel_reviews": results,
        }

    async def execute(self, **kwargs):
        return await self.review_panels(**kwargs)
