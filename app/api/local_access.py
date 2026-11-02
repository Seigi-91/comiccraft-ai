from urllib.parse import urlsplit
from fastapi import HTTPException
from app.core.config import settings


def require_local_settings(request):
    local={'localhost','127.0.0.1','::1','testserver','testclient'}
    peer=request.client.host if request.client else ''
    try:
        host=urlsplit('http://'+request.headers.get('host','')).hostname
        origin=request.headers.get('origin')
        origin_host=urlsplit(origin).hostname if origin else None
    except ValueError:
        raise HTTPException(403,'本机配置请求来源无效')
    if not settings.ENABLE_LOCAL_SETTINGS or peer not in local or host not in local or (origin and origin_host not in local):
        raise HTTPException(403,'仅允许本机设置请求；远程部署由管理员配置环境变量。')
