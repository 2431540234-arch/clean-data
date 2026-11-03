"""Truy cập tài nguyên có kiểm tra quyền sở hữu: MỌI router phải lấy dữ liệu qua các hàm này.

Quy ước: tài nguyên không tồn tại -> 404; tồn tại nhưng không thuộc về user (và user không phải
admin) -> 403. Quyền của dataset/version/gợi ý đều suy ra từ project cha.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.permissions import ensure_can_access_project
from app.models.dataset import Dataset, DatasetVersion
from app.models.project import Project
from app.models.suggestion import Suggestion
from app.models.user import User


def get_owned_project(db: Session, user: User, project_id: int) -> Project:
    """Lấy project mà user được phép truy cập."""
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Không tìm thấy dự án.")
    ensure_can_access_project(user, project)
    return project


def get_owned_dataset(db: Session, user: User, dataset_id: int) -> Dataset:
    """Lấy dataset mà user được phép truy cập (qua project của nó)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise NotFoundError("Không tìm thấy dataset.")
    ensure_can_access_project(user, dataset.project)
    return dataset


def get_owned_version(db: Session, user: User, version_id: int) -> DatasetVersion:
    """Lấy phiên bản dataset mà user được phép truy cập (qua dataset -> project)."""
    version = db.get(DatasetVersion, version_id)
    if version is None:
        raise NotFoundError("Không tìm thấy phiên bản dữ liệu.")
    ensure_can_access_project(user, version.dataset.project)
    return version


def get_owned_suggestion(db: Session, user: User, suggestion_id: int) -> Suggestion:
    """Lấy gợi ý mà user được phép truy cập (qua version -> dataset -> project)."""
    suggestion = db.get(Suggestion, suggestion_id)
    if suggestion is None:
        raise NotFoundError("Không tìm thấy gợi ý.")
    ensure_can_access_project(user, suggestion.version.dataset.project)
    return suggestion
