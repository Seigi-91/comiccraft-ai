from pydantic import BaseModel, Field, model_validator
from app.models.orm import CharacterDetails


class Outfit(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=4000)
    occasion: str = Field(default="", max_length=1000)


class CharacterModules(BaseModel):
    identity: str = Field(default="", max_length=4000)
    personality: str = Field(default="", max_length=4000)
    appearance: str = Field(default="", max_length=4000)
    background: str = Field(default="", max_length=4000)
    relationships: str = Field(default="", max_length=4000)
    voice: str = Field(default="", max_length=4000)
    outfits: list[Outfit] = Field(default_factory=list, max_length=30)
    active_outfit_id: str | None = None

    @model_validator(mode="after")
    def check_outfit(self):
        ids = [o.id for o in self.outfits]
        if len(ids) != len(set(ids)):
            raise ValueError("服装编号不能重复")
        if self.active_outfit_id and self.active_outfit_id not in ids:
            raise ValueError("当前服装必须属于此角色的服装方案")
        return self


async def modules(db, profile):
    row = await db.get(CharacterDetails, profile.id)
    return CharacterModules.model_validate(row.data).model_dump() if row else CharacterModules(appearance=profile.appearance_description or "").model_dump()


async def creative_character(db, profile):
    data = await modules(db, profile)
    from app.services.character_assets import approved_asset
    revision=await approved_asset(db,profile.id)
    name,reference=profile.name,profile.reference_image_url
    if revision:
        data=CharacterModules.model_validate(revision.snapshot['modules']).model_dump()
        name,reference=revision.snapshot['name'],revision.snapshot['reference_image_url']
    outfit = next((o for o in data['outfits'] if o['id'] == data['active_outfit_id']), None)
    return {"id": profile.id, "name": name, "appearance": data['appearance'],
            "reference_image_url": reference, **data,
            "asset_revision_id":revision.id if revision else None,"asset_sha256":revision.sha256 if revision else None,
            "active_outfit": outfit,
            "wardrobe_instruction": "人物脸型、发型与体态遵循外貌设定和角色参考图；服装以 active_outfit 为准，参考图旧服装不得覆盖当前服装。无当前方案则沿用原设定。"}
