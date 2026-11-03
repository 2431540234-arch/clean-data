"""API gợi ý mapping tên cột (fuzzy matching tầng 1, AI tầng 2)."""

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.exceptions import ValidationAppError
from app.models.user import User
from app.services import access
from app.services.frames import load_version_columns
from app.services.mapping.matcher import match_columns

router = APIRouter(prefix="/mapping", tags=["mapping"])

MAX_TARGET_COLUMNS = 500
MAX_COLUMN_NAME_LENGTH = 255


@router.post("/{version_id}/suggest")
def suggest_mapping(
    version_id: int,
    target_schema: list[str] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    """Gợi ý mapping tên cột của dataset version với target_schema.

    Body là một mảng JSON các tên cột chuẩn. Kết quả: mọi cột nguồn (đúng thứ tự) -> tên cột
    chuẩn hoặc null nếu không khớp.
    """
    version = access.get_owned_version(db, current_user, version_id)
    schema = [name.strip() for name in target_schema if name.strip()]
    if len(schema) != len(target_schema):
        raise ValidationAppError("Tên cột chuẩn không được để trống.")
    if len(schema) > MAX_TARGET_COLUMNS or any(len(n) > MAX_COLUMN_NAME_LENGTH for n in schema):
        raise ValidationAppError("Danh sách cột chuẩn quá dài.")
    return match_columns(load_version_columns(version), schema)
