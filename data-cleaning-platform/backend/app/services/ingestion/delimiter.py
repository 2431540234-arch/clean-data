"""Dò dấu phân cách (delimiter) của file CSV: ',', ';', '\\t', '|'."""

import csv
import io
from collections import Counter

_CANDIDATES = [",", ";", "\t", "|"]


def detect_delimiter(sample_text: str) -> str:
    """Trả về delimiter khả năng cao nhất dựa trên một đoạn mẫu của file CSV.

    Với mỗi ứng viên, đếm số cột của từng dòng (tôn trọng dấu ngoặc kép). Ứng viên tốt là
    ứng viên cho nhiều cột và số cột ổn định giữa các dòng. Không dùng csv.Sniffer vì nó hay
    nhầm khi dữ liệu có dấu chấm câu. Hòa thì ưu tiên ','.
    """
    lines = [line for line in sample_text.splitlines() if line.strip()][:50]
    if not lines:
        return ","
    joined = "\n".join(lines)
    best, best_score = ",", 0.0
    for delimiter in _CANDIDATES:
        try:
            counts = [len(row) for row in csv.reader(io.StringIO(joined), delimiter=delimiter)]
        except csv.Error:
            continue
        if not counts:
            continue
        mode, freq = Counter(counts).most_common(1)[0]
        if mode < 2:
            continue
        score = (freq / len(counts)) * mode
        if score > best_score:
            best, best_score = delimiter, score
    return best
