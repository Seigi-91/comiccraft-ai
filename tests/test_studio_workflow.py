"""Real graph + API integration, isolated database and media, deterministic provider replies."""

import base64
import io
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.orchestrator.routing import review_decision
from app.tools.llm_client import parse_json


def task(client, chapter_id):
    return client.get(f"/api/studio/chapters/{chapter_id}/task").json()


def pending(client, chapter_id):
    t = task(client, chapter_id)
    assert t["status"] == "needs_human", t
    job = next(
        j
        for j in client.get("/api/studio/jobs", params={"task_id": t["id"]}).json()
        if j["id"] == t["result"]["pending_job_id"]
    )
    return t, job


def respond(client, chapter_id, response):
    t, j = pending(client, chapter_id)
    result = client.post(f"/api/studio/jobs/{j['id']}/reply", json=response)
    assert result.status_code == 200, result.text
    return t, j


def image_upload(client):
    output = io.BytesIO()
    Image.new("RGB", (400, 300), "#724c9f").save(output, format="PNG")
    response = client.post(
        "/api/studio/uploads", files={"file": ("panel.png", output.getvalue(), "image/png")}
    )
    assert response.status_code == 200, response.text
    return response.json()["url"]


def plan_to_image(client, chapter_id):
    t, j = pending(client, chapter_id)
    assert j["stage"] == "generate_outline"
    invalid = client.post(f"/api/studio/jobs/{j['id']}/reply", json={"text": '{"invalid":true}'})
    assert invalid.status_code == 422
    respond(
        client,
        chapter_id,
        {
            "text": '{"title":"雨夜来信","world_view":"当代城市","outline":[{"scene":"雨夜","event":"少女发现来信"}],"characters":[{"name":"小雨","appearance":"红外套"}]}'
        },
    )
    respond(
        client,
        chapter_id,
        {
            "text": '{"panels":[{"index":0,"shot_type":"中景","perspective":"平视","composition":{"grid":"3x3"},"action":"小雨举起信封","background":"雨夜街角","character_positions":[{"character":"小雨","position":"center"}]}],"layout_type":"条漫"}'
        },
    )
    respond(
        client,
        chapter_id,
        {
            "text": '{"bubbles":[{"panel_index":0,"text":"原来你一直记得。","character":"小雨","bubble_type":"normal","position":{"x":10,"y":10}}]}'
        },
    )


def test_complete_workflow_and_retry():
    with TestClient(app) as client:
        assert client.get("/health").json()["provider"] == "chatgpt_desktop"
        assert len(client.get("/api/studio/agents").json()) == 6
        assert "key" not in client.get("/api/studio/config").text.lower()
        p = client.post(
            "/api/projects", json={"name": "测试项目", "inspiration": "雨夜来信"}
        ).json()
        c = client.post(f"/api/projects/{p['id']}/chapters", json={"title": "第一章"}).json()
        assert "id" in c, c
        wrong = client.post(
            "/api/tasks/generate-chapter", json={"project_id": "wrong", "chapter_id": c["id"]}
        )
        assert wrong.status_code == 404
        created = client.post(
            "/api/tasks/generate-chapter", json={"project_id": p["id"], "chapter_id": c["id"]}
        ).json()
        duplicate = client.post(
            "/api/tasks/generate-chapter", json={"project_id": p["id"], "chapter_id": c["id"]}
        ).json()
        assert duplicate["id"] == created["id"]
        plan_to_image(client, c["id"])
        _, j = pending(client, c["id"])
        assert j["kind"] == "image"
        assert "红外套" in j["prompt"]
        url = image_upload(client)
        respond(client, c["id"], {"image_url": url})
        _, j = pending(client, c["id"])
        assert j["kind"] == "vision"
        assert j["images"] == [url]
        respond(
            client,
            c["id"],
            {
                "text": '{"passed":false,"score":50,"issues":[{"type":"解剖","severity":"high","description":"手部畸形","suggestion":"修正手指"}]}'
            },
        )
        _, j = pending(client, c["id"])
        assert j["kind"] == "image" and "手部畸形" in j["prompt"]
        respond(client, c["id"], {"image_url": image_upload(client)})
        respond(client, c["id"], {"text": '{"passed":true,"score":92,"issues":[]}'})
        finished = task(client, c["id"])
        assert finished["status"] == "completed", finished
        state = finished["result"]["state"]
        assert state["retry_count"] == 2
        assert [e["node"] for e in state["events"]].count("generate_outline") == 1
        final = finished["result"]["final_comic"]
        result = client.get(final["final_image_url"])
        assert result.headers["content-type"] == "image/png"
        with Image.open(io.BytesIO(result.content)) as image:
            assert image.height > 300 and image.width == 1000
        chapters = client.get(f"/api/projects/{p['id']}/chapters").json()
        assert len(chapters[0]["panels"]) == 1
        assert chapters[0]["panels"][0]["status"] == "passed"
        assert chapters[0]["phase"] == "completed"
        assert (
            client.post(f"/api/studio/jobs/{j['id']}/reply", json={"image_url": url}).status_code
            == 409
        )
        assert (
            client.post(
                "/api/studio/uploads", files={"file": ("bad.png", b"not a png", "image/png")}
            ).status_code
            == 422
        )
        assert client.get("/api/missing").status_code == 404


def test_review_routing_pass_on_last_attempt():
    assert (
        review_decision({"retry_count": 3, "review_history": [{"passed": True}]}) == "final_layout"
    )
    assert (
        review_decision({"retry_count": 1, "review_history": [{"passed": False}]})
        == "generate_panels"
    )
    assert (
        review_decision({"retry_count": 3, "review_history": [{"passed": False}]})
        == "human_intervention"
    )


def test_json_fences_and_no_default_fallback():
    assert parse_json('```json\n{"x":1}\n```') == {"x": 1}
    import pytest

    with pytest.raises(ValueError):
        parse_json("not json")


def test_http_adapters_with_local_compatible_responses(monkeypatch):
    import asyncio
    import httpx
    from app.core.config import settings
    from app.tools.llm_client import LLMClient, VisionLLMClient
    from app.tools.image_gen import ImageGeneratorClient

    output = io.BytesIO()
    Image.new("RGB", (64, 64), "#111827").save(output, format="PNG")
    requests = []

    def respond(request):
        import json

        requests.append(json.loads(request.content))
        if request.url.path.endswith("/images/generations"):
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(output.getvalue()).decode()}]}
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"passed":true,"score":90,"issues":[]}'}}]},
        )

    original_client = httpx.AsyncClient
    monkeypatch.setattr(settings, "AI_PROVIDER", "local_http")
    monkeypatch.setattr(settings, "LOCAL_GPT_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original_client(transport=httpx.MockTransport(respond), **kw),
    )

    async def run():
        text = await LLMClient(model="local-text").generate_json("Return JSON")
        assert text["score"] == 90
        url = await ImageGeneratorClient(model="local-image").generate_image("A comic")
        assert url.startswith("/media/")
        review = await VisionLLMClient(model="local-vision").review_image(url, "Review")
        assert review["passed"]
        assert requests[-1]["messages"][0]["content"][1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        assert requests[1]["model"] == "local-image"

    asyncio.run(run())


def test_http_failure_is_not_replaced_by_fake_art(monkeypatch):
    import asyncio
    import httpx
    import pytest
    from app.core.config import settings
    from app.tools.image_gen import ImageGeneratorClient

    original_client = httpx.AsyncClient
    monkeypatch.setattr(settings, "AI_PROVIDER", "local_http")
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(500, json={"error": "offline"})
            ),
            **kw,
        ),
    )
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(ImageGeneratorClient().generate_image("test"))


def test_character_reference_is_local_and_inherited():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "角色测试"}).json()
        character = client.post(
            f"/api/projects/{project['id']}/characters",
            params={"name": "小雨", "appearance_description": "红色雨衣"},
        ).json()
        endpoint = f"/api/projects/{project['id']}/characters/{character['character_id']}/reference"
        assert (
            client.post(
                endpoint, params={"reference_image_url": "https://example.com/fake.png"}
            ).status_code
            == 422
        )
        url = image_upload(client)
        assert client.post(endpoint, params={"reference_image_url": url}).status_code == 200
        profiles = client.get(f"/api/projects/{project['id']}/characters").json()
        assert profiles[0]["is_confirmed"] and profiles[0]["reference_image_url"] == url
        chapter = client.post(
            f"/api/projects/{project['id']}/chapters", json={"title": "第一章"}
        ).json()
        client.post(
            "/api/tasks/generate-chapter",
            json={"project_id": project["id"], "chapter_id": chapter["id"]},
        )
        current, job = pending(client, chapter["id"])
        assert "红色雨衣" in job["prompt"]
        assert current["result"]["state"]["characters"][0]["reference_image_url"] == url
