"""Read-only environment checks. Never includes credentials or model requests."""
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path


def diagnostics(root=None, font_path=None, port=8000):
    root=Path(root) if root else Path(__file__).resolve().parents[2]
    checks=[]
    def add(name,status,detail,fix=''):
        checks.append({'name':name,'status':status,'detail':detail,'fix':fix})
    add('Python','ok' if sys.version_info>=(3,11) else 'error',platform.python_version(),'安装 Python 3.11+（推荐 3.12）。')
    node=shutil.which('node')
    try:
        version=subprocess.run([node,'--version'],capture_output=True,text=True,timeout=5).stdout.strip() if node else ''
        good=int(version.lstrip('v').split('.')[0])>=20
    except (OSError,ValueError,subprocess.TimeoutExpired):version='未检测到';good=False
    add('Node.js','ok' if good else 'warning',version or '未安装','安装 Node.js 20+；已有构建产物时编辑器运行不要求 Node。')
    add('可写目录','ok' if os.access(root,os.W_OK) else 'error','项目目录可写' if os.access(root,os.W_OK) else '项目目录不可写','将项目放入当前用户可写目录。')
    candidates=[font_path, 'C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    font=next((p for p in candidates if p and Path(p).is_file()),None)
    add('中文字体','ok' if font else 'warning','已找到字体文件（自定义字体仍需检查中文字形）' if font else '未找到已配置的中文字体','安装 Noto Sans CJK，并设置 COMIC_FONT_PATH。')
    add('前端构建','ok' if (root/'frontend/dist/index.html').exists() else 'warning','已构建' if (root/'frontend/dist/index.html').exists() else '尚未构建','运行启动脚本或 npm --prefix frontend run build。')
    with socket.socket() as sock:
        occupied=sock.connect_ex(('127.0.0.1',port))==0
    add('本机端口','info',f'{port} '+('已有服务监听；网页内检查时通常是当前应用' if occupied else '可用于启动'),'端口冲突时停止旧服务或更换 --port。')
    return {'ready':not any(c['status']=='error' for c in checks),'checks':checks,'model_requests':0}


if __name__=='__main__':
    import json
    from app.core.config import settings
    print(json.dumps(diagnostics(font_path=settings.COMIC_FONT_PATH,port=settings.APP_PORT),ensure_ascii=False,indent=2))
