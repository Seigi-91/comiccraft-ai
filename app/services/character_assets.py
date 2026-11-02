"""Explicitly approved character assets are immutable, independent of draft edits."""
from fastapi import HTTPException
from app.models.orm import CharacterAssetPolicy,CharacterAssetRevision


async def assert_draft_editable(db,character_id):
    policy=await db.get(CharacterAssetPolicy,character_id)
    if policy and policy.locked:
        raise HTTPException(409,'角色版本已锁定；请先解锁编辑，修改后重新审批。已有分镜不自动更新。')


async def approved_asset(db,character_id):
    policy=await db.get(CharacterAssetPolicy,character_id)
    revision=await db.get(CharacterAssetRevision,policy.revision_id) if policy else None
    return revision
