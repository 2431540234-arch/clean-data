"""Truy vấn DB cho bảng projects. Lọc theo owner_id nếu người gọi không phải admin."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.project import Project
from app.models.user import User


def get_by_id(db: Session, project_id: int) -> Project | None:
    """Lấy project theo id, trả về None nếu không tồn tại."""
    return db.get(Project, project_id)


def list_for_user(db: Session, user: User) -> list[Project]:
    """Lấy danh sách project: admin thấy toàn bộ, user thường chỉ thấy project của mình."""
    stmt = select(Project).order_by(Project.created_at.desc(), Project.id.desc())
    if user.role != "admin":
        stmt = stmt.where(Project.owner_id == user.id)
    return list(db.scalars(stmt))


def dataset_counts(db: Session, project_ids: list[int]) -> dict[int, int]:
    """Số dataset của từng project (một truy vấn cho cả danh sách, tránh N+1)."""
    if not project_ids:
        return {}
    rows = db.execute(
        select(Dataset.project_id, func.count(Dataset.id))
        .where(Dataset.project_id.in_(project_ids))
        .group_by(Dataset.project_id)
    )
    return {project_id: count for project_id, count in rows}


def create_project(db: Session, name: str, owner_id: int, commit: bool = True) -> Project:
    """Tạo project mới thuộc owner_id."""
    project = Project(name=name, owner_id=owner_id)
    db.add(project)
    if commit:
        db.commit()
        db.refresh(project)
    else:
        db.flush()
    return project


def dataset_ids(db: Session, project_id: int) -> list[int]:
    """Id các dataset của project (để dọn file lưu trữ khi xóa project)."""
    return list(db.scalars(select(Dataset.id).where(Dataset.project_id == project_id)))


def delete_project(db: Session, project: Project, commit: bool = True) -> None:
    """Xóa project (cascade xóa dataset, version, rule liên quan theo quan hệ model)."""
    db.delete(project)
    if commit:
        db.commit()
    else:
        db.flush()
