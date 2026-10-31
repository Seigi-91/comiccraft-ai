"""Real multipart edits adapter; model pixels are confined to the selected mask."""
from io import BytesIO
import base64
from uuid import uuid4
import httpx
from PIL import Image, ImageDraw, ImageChops, ImageStat
from app.core.config import settings
from app.core.paths import MEDIA
from app.tools.media import local_image_path


def png(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def create_mask(source_url, polygons):
    with Image.open(local_image_path(source_url)) as image:
        width,height=image.size
    mask=Image.new('L',(width,height),0)
    draw=ImageDraw.Draw(mask)
    for polygon in polygons:
        draw.polygon([(round(p['x']/100*(width-1)),round(p['y']/100*(height-1))) for p in polygon],fill=255)
    selected=ImageStat.Stat(mask).sum[0]/255
    if selected<16 or selected>width*height*.8:
        raise ValueError('请选择有效局部区域（至少16像素且不超过画面80%）')
    path=MEDIA/f'mask-{uuid4().hex}.png';mask.save(path)
    return '/media/'+path.name


async def edit_image(source_url, mask_url, instructions):
    if not settings.IMAGE_EDIT_BASE_URL:
        raise ValueError('图像编辑服务未配置；请设置 IMAGE_EDIT_BASE_URL、IMAGE_EDIT_MODEL 和密钥')
    with Image.open(local_image_path(source_url)) as im: source=im.convert('RGB')
    with Image.open(local_image_path(mask_url)) as im: mask=im.convert('L')
    # OpenAI-compatible masks: alpha=0 means edit; opaque means preserve.
    api_mask=Image.new('RGBA',source.size,(255,255,255,255))
    api_mask.putalpha(ImageChops.invert(mask))
    headers={'Authorization':'Bearer '+settings.IMAGE_EDIT_API_KEY} if settings.IMAGE_EDIT_API_KEY else {}
    async with httpx.AsyncClient(timeout=settings.GPT_TIMEOUT) as client:
        response=await client.post(settings.IMAGE_EDIT_BASE_URL.rstrip('/')+'/images/edits',headers=headers,
            data={'model':settings.IMAGE_EDIT_MODEL,'prompt':'仅修复透明蒙版区域，保持画风、身份、构图及未选区域不变。不要加字。修改要求：'+instructions,'n':'1'},
            files={'image':('source.png',png(source),'image/png'),'mask':('mask.png',png(api_mask),'image/png')})
        if response.status_code>=400:
            raise ValueError(f'图像编辑接口返回 HTTP {response.status_code}，请检查模型、接口、密钥和额度')
        items=response.json().get('data') or []
        if not items or not items[0].get('b64_json'):
            raise ValueError('编辑服务须返回 data[0].b64_json 图片；当前返回格式不受支持')
        raw=base64.b64decode(items[0]['b64_json'],validate=True)
    return composite_candidate(source_url,mask_url,raw)


def composite_candidate(source_url, mask_url, raw, allow_resize=False):
    with Image.open(local_image_path(source_url)) as im: source=im.convert("RGB")
    with Image.open(local_image_path(mask_url)) as im: mask=im.convert("L")
    if len(raw)>20*1024*1024:
        raise ValueError('编辑结果超过20MB')
    with Image.open(BytesIO(raw)) as im:
        if im.width*im.height>25_000_000:
            raise ValueError('编辑结果像素过大')
        edited=im.convert('RGB')
        if im.size!=source.size:
            if not allow_resize or abs(im.width/im.height-source.width/source.height)>0.001:
                raise ValueError('返回图片尺寸与原图不同：可勾选允许同宽高比对齐后重新上传；宽高比不一致的图片不能采用')
            edited=edited.resize(source.size,Image.Resampling.LANCZOS)
    # Outside-mask pixels are EXACTLY the source pixels, regardless of model drift.
    result=Image.composite(edited,source,mask)
    path=MEDIA/f'repair-{uuid4().hex}.png';result.save(path)
    return '/media/'+path.name
