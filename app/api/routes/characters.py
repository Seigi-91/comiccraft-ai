from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional

from app.db.session import get_db
from app.db.repositories import CharacterProfileRepository
from app.services.character_details import CharacterModules, modules
from app.models.orm import CharacterDetails
from app.tools.sam_client import CharacterConsistencyService

router = APIRouter()


@router.post("/{project_id}/characters")
async def create_character_profile(
    project_id: str,
    name: str,
    appearance_description: str = "",
    db: AsyncSession = Depends(get_db),
):
    repo = CharacterProfileRepository(db)

    existing = await repo.get_by_name(project_id, name)
    if existing:
        return {"character_id": existing.id, "message": "角色已存在"}

    profile = await repo.create(project_id, name, appearance_description)
    return {"character_id": profile.id, "name": profile.name}


@router.post("/{project_id}/characters/{character_id}/reference")
async def set_character_reference(
    project_id: str,
    character_id: str,
    reference_image_url: str,
    db: AsyncSession = Depends(get_db),
):
    repo = CharacterProfileRepository(db)
    consistency_service = CharacterConsistencyService(repo)

    profile = await repo.get(character_id)
    if not profile or profile.project_id != project_id:
        raise HTTPException(status_code=404, detail="角色不存在")

    from app.tools.media import local_image_path

    try:
        if not local_image_path(reference_image_url).is_file():
            raise ValueError("参考图不存在")
    except ValueError as error:
        raise HTTPException(422, str(error))
    await repo.update(
        character_id, {"reference_image_url": reference_image_url, "is_confirmed": True}
    )
    return {
        "character_id": character_id,
        "reference_image_url": reference_image_url,
        "embedding_extracted": False,
        "message": "参考图将直接附给 ChatGPT，不使用 SD/SAM",
    }


@router.post("/{project_id}/characters/{character_id}/confirm")
async def confirm_character_profile(
    project_id: str,
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = CharacterProfileRepository(db)
    consistency_service = CharacterConsistencyService(repo)

    profile = await repo.get(character_id)
    if not profile or profile.project_id != project_id:
        raise HTTPException(status_code=404, detail="角色不存在")

    if not profile.reference_image_url:
        raise HTTPException(status_code=400, detail="请先设置参考图像")

    success = await consistency_service.confirm_character_profile(character_id)
    if success:
        return {"character_id": character_id, "is_confirmed": True, "message": "角色档案已确认"}
    raise HTTPException(status_code=500, detail="确认失败")


@router.get("/{project_id}/characters")
async def list_characters(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = CharacterProfileRepository(db)
    profiles = await repo.list(project_id)

    return [
        {
            "id": p.id,
            "name": p.name,
            "appearance_description": p.appearance_description,
            "modules": await modules(db, p),
            "reference_image_url": p.reference_image_url,
            "is_confirmed": p.is_confirmed,
            "created_at": p.created_at,
        }
        for p in profiles
    ]


@router.get("/{project_id}/characters/{character_id}")
async def get_character_profile(
    project_id: str,
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = CharacterProfileRepository(db)

    profile = await repo.get(character_id)
    if not profile or profile.project_id != project_id:
        raise HTTPException(status_code=404, detail="角色不存在")

    return {
        "id": profile.id,
        "name": profile.name,
        "appearance_description": profile.appearance_description,
        "modules": await modules(db, profile),
        "reference_image_url": profile.reference_image_url,
        "face_mask_url": profile.face_mask_url,
        "face_bbox": profile.face_bbox,
        "is_confirmed": profile.is_confirmed,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


@router.delete("/{project_id}/characters/{character_id}")
async def delete_character_profile(
    project_id: str,
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = CharacterProfileRepository(db)

    profile = await repo.get(character_id)
    if not profile or profile.project_id != project_id:
        raise HTTPException(status_code=404, detail="角色不存在")

    success = await repo.delete(character_id)
    if success:
        return {"message": "角色已删除"}
    raise HTTPException(status_code=500, detail="删除失败")


@router.put("/{project_id}/characters/{character_id}/modules")
async def update_modules(project_id: str, character_id: str, data: CharacterModules, db: AsyncSession = Depends(get_db)):
    profile = await CharacterProfileRepository(db).get(character_id)
    if not profile or profile.project_id != project_id:
        raise HTTPException(404, "角色不存在")
    row = await db.get(CharacterDetails, character_id)
    if row:
        row.data = data.model_dump()
    else:
        db.add(CharacterDetails(character_id=character_id, data=data.model_dump()))
    profile.appearance_description = data.appearance
    await db.commit()
    return {"status": "saved", "modules": data.model_dump()}
