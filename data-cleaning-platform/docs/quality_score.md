# Công thức tính điểm chất lượng dữ liệu (Data Quality Score)

> TODO: hoàn thiện công thức và ví dụ minh họa. Cài đặt tại `backend/app/services/quality.py`.

## 1. Bốn tiêu chí thành phần

| Tiêu chí | Trọng số | Ý nghĩa |
|---|---|---|
| Completeness (đầy đủ) | 0.3 | Tỉ lệ dữ liệu không bị thiếu (null/empty/null-token) |
| Uniqueness (duy nhất) | 0.2 | Tỉ lệ dòng không bị trùng lặp |
| Validity (hợp lệ) | 0.3 | Tỉ lệ giá trị đúng định dạng mong đợi (email, phone, date...) |
| Consistency (nhất quán) | 0.2 | Tỉ lệ giá trị không bị biến thể khác nhau cho cùng một ý nghĩa |

## 2. Công thức tổng hợp

```
score = 100 * (
    0.3 * completeness +
    0.2 * uniqueness +
    0.3 * validity +
    0.2 * consistency
)
```

Mỗi thành phần nằm trong khoảng [0, 1].

## 3. TODO

- Công thức chi tiết tính từng thành phần (completeness/uniqueness/validity/consistency)
  dựa trên kết quả của `app.services.profiling` và `app.services.detectors`.
- Ví dụ tính tay trên `sample_data/khach_hang_ban.csv`.
- Cách lưu/cache kết quả vào bảng `quality_reports`.
