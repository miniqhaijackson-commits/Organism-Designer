from pydantic import BaseModel, Field
from typing import Optional, List


class OrganismCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    genome: str = Field(..., min_length=1, max_length=10000)
    parent_id: Optional[int] = None


class Organism(BaseModel):
    id: int
    name: str
    genome: str
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True
