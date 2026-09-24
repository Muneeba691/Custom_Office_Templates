import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import TenantContext, get_current_context, require_roles
from app.core.storage import StorageNotConfiguredError, get_storage
from app.modules.documents.schemas import (
    DocumentOut,
    DocumentRequirementCreate,
    DocumentReview,
    DocumentUploadInit,
    DocumentUploadInitOut,
)
from app.modules.documents.service import (
    DocumentNotFoundError,
    InvalidDocumentStateError,
    WorkerNotInTenantError,
    confirm_upload,
    create_document_requirement,
    get_document,
    init_upload,
    list_documents_for_worker,
    review_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])

WRITE_ROLES = ("OWNER", "ADMIN", "HR")
REVIEW_ROLES = ("OWNER", "ADMIN", "HR", "COMPLIANCE")


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def create_requirement_endpoint(
    payload: DocumentRequirementCreate,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        document = await create_document_requirement(db, ctx.tenant_id, payload)
    except WorkerNotInTenantError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_WORKER", "message": str(exc)}},
        )
    return document


@router.get("/worker/{worker_id}", response_model=list[DocumentOut])
async def list_worker_documents_endpoint(
    worker_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    return await list_documents_for_worker(db, ctx.tenant_id, worker_id)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document_endpoint(
    document_id: uuid.UUID,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    document = await get_document(db, ctx.tenant_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"}},
        )
    return document


@router.post("/{document_id}/upload-init", response_model=DocumentUploadInitOut)
async def init_upload_endpoint(
    document_id: uuid.UUID,
    payload: DocumentUploadInit,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    storage = get_storage()
    try:
        upload_url, storage_key, expires_in = await init_upload(
            db, storage, ctx.tenant_id, document_id, payload
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"}},
        )
    except InvalidDocumentStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_STATE", "message": str(exc)}},
        )
    except StorageNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"error": {"code": "STORAGE_NOT_CONFIGURED", "message": str(exc)}},
        )
    return DocumentUploadInitOut(
        upload_url=upload_url, storage_key=storage_key, expires_in_seconds=expires_in
    )


@router.post("/{document_id}/upload-confirm", response_model=DocumentOut)
async def confirm_upload_endpoint(
    document_id: uuid.UUID,
    storage_key: str,
    payload: DocumentUploadInit,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        document = await confirm_upload(
            db, ctx.tenant_id, document_id,
            storage_key=storage_key,
            file_name=payload.file_name,
            content_type=payload.content_type,
            file_size_bytes=payload.file_size_bytes,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"}},
        )
    return document


@router.post(
    "/{document_id}/review",
    response_model=DocumentOut,
    dependencies=[Depends(require_roles(*REVIEW_ROLES))],
)
async def review_document_endpoint(
    document_id: uuid.UUID,
    payload: DocumentReview,
    ctx: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        document = await review_document(db, ctx.tenant_id, document_id, payload.status)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"}},
        )
    except InvalidDocumentStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_STATE", "message": str(exc)}},
        )
    return document
