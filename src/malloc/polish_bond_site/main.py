import datetime as dt
import logging
from typing import Annotated


from fastapi import FastAPI, Depends, HTTPException
from malloc.polish_bond.bond import BondMaker, Bond


from .dependencies import SiteBondMaker, Settings

settings = Settings()

logging.basicConfig(level=settings.log_level)
_logger = logging.getLogger(__name__)


app = FastAPI()
sbm = SiteBondMaker(settings)


@app.get("/")
async def root():
    return {"message": "Hello World"}


def bond_by_name(name: str, purchase_date: dt.date, sbm: Annotated[BondMaker, Depends(sbm)]) -> Bond:
    try:
        return sbm(name, purchase_date)        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/by_name/{name}/{purchase_date}")
async def bond_by_name(bond: Annotated[Bond, Depends(bond_by_name)]) -> Bond:
    """Return bond data by name."""    
    return bond


@app.get("/by_name/{name}/{purchase_date}/daily_values")
async def daily_values(bond: Annotated[Bond, Depends(bond_by_name)]) -> list[dict]:
    """Return bond daily values."""
    return bond.daily_values.reset_index().to_dict("records")


@app.get("/by_name/{name}/{purchase_date}/cash_flow")
async def daily_values(bond: Annotated[Bond, Depends(bond_by_name)]) -> list[dict]:
    """Return bond daily values."""
    return bond.cash_flow.reset_index().to_dict("records")
