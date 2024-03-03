import uvicorn


def start() -> None:
    """Start the server."""
    uvicorn.run("malloc.polish_bond_site.main:app", reload=True)