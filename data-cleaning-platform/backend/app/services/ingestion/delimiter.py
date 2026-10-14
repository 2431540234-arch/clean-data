"""Dò dấu phân cách (delimiter) của file CSV: ',', ';', '\\t', '|'."""


def detect_delimiter(sample_text: str) -> str:
    """Trả về delimiter khả năng cao nhất dựa trên một đoạn mẫu của file CSV.

    Gợi ý cách làm: dùng csv.Sniffer().sniff(sample_text, delimiters=",;\\t|")
    và bắt lỗi csv.Error để fallback về ",".
    """
    raise NotImplementedError("TODO: dùng csv.Sniffer để dò delimiter, fallback ','.")
