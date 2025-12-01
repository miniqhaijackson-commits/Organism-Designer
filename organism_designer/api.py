from fastapi import APIRouter, HTTPException
from typing import List
from backend import db
from . import models

router = APIRouter()

@router.post("/organisms", response_model=models.Organism)
def create_organism(organism: models.OrganismCreate):
    """Create a new organism."""
    org_id = db.create_organism(
        name=organism.name,
        genome=organism.genome,
        parent_id=organism.parent_id
    )
    db_organism = db.get_organism(org_id)
    return db_organism

@router.get("/organisms", response_model=List[models.Organism])
def list_organisms(limit: int = 50):
    """List all organisms."""
    return db.list_organisms(limit=limit)

@router.get("/organisms/{organism_id}", response_model=models.Organism)
def get_organism(organism_id: int):
    """Get a single organism by its ID."""
    db_organism = db.get_organism(organism_id)
    if db_organism is None:
        raise HTTPException(status_code=404, detail="Organism not found")
    return db_organism
