from fastapi import APIRouter, Depends, HTTPException
from app.db.session import get_db
from app.core.config import settings
from app.services.diagnostics import diagnostics
from app.services.sample_import import import_rain_night

router=APIRouter()


@router.get('/diagnostics')
async def check_environment():
    import asyncio
    return await asyncio.to_thread(diagnostics,font_path=settings.COMIC_FONT_PATH,port=settings.APP_PORT)


@router.post('/sample')
async def sample(db=Depends(get_db)):
    try:
        return await import_rain_night(db)
    except (OSError,ValueError) as error:
        await db.rollback()
        raise HTTPException(422,'示例导入失败，请检查样例文件与字体配置。原有项目未改变。') from error
