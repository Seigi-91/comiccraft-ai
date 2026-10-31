"""Deterministic, non-destructive local effects; original media is never overwritten."""
import math
import random
from typing import Literal
from PIL import Image,ImageDraw,ImageEnhance
from pydantic import BaseModel,Field,model_validator


class EffectLayer(BaseModel):
    id:str=Field(min_length=1,max_length=100)
    kind:Literal['rain','speed_lines','warm_glow','contrast']
    enabled:bool=True
    opacity:float=Field(default=.3,ge=0,le=1)
    x:float=Field(default=0,ge=0,le=100)
    y:float=Field(default=0,ge=0,le=100)
    width:float=Field(default=100,gt=0,le=100)
    height:float=Field(default=100,gt=0,le=100)

    @model_validator(mode='after')
    def bounds(self):
        if self.x+self.width>100 or self.y+self.height>100:raise ValueError('特效区域超出画面')
        return self


def apply_effects(image,layers):
    image=image.convert('RGB').copy()
    for raw in layers:
        layer=EffectLayer.model_validate(raw)
        if not layer.enabled or not layer.opacity:continue
        x=round(image.width*layer.x/100);y=round(image.height*layer.y/100)
        right=min(image.width,round(image.width*(layer.x+layer.width)/100));bottom=min(image.height,round(image.height*(layer.y+layer.height)/100))
        if right<=x or bottom<=y:continue
        original=image.crop((x,y,right,bottom));w,h=original.size
        if layer.kind=='contrast':effect=ImageEnhance.Contrast(original).enhance(1.6)
        elif layer.kind=='warm_glow':
            tint=Image.new('RGB',(w,h),(255,203,120));effect=Image.blend(original,tint,.6)
        else:
            canvas=original.convert('RGBA');overlay=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(overlay);rng=random.Random(layer.id)
            if layer.kind=='rain':
                for _ in range(max(20,w*h//6000)):
                    px=rng.randint(0,w);py=rng.randint(0,h);length=rng.randint(15,45)
                    draw.line((px,py,px-5,py+length),fill=(200,225,255,160),width=max(1,w//650))
            else:
                for _ in range(55):
                    angle=rng.random()*math.tau;r0=rng.uniform(.5,.8);rx=w*.8;ry=h*.8
                    draw.line((w/2+math.cos(angle)*rx*r0,h/2+math.sin(angle)*ry*r0,w/2+math.cos(angle)*rx,h/2+math.sin(angle)*ry),fill=(240,240,240,220),width=max(1,w//500))
            effect=Image.alpha_composite(canvas,overlay).convert('RGB')
        image.paste(Image.blend(original,effect,layer.opacity),(x,y))
    return image
