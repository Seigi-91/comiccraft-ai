"""Import the authored six-panel story through the real desktop-handoff API.

This does not generate images or fabricate an LLM call. It submits the saved
Codex-authored story, built-in imagegen outputs, and recorded visual reviews.
The website runs its ordinary LangGraph nodes and actual layout renderer.
"""
import argparse
import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/rain-night-light"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    production = json.loads((OUTPUT / "production.json").read_text(encoding="utf-8"))
    reviews = json.loads((OUTPUT / "review.json").read_text(encoding="utf-8"))
    if len(production["panels"]) != 6 or len(reviews["panels"]) != 6:
        raise ValueError("Six panels and six actual visual review records are required")
    for panel in production["panels"]:
        if not (OUTPUT / (panel["slug"] + ".png")).is_file():
            raise FileNotFoundError(panel["slug"])
    client = httpx.Client(base_url=args.base_url, timeout=120)

    def request(method, url, **kwargs):
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def upload(path):
        with path.open("rb") as image:
            return request("POST", "/api/studio/uploads", files={"file":(path.name,image,"image/png")})["url"]

    saved = OUTPUT / "website.json"
    if saved.exists():
        publication = json.loads(saved.read_text(encoding="utf-8"))
    else:
        project = request("POST", "/api/projects", json={
            "name":"雨夜留灯 · 六格连续漫画",
            "description":"一封旧信，一只淋雨的小猫，一盏为晚归者留下的灯。",
            "inspiration":"六格完整短篇；主角小雨、橘白小猫、旧书店。人物与场景保持一致。先读奶奶的信，后发现小猫、抱起、进店、安置，最后在窗边留灯。"})
        sheet_url = upload(OUTPUT / "characters/characters.png")
        for name, appearance in [
            ("小雨", "24岁中国女性，棕眼，黑色齐下巴短发、薄刘海；红色连帽雨衣（帽子始终放下）、黑色纽扣、炭灰针织衫、黑裤、深棕短靴、同一只黑色皮挎包。"),
            ("小橘", "橘色虎斑幼猫，绿色眼睛、白口鼻、白胸脯、四只白爪、无项圈。")]:
            character = request("POST", f"/api/projects/{project['id']}/characters",
                                params={"name":name, "appearance_description":appearance})
            request("POST", f"/api/projects/{project['id']}/characters/{character['character_id']}/reference",
                    params={"reference_image_url":sheet_url})
        chapter = request("POST", f"/api/projects/{project['id']}/chapters", json={"title":"第一章：雨夜留灯"})
        task = request("POST", "/api/tasks/generate-chapter", json={"project_id":project["id"], "chapter_id":chapter["id"]})
        publication = {"project_id":project["id"], "chapter_id":chapter["id"], "task_id":task["id"],
                       "url":f"{args.base_url}/projects/{project['id']}", "image_urls":{}}
        saved.write_text(json.dumps(publication, ensure_ascii=False, indent=2), encoding="utf-8")

    characters = [
        {"name":"小雨", "appearance":"黑色齐下巴短发与薄刘海，棕色眼睛，红色雨衣帽子放下，灰黑针织衫、黑长裤、棕短靴、黑皮挎包", "personality":"安静、心软，愿意将被爱变成行动", "role":"主角"},
        {"name":"小橘", "appearance":"橘虎斑幼猫，白嘴、白胸、白爪、绿眼睛，无项圈", "personality":"从害怕到信任", "role":"被帮助者"}]
    story = {"title":"雨夜留灯", "world_view":"当代江南老城，同一场夜雨、同一家深绿木门旧书店。窗在门左、长椅在门右、黄铜台灯始终亮着。",
             "outline":[{"scene":p["title"], "location":"旧书店门外" if p["index"]<4 else "旧书店窗边",
                         "event":p["caption"], "emotion":["孤独与怀念","担心","温柔与决心","行动与信任","安心","希望"][p["index"]],
                         "characters":["小雨"] if p["index"]==0 else ["小雨","小橘"]} for p in production["panels"]],
             "characters":characters}
    storyboard = {"layout_type":"条漫", "panels":[
        {"index":p["index"], "shot_type":["全景","低机位近景","中近景","背侧中景","室内中景","外景全景"][p["index"]],
         "perspective":["平视","低视角","三分之四侧面","背侧","平视","平视"][p["index"]],
         "composition":{"grid":"3x3", "focal_point":{"x":45,"y":50}},
         "action":p["title"]+"。"+p["caption"], "background":"同一家旧书店：左窗、右门、门右长椅；黄铜台灯在窗边，屋外雨夜。",
         "lighting":"靛蓝雨夜与琥珀灯光；从未改变天气或时间。",
         "character_positions":[{"character":c,"position":"center"} for c in (["小雨"] if p["index"]==0 else ["小雨","小橘"])],
         "production_prompt":p["prompt"]} for p in production["panels"]]}
    dialogues = {"bubbles":[{"panel_index":p["index"], "text":p["caption"].strip('“”'),
                             "character":"小雨" if p["index"] in [2,5] else None,
                             "bubble_type":"normal" if p["index"]==2 else "thinking" if p["index"]==5 else "narrator",
                             "position":{"x":5,"y":5}} for p in production["panels"]]}
    # API returns promptly; its background graph then advances to the next handoff.
    for _ in range(150):
        task = request("GET", "/api/tasks/"+publication["task_id"])
        if task["status"] == "completed":
            publication["final_comic"] = task["result"]["final_comic"]
            saved.write_text(json.dumps(publication, ensure_ascii=False, indent=2), encoding="utf-8")
            image = client.get(publication["final_comic"]["final_image_url"])
            image.raise_for_status()
            (OUTPUT / "雨夜留灯-完整条漫.png").write_bytes(image.content)
            print(json.dumps(publication, ensure_ascii=False))
            return
        if task["status"] == "failed":
            raise RuntimeError(task["error_message"])
        pending_id = (task.get("result") or {}).get("pending_job_id")
        if task["status"] != "needs_human" or not pending_id:
            time.sleep(0.5)
            continue
        job = next(j for j in request("GET", "/api/studio/jobs", params={"task_id":task["id"]}) if j["id"]==pending_id)
        stage = job["stage"]
        if stage in ["generate_outline", "generate_storyboard", "generate_dialogue"]:
            content = {"generate_outline":story, "generate_storyboard":storyboard, "generate_dialogue":dialogues}[stage]
            payload = {"text":json.dumps(content, ensure_ascii=False)}
        elif job["kind"] == "image":
            index = int(stage.rsplit(":",1)[1])
            key = str(index)
            if key not in publication["image_urls"]:
                publication["image_urls"][key] = upload(OUTPUT / (production["panels"][index]["slug"]+".png"))
                saved.write_text(json.dumps(publication, ensure_ascii=False, indent=2), encoding="utf-8")
            payload = {"image_url":publication["image_urls"][key]}
        elif job["kind"] == "vision":
            target = job["images"][0]
            index = next(int(k) for k,v in publication["image_urls"].items() if v==target)
            review = reviews["panels"][index]
            if not review["inspected"]:
                raise ValueError(f"Panel {index} has not been visually inspected")
            payload = {"text":json.dumps({"passed":review["passed"], "score":review["score"], "issues":review["issues"]}, ensure_ascii=False)}
        else:
            raise ValueError("Unrecognized handoff: "+str(job))
        request("POST", f"/api/studio/jobs/{pending_id}/reply", json=payload)
        print(f"Submitted {stage}", flush=True)
    raise TimeoutError("Generation did not complete; saved task can resume")


if __name__ == '__main__':
    main()
