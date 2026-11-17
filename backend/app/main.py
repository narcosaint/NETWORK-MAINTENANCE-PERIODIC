from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import build_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = build_engine()
    try:
        yield
    finally:
        app.state.engine.dispose()


app = FastAPI(title="Hotel Maintenance API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db", responses={503: {"description": "Database unavailable"}})
def database_health(request: Request):
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}


from app.api import router
app.include_router(router)


# Same-origin UI: API tokens stay in browser memory, no CORS or public proxy.
web_directory = Path(__file__).resolve().parent / 'web'
app.mount('/assets', StaticFiles(directory=web_directory), name='web-assets')


@app.get('/', include_in_schema=False)
def web_home():
    return FileResponse(web_directory / 'index.html', headers={'Cache-Control': 'no-store'})


@app.middleware('http')
async def web_security_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path == '/' or request.url.path.startswith('/assets/'):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
    return response

from app.hotel_api import router as hotel_router
app.include_router(hotel_router)

from app.speedtest_api import router as speedtest_router
app.include_router(speedtest_router)

from app.sampling_api import router as sampling_router
app.include_router(sampling_router)

from app.sampling_coverage_api import router as coverage_router
app.include_router(coverage_router)

from app.sampling_observation_api import router as observation_router
app.include_router(observation_router)
