from app.agents.base import VisionAgent
from app.agents.skills import instructions
from app.models.schemas import ReviewResult


import json,hashlib

class StyleReviewerAgent(VisionAgent):
    async def review_panels(self, panels, style_ref_urls=None, characters=None, previous_reviews=None):
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
            prompt = instructions("style_reviewer", panel.get("prompt", "")) + "\n分镜要求：" + panel.get("prompt", "")
            prompt += (
                "\n第一张为待审面板，其余为角色表及已生成的开场/前一格参考。"
                "必须跨图对比脸型、发型、服装、道具、动物花纹、天气和场景结构。镜头变化不等于连续性错误。"
                "实际附图路径顺序：" + str(references)
            )
            from app.api.routes.compatibility import fingerprint
            from app.services.production_records import asset_hash
            reference_hashes=[asset_hash(u) for u in references]
            signature=hashlib.sha256(json.dumps([prompt,reference_hashes,fingerprint('vision')],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            previous=next((r for r in previous_reviews or [] if r.get('panel_index')==panel['index']),{})
            if all(reference_hashes) and previous.get('passed') and previous.get('evidence_signature')==signature:
                results.append({**previous,'reused_review':True})
                continue
            review = ReviewResult.model_validate(
                await self.llm_client.review_images(references, prompt)
            ).model_dump()
            review["passed"] = bool(
                review["passed"]
                and review["score"] >= 80
                and not any(i["severity"] == "high" for i in review["issues"])
            )
            review["panel_index"] = panel["index"]
            review["evidence_signature"] = signature
            review["reused_review"] = False
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
