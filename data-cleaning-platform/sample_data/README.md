# Dữ liệu demo

File `khach_hang_ban.csv` (và bản Excel `khach_hang_ban.xlsx` sinh từ cùng dữ liệu) chứa
30 dòng dữ liệu khách hàng tiếng Việt với các lỗi được **cài sẵn có chủ đích**, dùng để demo
tính năng phát hiện lỗi và làm sạch dữ liệu:

| Loại lỗi | Vị trí / ví dụ |
|---|---|
| Trùng dòng tuyệt đối | Dòng "Tran Thi Binh" xuất hiện 2 lần giống hệt nhau |
| Thiếu dữ liệu | Nhiều ô trống ở cột `email`, `so_dien_thoai`, `ngay_sinh`, `tuoi`, `tinh_thanh` |
| Ngày lẫn định dạng | Cột `ngay_sinh` lẫn cả `dd/mm/yyyy` (ví dụ `15/04/1990`) và `yyyy-mm-dd` (ví dụ `1995-03-12`) |
| Số điện thoại nhiều kiểu | `0901234567`, `0912 345 678`, `+84 933 445 566`, `090-555-1234` |
| Email không nhất quán | Viết hoa (`BUITHIHOA@GMAIL.COM`), thừa khoảng trắng (` TranThiBinh@GMAIL.com `), sai cú pháp (`tranvanchinh@invalid-email`) |
| Tên tỉnh/thành không nhất quán | `HCM` / `TP.HCM` / `TPHCM` / `TP. Hồ Chí Minh` / `Hồ Chí Minh` đều là một nơi |
| Outlier tuổi | `150` (dòng "Dao Van Phuc"), `-5` (dòng "Vu Van Dat") |
| Giá trị null-token | Ô ghi `"N/A"`, `"-"` thay vì để trống |

Dữ liệu này cố ý "bẩn" để minh họa khả năng phát hiện và gợi ý làm sạch của hệ thống,
không phản ánh dữ liệu khách hàng thật.

File `nhan_su_ban.xlsx`: TODO — hiện đang dùng tạm cùng cấu trúc dữ liệu như
`khach_hang_ban.csv` (sinh bằng pandas), cần thay bằng dữ liệu nhân sự riêng nếu muốn
tách biệt 2 bộ demo.
