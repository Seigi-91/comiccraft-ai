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
    outfit = next((o for o in data['outfits'] if o['id'] == data['active_outfit_id']), None)
    return {"id": profile.id, "name": profile.name, "appearance": data['appearance'],
            "reference_image_url": profile.reference_image_url, **data,
            "active_outfit": outfit,
            "wardrobe_instruction": "人物脸型、发型与体态遵循外貌设定和角色参考图；服装以 active_outfit 为准，参考图旧服装不得覆盖当前服装。无当前方案则沿用原设定。"}
