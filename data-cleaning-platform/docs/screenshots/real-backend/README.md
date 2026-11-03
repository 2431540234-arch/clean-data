# Ảnh chụp giao diện thật (backend thật, không mock)

Chụp ngày 04/11/2026 từ Chromium (1280 x 900) với **Streamlit thật nói chuyện với backend FastAPI thật và
PostgreSQL thật** (`FRONTEND_MOCK` không đặt). Dữ liệu: `sample_data/khach_hang_ban.csv` cho phần gợi ý làm sạch,
`sample_data/khach_hang_tieu_de_khac.csv` cho phần mapping cột. Tên file: `<số thứ tự>-<trang>-<trạng thái>.png`.

| Ảnh | Nội dung |
|---|---|
| `01-dang-nhap` | Trang đăng nhập (không còn banner dữ liệu mẫu) |
| `02-trang-chu`, `03-dashboard-seed` | Trang chủ và Dashboard với dữ liệu nạp bằng `seed.py` |
| `04-dialog-tao-project`, `05-dashboard-sau-khi-tao` | Tạo project |
| `06-tai-len-ket-qua` | Tải `khach_hang_ban.csv`: 30 dòng, 6 cột, mã hóa utf-8, 20 dòng xem trước |
| `07-tong-quan-thong-ke` | Thống kê cột, điểm chất lượng 90,5 / 100 |
| `08-tong-quan-loi-da-phat-hien` | Tab **Lỗi đã phát hiện**: 13 nhóm lỗi theo mức độ (Cao/Trung bình/Thấp) |
| `09-tong-quan-bieu-do` | Biểu đồ tỉ lệ thiếu, kiểu dữ liệu, lỗi theo mức độ, phân bố giá trị cột |
| `10-goi-y-danh-sach-theo-muc-do` | 10 gợi ý, thẻ có viền và nhãn màu theo mức độ nghiêm trọng của lỗi |
| `11-goi-y-da-chap-nhan-tat-ca` | Sau khi chấp nhận tất cả gợi ý |
| `12-goi-y-xem-truoc-thay-doi`, `13-goi-y-hop-thoai-xac-nhan` | Xem trước theo từng ô và hộp thoại xác nhận áp dụng |
| `14-goi-y-sau-khi-ap-dung` | Sau khi áp dụng: phiên bản 2 |
| `15-lich-su-phien-ban` | Lịch sử phiên bản (undo/redo/khôi phục) |
| `16-tong-quan-sau-khi-lam-sach` | 29 dòng, điểm chất lượng 98,4 / 100 |
| `17-xuat-du-lieu` | Xuất CSV và Excel kèm báo cáo chất lượng |
| `18-dashboard-co-diem-chat-luong` | Dashboard: Số dataset, Điểm chất lượng TB |
| `19-nhat-ky-hoat-dong` | Nhật ký của chính người dùng (nhãn tiếng Việt cho mã mới) |
| `20-tai-khoan` | Trang Tài khoản |
| `21-mapping-tai-len-file-tieu-de-khac` | Tải `khach_hang_tieu_de_khac.csv` (tiêu đề tiếng Việt) |
| `22-mapping-goi-y-tu-dong`, `23-mapping-sau-khi-xac-nhan` | Gợi ý mapping tự động và xác nhận |
| `24-tai-khoan-doi-mat-khau-thanh-cong`, `25-dashboard-sau-khi-doi-mat-khau` | Đổi mật khẩu: ở lại trang, token mới vẫn dùng được |
| `26-admin-danh-sach-nguoi-dung`, `27-admin-thong-ke-he-thong` | Quản trị người dùng, thống kê hệ thống |
| `28-admin-nhat-ky-toan-he-thong` | Nhật ký toàn hệ thống (admin) |
