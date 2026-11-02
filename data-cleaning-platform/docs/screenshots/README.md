# Ảnh chụp kiểm tra giao diện

Ảnh chụp từ Chrome với frontend chạy ở chế độ dữ liệu mẫu (`FRONTEND_MOCK=1`), nền sáng,
cửa sổ 1280px (ảnh `mobile` là 375px). Tên file: `<trang>__<trạng-thái>.png`.

Một số ảnh của các trang làm trước (Trang chủ ở mobile, Tải lên, Tổng quan dữ liệu, Mapping cột)
được chụp lại ở Giai đoạn 5 (kiểm tra tổng thể) để khớp giao diện cuối cùng.

## Đăng nhập / Đăng ký
| Ảnh | Nội dung |
|---|---|
| `dang-nhap__mac-dinh` | Form đăng nhập, banner dữ liệu mẫu kèm tài khoản thử |
| `dang-nhap__loi-form-trong` | Gửi form trống: danh sách lỗi kiểm tra phía giao diện |
| `dang-nhap__sai-mat-khau` | Sai mật khẩu: một câu chung, không lộ email có tồn tại |
| `dang-nhap__mobile` | Bố cục 375px |
| `dang-ky__loi-mat-khau-khong-khop` | Lỗi nhập lại mật khẩu |
| `dang-ky__thanh-cong-toast-trang-chu` | Đăng ký xong tự vào Trang chủ kèm toast |

## Trang chủ, Dashboard
| Ảnh | Nội dung |
|---|---|
| `trang-chu__mac-dinh` | Lời chào, trạng thái chưa có dữ liệu, 6 lối tắt quy trình |
| `dashboard__danh-sach-project` | KPI và lưới project |
| `dashboard__dialog-tao-project` / `...-loi-ten-trong` | Hộp thoại tạo project và lỗi tên trống |
| `dashboard__menu-them-doi-ten-xoa` | Menu đổi tên/xóa trong thẻ project |
| `dashboard__dialog-xac-nhan-xoa` / `dashboard__sau-khi-xoa` | Xác nhận xóa và kết quả |

## Tải lên
| Ảnh | Nội dung |
|---|---|
| `tai-len__mac-dinh-o-tai-file-tieng-viet` | Ô tải file đã Việt hóa bằng CSS |
| `tai-len__o-tai-file-khi-selector-hong-chu-goc-hien-lai` | Kiểm tra an toàn khi hỏng: chữ tiếng Anh gốc hiện lại |

## Gợi ý làm sạch
| Ảnh | Nội dung |
|---|---|
| `goi-y-lam-sach__chua-chon-dataset` | Chưa chọn dataset |
| `goi-y-lam-sach__rong-chua-co-goi-y` | Trạng thái rỗng, nút Sinh gợi ý |
| `goi-y-lam-sach__danh-sach-goi-y` | Danh sách thẻ gợi ý |
| `goi-y-lam-sach__da-duyet-chap-nhan-tu-choi` | Sau khi chấp nhận/từ chối |
| `goi-y-lam-sach__tab-ap-dung-chua-xem-truoc` | Tab áp dụng, nút áp dụng bị khóa |
| `goi-y-lam-sach__xem-truoc-thay-doi-theo-o` | Xem trước: danh sách thay đổi theo ô |
| `goi-y-lam-sach__xem-truoc-bang-sau-to-mau` | Xem trước: bảng sau, ô đổi được tô màu |
| `goi-y-lam-sach__dialog-xac-nhan-ap-dung` | Hộp thoại xác nhận áp dụng |
| `goi-y-lam-sach__sau-khi-ap-dung` | Banner kết quả, phiên bản mới |
| `goi-y-lam-sach__du-lieu-da-sach` | Không còn gợi ý nào |
| `goi-y-lam-sach__loi-may-chu` / `...-chi-tiet-ky-thuat` | Trạng thái lỗi thân thiện |
| `goi-y-lam-sach__khung-mapping-cong-tat` / `...mapping-trong-buoc-xem-truoc` | Bước đổi tên từ Mapping |
