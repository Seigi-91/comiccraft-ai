import asyncio
from fastapi import APIRouter, Request
from app.api.local_access import require_local_settings
from app.tools.codex_connector import status
router=APIRouter()


@router.get("/status")
async def connection_status(request:Request):
    require_local_settings(request)
    return await asyncio.to_thread(status)


@router.get("/installer")
async def installer():
    import io, zipfile
    from fastapi.responses import Response
    from app.core.paths import ROOT
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
        for name in ["Install-Codex-Connector.cmd","scripts/install_codex.ps1","scripts/install_codex.sh"]:
            text=(ROOT/name).read_text(encoding="utf-8")
            if name.endswith((".cmd",".ps1")):text=text.replace("\r\n","\n").replace("\n","\r\n")
            archive.writestr(name,text.encode("utf-8"))
        archive.writestr("README.txt","Unzip first. Windows: double-click Install-Codex-Connector.cmd. Requires Node.js 20+. Installs official @openai/codex and opens its ChatGPT login. No app keys or account credentials are in this package. macOS/Linux: bash scripts/install_codex.sh. Then refresh website status and explicitly test capabilities.")
    return Response(buffer.getvalue(),media_type="application/zip",headers={"Content-Disposition":'attachment; filename="ComicCraft-Codex-Connector.zip"'})
