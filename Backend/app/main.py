from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.modules.identity.router import router as identity_router
from app.modules.tenant.router import router as tenant_router

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

register_exception_handlers(app)

app.include_router(tenant_router, prefix=settings.API_V1_PREFIX)
app.include_router(identity_router, prefix=settings.API_V1_PREFIX)


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME, "environment": settings.ENVIRONMENT}
