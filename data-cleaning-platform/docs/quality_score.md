# Công thức tính điểm chất lượng dữ liệu (Data Quality Score)

Cài đặt tại `backend/app/services/quality.py`. Điểm được tính trên **một phiên bản** của dataset.

## 1. Bốn tiêu chí thành phần

| Tiêu chí | Trọng số | Ý nghĩa |
|---|---|---|
| Completeness (đầy đủ) | 0.3 | Tỉ lệ dữ liệu không bị thiếu (null/empty/null-token) |
| Uniqueness (duy nhất) | 0.2 | Tỉ lệ dòng không bị trùng lặp |
| Validity (hợp lệ) | 0.3 | Tỉ lệ giá trị đúng định dạng mong đợi (email, phone, date, số) |
| Consistency (nhất quán) | 0.2 | Tỉ lệ giá trị không bị viết theo nhiều kiểu khác nhau |

## 2. Công thức tổng hợp

```
score = 100 * (
    0.3 * completeness +
    0.2 * uniqueness +
    0.3 * validity +
    0.2 * consistency
)
```

Mỗi thành phần nằm trong khoảng [0, 1]; `overall_score` nằm trong [0, 100], làm tròn 1 chữ số
thập phân (thành phần làm tròn 4 chữ số). API trả đúng các giá trị này (`QualityReportOut`).

## 3. Cách tính từng thành phần

Mọi tỉ lệ có dạng `1 - xấu / tổng`, kẹp trong [0, 1]; nếu `tổng = 0` (không có gì để kiểm tra)
thì thành phần bằng 1.

| Thành phần | `xấu` | `tổng` |
|---|---|---|
| completeness | số ô thiếu (ô trống, chỉ có khoảng trắng, hoặc null-token trong `app/data/null_tokens.json` như `N/A`, `-`, `null`) | số dòng × số cột |
| uniqueness | số dòng trùng hoàn toàn với một dòng đứng trước (bản đầu tiên không tính) | số dòng |
| validity | số ô **khác nhau** (cột, dòng) bị lỗi: email sai cú pháp, SĐT không hợp lệ (phonenumbers, vùng VN), ngày không có thật, chữ trong cột số, giá trị bất thường theo IQR (1,5 × IQR) | số ô không thiếu của các cột kiểu email, phone, date, integer, float |
| consistency | số ô **khác nhau** thuộc nhóm không nhất quán: ngày/SĐT viết lẫn kiểu (tính các ô thuộc kiểu ít gặp), email thừa khoảng trắng hoặc viết hoa, văn bản thừa khoảng trắng, hoa/thường lộn xộn, nhiều cách viết cho cùng một giá trị | số ô không thiếu của các cột kiểu text, email, phone, date |

Một ô bị nhiều lỗi cùng nhóm chỉ bị trừ một lần. Trùng gần đúng (fuzzy) được báo ở danh sách lỗi
nhưng không trừ điểm, vì cần người xác nhận.

## 4. Ví dụ tính tay trên `sample_data/khach_hang_ban.csv`

File có 30 dòng, 6 cột (180 ô).

- Đầy đủ: 12 ô thiếu → `1 - 12/180 = 0,9333`.
- Duy nhất: 1 dòng trùng (dòng "Tran Thi Binh" lặp lại) → `1 - 1/30 = 0,9667`.
- Hợp lệ: các cột có định dạng (email 29 ô, SĐT 28, ngày 27, tuổi 26) có 110 ô không thiếu; 3 ô lỗi
  (1 email `tranvanchinh@invalid-email`, 2 tuổi bất thường 150 và -5) → `1 - 3/110 = 0,9727`.
- Nhất quán: các cột chữ/email/SĐT/ngày có 30 + 29 + 28 + 27 + 28 = 142 ô không thiếu; 43 ô viết khác
  chuẩn (13 ngày sai kiểu, 7 SĐT sai kiểu, 5 email thừa khoảng trắng/hoa, các cách viết khác nhau của
  tỉnh/thành...) → `1 - 43/142 = 0,6972`.

```
score = 100 * (0,3*0,9333 + 0,2*0,9667 + 0,3*0,9727 + 0,2*0,6972) = 90,5
```

Sau khi áp dụng các gợi ý làm sạch (xóa dòng trùng, chuẩn hóa ngày/SĐT/email/tỉnh thành...) điểm
tăng rõ rệt (có kiểm thử tự động: `test_cleaning_improves_quality_score`).

## 5. Lưu và cache

- Bảng `quality_reports` có tối đa một dòng cho mỗi phiên bản (`version_id` UNIQUE).
- Phiên bản dữ liệu không bao giờ đổi, nên điểm chỉ tính **một lần**: khi chạy profiling (đã có sẵn kết
  quả detector) hoặc lần đầu gọi `GET /quality/{version_id}`; các lần sau đọc lại từ DB.
- `GET /projects` chỉ tính điểm trung bình trên các phiên bản **hiện tại** đã có báo cáo; project
  chưa có báo cáo nào trả `null` (frontend ẩn chỉ số).
- Lưu ý: ràng buộc CHECK trong DB cho phép 0..100 cho cả bốn thành phần; ta lưu 0..1 (nằm trong khoảng
  đó) để khớp hợp đồng với frontend.
