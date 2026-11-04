"""Load recent dataset details for dashboard-style views."""

from typing import Any

from api_client import APIError, get_quality, list_dataset_versions, list_project_datasets
from components.ui import safe_call

_MAX_RECENT_DATASETS = 10


def project_dataset_summaries(
    token: str, project_id: int
) -> tuple[list[dict[str, Any]] | None, APIError | None]:
    datasets, error = safe_call("Đang tải dataset…", list_project_datasets, token, project_id)
    if error is not None:
        return None, error

    summaries = []
    for dataset in datasets[:_MAX_RECENT_DATASETS]:
        current_version_id = dataset.get("current_version_id")
        versions, error = safe_call(
            "Đang tải phiên bản…", list_dataset_versions, token, dataset["id"]
        )
        if error is not None:
            return None, error

        version = next((item for item in versions if item["id"] == current_version_id), None)
        if version is None:
            return None, APIError(
                502, f"Không tìm thấy phiên bản hiện tại của dataset #{dataset['id']}."
            )

        quality, error = safe_call("Đang tải điểm chất lượng…", get_quality, token, version["id"])
        if error is not None:
            return None, error
        summaries.append({"dataset": dataset, "version": version, "quality": quality})

    return summaries, None
