import datetime as dt
import json
import logging
from pathlib import Path
from typing import Annotated


from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from malloc.polish_bond.bond import BondMaker, Bond, BOND_TYPES


from .dependencies import SiteBondMaker, Settings

settings = Settings()

logging.basicConfig(level=settings.log_level)
_logger = logging.getLogger(__name__)


app = FastAPI()
sbm = SiteBondMaker(settings)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

TRANSLATIONS_DIR = Path(__file__).parent / "translations"
SUPPORTED_LOCALES = {"en", "pl"}
DEFAULT_LOCALE = "en"


# ── helpers ───────────────────────────────────────────────────────────────────

def load_translations(locale: str) -> dict:
    path = TRANSLATIONS_DIR / f"{locale}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def detect_locale(accept_language: str) -> str:
    return "pl" if "pl" in accept_language.lower() else DEFAULT_LOCALE


def validated_locale(locale: str) -> str:
    return locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE


# ── shared dependency ─────────────────────────────────────────────────────────

def get_bond(name: str, purchase_date: dt.date, sbm: Annotated[BondMaker, Depends(sbm)]) -> Bond:
    try:
        return sbm(name, purchase_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── web UI ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=RedirectResponse)
async def root_redirect(request: Request):
    locale = detect_locale(request.headers.get("accept-language", ""))
    return RedirectResponse(url=f"/{locale}/", status_code=302)


@app.get("/{locale}/", response_class=HTMLResponse)
async def landing_page(request: Request, locale: str, error: str = None):
    locale = validated_locale(locale)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "t": load_translations(locale),
        "locale": locale,
        "path_suffix": "/",
        "error": error,
    })


@app.get("/{locale}/bond/{name}/{purchase_date}", response_class=HTMLResponse)
async def bond_detail_page(
    request: Request,
    locale: str,
    name: str,
    purchase_date: dt.date,
    sbm: Annotated[BondMaker, Depends(sbm)],
):
    locale = validated_locale(locale)
    path_suffix = f"/bond/{name}/{purchase_date}"

    try:
        bond = sbm(name, purchase_date)
    except ValueError as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "t": load_translations(locale),
                "locale": locale,
                "path_suffix": "/",
                "error": str(e),
            },
            status_code=404,
        )

    try:
        current_value = bond.current_value
    except (KeyError, Exception):
        current_value = None

    cash_flow = bond.cash_flow.reset_index().to_dict("records")

    return templates.TemplateResponse(
        "bond_detail.html",
        {
            "request": request,
            "t": load_translations(locale),
            "locale": locale,
            "path_suffix": path_suffix,
            "bond": bond,
            "current_value": current_value,
            "cash_flow": cash_flow,
        },
    )


# ── JSON API ──────────────────────────────────────────────────────────────────

@app.get("/bonds")
async def list_bonds(sbm: Annotated[BondMaker, Depends(sbm)]) -> dict[str, list[str]]:
    """Return available bond series grouped by kind."""
    return {
        kind: sorted(df["Seria"].dropna().tolist())
        for kind, df in sbm.bond_info.items()
        if kind in BOND_TYPES and "Seria" in df.columns
    }


@app.get("/by_name/{name}/{purchase_date}")
async def bond_by_name(bond: Annotated[Bond, Depends(get_bond)]) -> Bond:
    """Return bond data by name."""
    return bond


@app.get("/by_name/{name}/{purchase_date}/daily_values")
async def daily_values(bond: Annotated[Bond, Depends(get_bond)]) -> list[dict]:
    """Return bond daily values."""
    return bond.daily_values.reset_index().to_dict("records")


@app.get("/by_name/{name}/{purchase_date}/daily_values/csv")
async def daily_values_csv(bond: Annotated[Bond, Depends(get_bond)]):
    """Return bond daily values as CSV."""
    return Response(
        content=(
            bond
            .daily_values
            .rename(columns={"value": "marketPrice"})
            .to_csv(index=True, sep=";")
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={bond.name}_{bond.purchase_date}_daily_values.csv"
        },
    )


@app.get("/by_name/{name}/{purchase_date}/cash_flow")
async def cash_flow(bond: Annotated[Bond, Depends(get_bond)]) -> list[dict]:
    """Return bond cash flow events."""
    return bond.cash_flow.reset_index().to_dict("records")
