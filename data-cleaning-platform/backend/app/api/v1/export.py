"""API xuất dữ liệu đã làm sạch ra CSV/Excel kèm báo cáo chất lượng."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{version_id}/csv")
def export_csv(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Xuất dữ liệu của một phiên bản dataset ra file CSV (UTF-8-BOM)."""
    raise NotImplementedError(
        "TODO: dùng app.services.export.export_to_csv_bytes, trả StreamingResponse."
    )


@router.get("/{version_id}/excel")
def export_excel(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Xuất dữ liệu kèm báo cáo chất lượng ra file Excel nhiều sheet."""
    raise NotImplementedError(
        "TODO: dùng app.services.export.export_to_excel_bytes + app.services.report."
    )
