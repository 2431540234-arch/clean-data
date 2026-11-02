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

## Lịch sử phiên bản
| Ảnh | Nội dung |
|---|---|
| `lich-su-phien-ban__chi-co-ban-goc` | Dataset chỉ có bản gốc: trạng thái rỗng, Hoàn tác/Làm lại bị khóa |
| `lich-su-phien-ban__danh-sach-phien-ban` | Timeline từ mới đến cũ, nhãn Hiện tại/Bản gốc, thay đổi dòng/cột |
| `lich-su-phien-ban__sau-hoan-tac-co-the-lam-lai` | Sau Hoàn tác: nút Làm lại mở khóa |
| `lich-su-phien-ban__dialog-xac-nhan-khoi-phuc` | Hộp thoại xác nhận khôi phục |
| `lich-su-phien-ban__sau-khoi-phuc` | Sau khi khôi phục |
| `lich-su-phien-ban__loi-may-chu-khi-hoan-tac` | Lỗi máy chủ khi hoàn tác (thân thiện, không traceback) |

## Xuất dữ liệu
| Ảnh | Nội dung |
|---|---|
| `xuat-du-lieu__ban-goc-chua-tao-tep` | Gauge và 4 tiêu chí thành phần, nhắc đang xuất bản gốc |
| `xuat-du-lieu__sau-khi-tao-tep-co-nut-tai` | Sau khi tạo tệp CSV và Excel: hiện nút Tải xuống kèm dung lượng |
| `xuat-du-lieu__phien-ban-da-lam-sach` | Phiên bản 2: điểm chất lượng tăng (90,7 → 98,0) |
| `xuat-du-lieu__loi-diem-chat-luong-va-xuat-csv` | Lỗi điểm chất lượng và lỗi tạo CSV: trang vẫn dùng được |
| `xuat-du-lieu__mobile` | Bố cục 375px |

## Nhật ký hoạt động
| Ảnh | Nội dung |
|---|---|
| `nhat-ky__danh-sach-cua-toi` | Nhật ký của chính mình, mới nhất trước, bộ lọc hành động/ngày |
| `nhat-ky__loc-theo-hanh-dong` | Lọc theo hành động (chip màu chính) |
| `nhat-ky__chi-tiet-truoc-sau` | Chi tiết một bản ghi: trạng thái trước/sau (JSON) |
| `nhat-ky__admin-chi-xem-cua-minh` / `nhat-ky__admin-toan-he-thong` | Admin: công tắc "Xem toàn hệ thống", thêm cột người thực hiện |
| `nhat-ky__chua-co-hoat-dong` | Tài khoản mới chưa có hoạt động |
| `nhat-ky__loi-may-chu` | Lỗi máy chủ thân thiện |

## Tài khoản
| Ảnh | Nội dung |
|---|---|
| `tai-khoan__ho-so-va-doi-mat-khau` | Hồ sơ và form đổi mật khẩu |
| `tai-khoan__loi-kiem-tra-form` | Mật khẩu nhập lại không khớp |
| `tai-khoan__sai-mat-khau-hien-tai` | Backend từ chối mật khẩu cũ |
| `tai-khoan__doi-thanh-cong` | Đổi thành công (toast, vẫn đăng nhập) |
| `tai-khoan__mobile` | Bố cục 375px |

## Quản trị người dùng
| Ảnh | Nội dung |
|---|---|
| `quan-tri-nguoi-dung__danh-sach` | KPI, tìm kiếm, bộ lọc quyền/trạng thái, bảng người dùng |
| `quan-tri-nguoi-dung__tim-kiem` | Tìm theo tên/email |
| `quan-tri-nguoi-dung__khung-quan-ly` | Khung quản lý: đổi quyền, khóa/mở khóa, đặt lại mật khẩu |
| `quan-tri-nguoi-dung__dialog-xac-nhan-khoa` / `...__sau-khi-khoa` | Xác nhận khóa và kết quả (KPI "Đã khóa") |
| `quan-tri-nguoi-dung__mat-khau-tam-hien-mot-lan` | Mật khẩu tạm sau khi đặt lại, hiển thị một lần |
| `quan-tri-nguoi-dung__tu-quan-ly-bi-chan` | Admin không tự khóa/hạ quyền chính mình |
| `quan-tri-nguoi-dung__loi-may-chu` | Lỗi máy chủ thân thiện |

## Thống kê hệ thống
| Ảnh | Nội dung |
|---|---|
| `thong-ke-he-thong__tong-quan` | 6 chỉ số, 2 biểu đồ vành khuyên, gauge điểm chất lượng TB |
| `thong-ke-he-thong__mobile` | Bố cục 375px |
| `thong-ke-he-thong__loi-may-chu` | Lỗi máy chủ thân thiện |

## Responsive (`responsive/`)
Ảnh 12 trang ở 768px (`<trang>__768.png`) và 375px (`<trang>__375.png`), chụp trong phiên admin
sau khi đã chọn dataset (Mapping đã có bảng gợi ý, Gợi ý làm sạch đã sinh gợi ý, Xuất dữ liệu đã tạo
tệp CSV). Kết quả quét tự động: không trang nào tràn ngang ở 1280/768/375px và không có chữ hay
placeholder nào dưới tương phản 4,5:1.
