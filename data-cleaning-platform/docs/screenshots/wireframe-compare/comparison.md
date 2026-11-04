# Đối chiếu wireframe — Bước 2 và Bước 3

Ảnh `compare-*.png` đặt giao diện ứng dụng cạnh wireframe theo cùng kích thước viewport. Ảnh app là ảnh chụp giao diện Streamlit; ảnh wireframe desktop là tham chiếu từ [HTML gốc](../../design/wireframe-dataclean.html), với bản PDF tại [wireframe-dataclean.pdf](../../design/wireframe-dataclean.pdf).

| Trang / viewport | Khác biệt quan sát được | Lý do |
|---|---|---|
| Trang chủ · 1440×900 | Có bảng dataset gần đây của project đang chọn và hoạt động mới nhất của tài khoản; không hiển thị các số KPI minh họa trong wireframe. Ảnh: [`compare-home-1440.png`](./compare-home-1440.png). | Dataset và hoạt động lấy từ backend thật. Backend không lưu tiến độ workflow theo từng bước, nên không tự suy diễn tiến độ hoặc số liệu. |
| Trang chủ · 375×812 | Header và stepper thu gọn theo chiều rộng; các bảng nằm trong khung nội dung và trang cuộn dọc. Wireframe bên trái là crop từ bản desktop. Ảnh: [`compare-home-375.png`](./compare-home-375.png). | Wireframe không có biến thể mobile; ảnh crop chỉ là tham chiếu nội dung, không dùng làm chuẩn responsive. |
| Dự án · 1440×900 | Có KPI, tìm kiếm/lọc, thẻ dự án với thao tác Mở/Sửa/Xóa, và dataset của project đang chọn. Ảnh: [`compare-projects-1440.png`](./compare-projects-1440.png). | Dữ liệu lấy từ API. Backend không lưu trạng thái “bước tiếp theo” cho từng dataset; điểm KPI ghi rõ là trung bình các điểm trung bình theo dự án, không coi là trung bình toàn dataset. |
| Dự án · 375×812 | Thẻ KPI và nội dung xếp dọc; menu ngang cuộn trong vùng riêng, không tràn toàn trang. Wireframe bên trái là crop từ desktop. Ảnh: [`compare-projects-375.png`](./compare-projects-375.png). | Wireframe không có biến thể mobile; các hành động hiển thị bằng widget Streamlit thật. |
| Đăng nhập · 1440×900 | Bố cục hai cột và card đăng nhập bám sát wireframe; ứng dụng không điền sẵn email hoặc hiện lỗi đăng nhập mẫu. Ảnh: [`compare-login-1440.png`](./compare-login-1440.png). | Không dùng dữ liệu minh họa trong wireframe như dữ liệu thật; banner dữ liệu mẫu chỉ hiện khi bật chế độ mock. |
| Đăng nhập · 375×812 | Ứng dụng xếp phần giới thiệu phía trên form, không tràn ngang; ảnh: [`compare-login-375.png`](./compare-login-375.png). Wireframe bên phải là crop từ bản desktop. | Wireframe không có biến thể mobile; crop chỉ thể hiện phần desktop nằm trong vùng 375px, không dùng làm chuẩn responsive. |
| Header admin · 1440×1000 | Đủ 7 mục menu trên cùng một hàng, không cuộn; ảnh chụp: [`admin-menu-1440.png`](./admin-menu-1440.png). | Menu dùng hết chiều rộng khả dụng ở desktop; nhãn không bị cắt. |
| Header admin · 1280×1000 | Đủ 7 mục menu trên cùng một hàng, không cuộn. | Cùng bố cục desktop; chỉ bật cuộn ngang tại viewport rộng tối đa 768px. |
| Header admin · 375×812 | Menu cuộn ngang, không xếp thành danh sách dọc; ảnh chụp: [`admin-menu-375.png`](./admin-menu-375.png). | Giữ chiều rộng tối thiểu cho từng mục ở màn hình hẹp; nội dung trang không tràn ngang. |
| Làm sạch · 1440×900 | Wireframe dùng nội dung minh họa và có một số bảng/chỉ số cụ thể; ứng dụng hiển thị dữ liệu và trạng thái phiên làm việc thực tế. Bố cục ứng dụng dùng hai cột cân bằng. | Không lấy số liệu minh họa trong wireframe làm dữ liệu; các tab nguồn và hàng đợi dùng widget Streamlit thật theo quyết định đã chốt. |
| Làm sạch · 375×812 | Menu và stepper của ứng dụng tự xuống dòng; nội dung trang tiếp tục cuộn dọc. Wireframe bên cạnh là crop 375×812 từ wireframe desktop 1440px, không phải thiết kế mobile. | Wireframe không cung cấp biến thể mobile; crop chỉ cho biết phần nội dung desktop nằm trong vùng nhìn hẹp, không dùng làm chuẩn responsive. |
| Thư viện quy tắc · 1440×900 | Wireframe đặt danh sách và trình soạn cạnh nhau; ứng dụng đặt một trình soạn dùng chung bên dưới hai tab quy tắc. | Trình soạn được dùng chung thay vì nhân đôi trong mỗi tab; hai tab riêng là yêu cầu bắt buộc. Quy tắc dự án được nạp vào trình soạn rồi lưu thành quy tắc mới vì backend không có `PUT /rules`. |
| Thư viện quy tắc · 375×812 | Ứng dụng thu menu và stepper thành các hàng gọn, còn nội dung trang cuộn dọc. Wireframe là crop desktop 1440px; phần bên phải của wireframe không nằm trong crop. | Không có wireframe mobile riêng; không suy diễn phần bị crop thành thiết kế responsive dự kiến. |

## Ảnh nguồn

- Ứng dụng: `login-1440.png`, `login-375.png`, `cleaning-app-1440.png`, `cleaning-app-375.png`, `rule-library-app-1440.png`, `rule-library-app-375.png`.
- Trang chủ: `home-app-1440.png`, `home-app-375.png`, `compare-home-1440.png`, `compare-home-375.png`.
- Dự án: `projects-app-1440.png`, `projects-app-375.png`, `compare-projects-1440.png`, `compare-projects-375.png`.
- Wireframe Trang chủ / Dự án: `wireframe-home-1440.png`, `wireframe-projects-1440.png`.
- Wireframe desktop: `wireframe-login-1440.png`, `wireframe-cleaning-1440.png`, `wireframe-rule-library-1440.png`.
- Tham chiếu crop 375px: `wireframe-login-375.png`, `wireframe-cleaning-375.png`, `wireframe-rule-library-375.png`, `wireframe-home-375.png`, `wireframe-projects-375.png`.
- Ảnh ghép đối chiếu: `compare-login-1440.png`, `compare-login-375.png`, `compare-cleaning-1440.png`, `compare-cleaning-375.png`, `compare-rule-library-1440.png`, `compare-rule-library-375.png`.

Các con số xuất hiện trong wireframe là dữ liệu minh họa và không được dùng làm kết quả kiểm thử hay số liệu thực của ứng dụng.
