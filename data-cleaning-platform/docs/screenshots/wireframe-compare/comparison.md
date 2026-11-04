# Đối chiếu wireframe — Bước 2

Ảnh `compare-*.png` đặt giao diện ứng dụng cạnh wireframe theo cùng kích thước viewport. Ảnh app là ảnh chụp giao diện Streamlit; ảnh wireframe desktop là tham chiếu từ [HTML gốc](../../design/wireframe-dataclean.html), với bản PDF tại [wireframe-dataclean.pdf](../../design/wireframe-dataclean.pdf).

| Trang / viewport | Khác biệt quan sát được | Lý do |
|---|---|---|
| Header admin · 1440×1000 | Đủ 7 mục menu trên cùng một hàng, không cuộn; ảnh chụp: [`admin-menu-1440.png`](./admin-menu-1440.png). | Menu dùng hết chiều rộng khả dụng ở desktop; nhãn không bị cắt. |
| Header admin · 1280×1000 | Đủ 7 mục menu trên cùng một hàng, không cuộn. | Cùng bố cục desktop; chỉ bật cuộn ngang tại viewport rộng tối đa 768px. |
| Header admin · 375×812 | Menu cuộn ngang, không xếp thành danh sách dọc; ảnh chụp: [`admin-menu-375.png`](./admin-menu-375.png). | Giữ chiều rộng tối thiểu cho từng mục ở màn hình hẹp; nội dung trang không tràn ngang. |
| Làm sạch · 1440×900 | Wireframe dùng nội dung minh họa và có một số bảng/chỉ số cụ thể; ứng dụng hiển thị dữ liệu và trạng thái phiên làm việc thực tế. Bố cục ứng dụng dùng hai cột cân bằng. | Không lấy số liệu minh họa trong wireframe làm dữ liệu; các tab nguồn và hàng đợi dùng widget Streamlit thật theo quyết định đã chốt. |
| Làm sạch · 375×812 | Menu và stepper của ứng dụng tự xuống dòng; nội dung trang tiếp tục cuộn dọc. Wireframe bên cạnh là crop 375×812 từ wireframe desktop 1440px, không phải thiết kế mobile. | Wireframe không cung cấp biến thể mobile; crop chỉ cho biết phần nội dung desktop nằm trong vùng nhìn hẹp, không dùng làm chuẩn responsive. |
| Thư viện quy tắc · 1440×900 | Wireframe đặt danh sách và trình soạn cạnh nhau; ứng dụng đặt một trình soạn dùng chung bên dưới hai tab quy tắc. | Trình soạn được dùng chung thay vì nhân đôi trong mỗi tab; hai tab riêng là yêu cầu bắt buộc. Quy tắc dự án được nạp vào trình soạn rồi lưu thành quy tắc mới vì backend không có `PUT /rules`. |
| Thư viện quy tắc · 375×812 | Ứng dụng thu menu và stepper thành các hàng gọn, còn nội dung trang cuộn dọc. Wireframe là crop desktop 1440px; phần bên phải của wireframe không nằm trong crop. | Không có wireframe mobile riêng; không suy diễn phần bị crop thành thiết kế responsive dự kiến. |

## Ảnh nguồn

- Ứng dụng: `cleaning-app-1440.png`, `cleaning-app-375.png`, `rule-library-app-1440.png`, `rule-library-app-375.png`.
- Wireframe desktop: `wireframe-cleaning-1440.png`, `wireframe-rule-library-1440.png`.
- Tham chiếu crop 375px: `wireframe-cleaning-375.png`, `wireframe-rule-library-375.png`.
- Ảnh ghép đối chiếu: `compare-cleaning-1440.png`, `compare-cleaning-375.png`, `compare-rule-library-1440.png`, `compare-rule-library-375.png`.

Các con số xuất hiện trong wireframe là dữ liệu minh họa và không được dùng làm kết quả kiểm thử hay số liệu thực của ứng dụng.
