"""Script nạp dữ liệu demo: user mẫu, project mẫu, dataset mẫu từ sample_data/.

Cách dùng:
    python scripts/seed_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    """Nạp user demo, project demo và upload sẵn sample_data/khach_hang_ban.csv.

    Gợi ý cách làm: tạo 1 user thường (demo@example.com), 1 project "Demo", đọc file
    sample_data/khach_hang_ban.csv bằng app.services.ingestion.reader, lưu thành dataset
    + version đầu tiên qua app.repositories.dataset_repo + app.services.storage.
    """
    raise NotImplementedError("TODO: nạp user/project/dataset demo từ sample_data/.")


if __name__ == "__main__":
    main()
