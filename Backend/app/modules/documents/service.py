import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import ObjectStorage, StorageNotConfiguredError
from app.modules.documents.models import Document, DocumentStatus
from app.modules.documents.schemas import DocumentRequirementCreate, DocumentUploadInit
from app.modules.workforce.service import get_worker


class WorkerNotInTenantError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class InvalidDocumentStateError(Exception):
    pass


async def create_document_requirement(
    db: AsyncSession, tenant_id: uuid.UUID, payload: DocumentRequirementCreate
) -> Document:
    worker = await get_worker(db, tenant_id, payload.worker_id)
    if worker is None:
        raise WorkerNotInTenantError("worker_id does not belong to this tenant")

    document = Document(
        tenant_id=tenant_id,
        worker_id=payload.worker_id,
        document_type=payload.document_type,
        status=DocumentStatus.REQUIRED,
        expires_on=payload.expires_on,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def get_document(db: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            Document.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def list_documents_for_worker(
    db: AsyncSession, tenant_id: uuid.UUID, worker_id: uuid.UUID
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(
            Document.tenant_id == tenant_id,
            Document.worker_id == worker_id,
            Document.is_deleted == False,  # noqa: E712
        )
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def init_upload(
    db: AsyncSession,
    storage: ObjectStorage,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: DocumentUploadInit,
) -> tuple[str, str, int]:
    document = await get_document(db, tenant_id, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document {document_id} not found")

    if document.status not in (DocumentStatus.REQUIRED, DocumentStatus.REJECTED):
        raise InvalidDocumentStateError(
            f"Cannot upload to a document in status {document.status}"
        )

    storage_key = (
        f"tenants/{tenant_id}/workers/{document.worker_id}/documents/"
        f"{document_id}/v{document.version + 1}/{payload.file_name}"
    )

    expires_in = 300
    try:
        upload_url = storage.generate_upload_url(
            key=storage_key, content_type=payload.content_type, expires_seconds=expires_in
        )
    except StorageNotConfiguredError:
        raise

    return upload_url, storage_key, expires_in


async def confirm_upload(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    storage_key: str,
    file_name: str,
    content_type: str,
    file_size_bytes: int,
) -> Document:
    document = await get_document(db, tenant_id, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document {document_id} not found")

    document.storage_key = storage_key
    document.file_name = file_name
    document.content_type = content_type
    document.file_size_bytes = file_size_bytes
    document.version += 1
    document.status = DocumentStatus.UPLOADED

    await db.commit()
    await db.refresh(document)
    return document


async def review_document(
    db: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID, new_status: DocumentStatus
) -> Document:
    if new_status not in (DocumentStatus.VERIFIED, DocumentStatus.REJECTED):
        raise InvalidDocumentStateError("Review status must be VERIFIED or REJECTED")

    document = await get_document(db, tenant_id, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document {document_id} not found")

    if document.status != DocumentStatus.UPLOADED:
        raise InvalidDocumentStateError(
            f"Cannot review a document in status {document.status}; must be UPLOADED"
        )

    document.status = new_status
    await db.commit()
    await db.refresh(document)
    return document
