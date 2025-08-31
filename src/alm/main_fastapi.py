from __future__ import annotations

import asyncio
import importlib
import os
import pkgutil
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Ansible Logs Monitoring API", version="0.1.0")

    _include_route_modules(app)

    @app.get("/", tags=["meta"])
    async def read_root() -> dict[str, str]:
        return {"service": "alm", "status": "ok"}

    return app


def _include_route_modules(app: FastAPI) -> None:
    """Dynamically discover and include routers from the `routes` package.

    A module is included if it defines a module-level variable named `router`
    that is an instance of `fastapi.APIRouter`.
    """
    current_dir = Path(__file__)
    routes_dir = current_dir.parent / "routes"

    if not routes_dir.exists():
        return

    # Determine the importable package name for routes based on this module's package
    package_name: Optional[str] = __package__
    if not package_name:
        # Fallback to `alm` if __package__ is not set when run as a script
        package_name = "alm"

    routes_package = f"{package_name}.routes"

    for module_info in pkgutil.iter_modules([str(routes_dir)]):
        module_name = f"{routes_package}.{module_info.name}"
        module = importlib.import_module(module_name)
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            app.include_router(router)


app = create_app()


def run_db():
    import uvicorn

    # Run with: python -m uvicorn alm.main_fastapi:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run_db()
