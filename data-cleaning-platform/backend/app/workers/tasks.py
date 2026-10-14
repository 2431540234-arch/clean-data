"""Các tác vụ nền xử lý file lớn (profiling, phát hiện lỗi) để không block request HTTP."""


def process_large_dataset_async(dataset_version_id: int) -> None:
    """Chạy profiling + detectors cho một dataset lớn ở background.

    Gợi ý cách làm: dùng FastAPI BackgroundTasks cho tác vụ ngắn, hoặc một task queue
    (ví dụ Celery/RQ) cho tác vụ dài; cập nhật kết quả vào DB khi hoàn tất để frontend
    poll trạng thái.
    """
    raise NotImplementedError(
        "TODO: chạy profiling/detectors ở background cho dataset_version_id, lưu kết quả vào DB."
    )
