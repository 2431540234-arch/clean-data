# Ghi chú thiết kế backend (để chuẩn bị bảo vệ đồ án)

Mỗi nhóm chức năng có một mục: **làm gì**, **thiết kế chính**, **vì sao chọn cách đó**, viết bằng
ngôn ngữ dễ hiểu. Chi tiết kỹ thuật đầy đủ nằm ở code, test và `BACKEND_TODO.md`.

## Nhóm 0. Hạ tầng dùng chung

**Làm gì.** Dựng những phần nền mà mọi chức năng sau đều dùng: nơi lưu file dữ liệu, cách kiểm tra
"người này có được xem dữ liệu này không", cách báo lỗi, cách ghi nhật ký, và cấu hình an toàn.

**Thiết kế chính.**
- *Nơi lưu file:* dữ liệu từng dòng không nhét vào PostgreSQL mà lưu thành file Parquet; PostgreSQL
  chỉ giữ thông tin mô tả (phiên bản nào, bao nhiêu dòng, ai tạo). Có hai "ngăn kéo": thư mục trên máy
  (mặc định, không cần cấu hình gì) và S3 (dùng khi có khóa). Phần còn lại của hệ thống không biết đang
  dùng ngăn nào.
- *Quyền sở hữu:* chỉ có **một** chỗ trả lời câu hỏi "user này có quyền với project/dataset/phiên bản/
  gợi ý này không", và mọi API bắt buộc đi qua đó. Dataset, phiên bản, gợi ý đều lấy quyền từ project cha.
- *Lỗi:* lỗi nghiệp vụ trả thông báo tiếng Việt rõ ràng; lỗi bất ngờ chỉ trả một câu chung, chi tiết
  nằm trong log của server, không lộ ra cho người dùng.
- *Nhật ký:* ghi nhật ký có thể nằm **cùng một giao dịch** với thao tác chính, nên "đã làm" và "đã ghi
  lại" luôn đi cùng nhau.
- *Cấu hình:* CORS mặc định chỉ cho frontend; ở môi trường production, hệ thống từ chối khởi động nếu
  còn dùng khóa JWT mặc định hoặc CORS `*`.

**Vì sao.** Làm nền chắc trước thì các chức năng sau ngắn và đồng nhất, và các lỗi bảo mật hay gặp
(truy cập chéo dữ liệu, lộ lỗi nội bộ, đường dẫn file độc hại) bị chặn từ một điểm duy nhất thay vì
phải nhớ ở từng API. Lưu file Parquet và để DB chỉ giữ metadata giúp DB nhỏ, nhanh; Parquet còn giữ
nguyên chữ (số 0 đầu của số điện thoại không bị mất).

## Nhóm 1. Dự án (projects)

**Làm gì.** Cho người dùng tạo, xem danh sách, đổi tên và xóa dự án; danh sách có kèm số dataset của từng dự án để Dashboard hiển thị.

**Thiết kế chính.** Mọi API đều lấy dự án qua hàm kiểm tra quyền sở hữu chung (không có thì 404, không phải của mình thì 403, admin được qua). Mỗi lần tạo/đổi tên/xóa đều ghi một dòng nhật ký trong **cùng giao dịch** với thao tác. Khi xóa dự án, DB xóa dây chuyền dataset và phiên bản, sau đó server mới dọn file Parquet; nếu dọn file lỗi thì chỉ ghi cảnh báo, không làm hỏng thao tác. Số dataset được đếm bằng một truy vấn gộp cho cả danh sách thay vì hỏi từng dự án.

**Vì sao.** Đặt quyền ở một chỗ giúp các nhóm sau (dataset, rule...) dùng lại và không sót lỗ hổng truy cập chéo. Ghi nhật ký cùng giao dịch đảm bảo "đã làm" và "đã ghi lại" không bao giờ lệch nhau; dọn file sau khi commit tránh trường hợp mất file mà DB vẫn còn bản ghi. Tên dự án được cắt khoảng trắng và từ chối chuỗi rỗng để dữ liệu sạch ngay từ đầu.

## Nhóm 2. Tải file lên và quản lý dataset

**Làm gì.** Nhận file CSV/Excel, đọc thành bảng, lưu file gốc cùng "phiên bản 1" của dữ liệu, rồi trả về thông tin dataset kèm vài dòng xem trước. Có thêm xem dataset, danh sách phiên bản, đổi sheet Excel và danh sách dataset của một dự án.

**Thiết kế chính.** Mọi ô đều được đọc dưới dạng chữ để không mất số 0 đầu của số điện thoại hay biến "29" thành "29.0". Hệ thống tự đoán bảng mã (UTF-8, cp1258...), dấu phân cách (`,` `;` tab `|`) và bỏ qua vài dòng rác ở đầu file để tìm đúng dòng tiêu đề. Trước khi đọc, server kiểm tra đuôi file, kiểm tra nội dung thật có đúng loại không (file `.exe` đổi tên thành `.csv` bị chặn), giới hạn dung lượng (đọc theo từng khối, vượt thì báo 413), số dòng và số cột. Dataset, file gốc, phiên bản 1 và dòng nhật ký được tạo trong một giao dịch; nếu một bước lỗi thì cả DB lẫn file đều được dọn.

**Vì sao.** File người dùng gửi lên là nguồn rủi ro lớn nhất (sai định dạng, quá lớn, đội lốt), nên mọi kiểm tra nằm ở cửa vào và tên file người dùng không bao giờ được dùng làm đường dẫn lưu (server tự sinh khóa lưu trữ). Giữ nguyên dữ liệu gốc dạng chữ giúp các bước làm sạch về sau chủ động quyết định kiểu dữ liệu thay vì để thư viện tự đoán sai. Đổi sheet bị từ chối (409) khi đã có phiên bản làm sạch để không phá lịch sử thay đổi.

## Nhóm 3. Phân tích cột (profiling) và phát hiện lỗi dữ liệu

**Làm gì.** Với mỗi phiên bản dữ liệu, hệ thống thống kê từng cột (kiểu thật, tỉ lệ ô trống, số giá trị khác nhau, nhỏ nhất/lớn nhất/trung bình, vài giá trị mẫu) và tự tìm lỗi: ô thiếu, dòng trùng, giá trị bất thường, ngày lẫn định dạng, số điện thoại/email sai, khoảng trắng và hoa/thường lộn xộn, cùng một giá trị nhưng viết nhiều cách ("HCM", "TP.HCM", "Hồ Chí Minh").

**Thiết kế chính.** Kiểu của cột được suy ra theo thứ tự email, điện thoại, ngày, số nguyên, số thực, đúng/sai, văn bản, và một kiểu thắng khi có từ 80% giá trị khớp, nên vài giá trị bẩn không làm hỏng kết luận. Có 8 detector độc lập; một detector lỗi không làm hỏng các detector còn lại. Một dòng trong bảng lỗi mô tả cả nhóm lỗi của một cột (ví dụ "13 ngày sai định dạng") kèm số dòng và giá trị mẫu, nên mình thêm hai cột `affected_count` và `details` cho `data_issues` (migration 0003). Danh sách 63 tỉnh/thành được bổ sung đầy đủ để nhận ra các cách viết khác nhau của cùng một tỉnh.

**Vì sao.** Phiên bản dữ liệu không đổi sau khi tạo nên chạy profiling lần hai chỉ trả lại kết quả cũ, giúp các gợi ý đã gắn với một lỗi không bị mất liên kết. Mọi kiểm tra đắt tiền (số điện thoại, ngày) chỉ chạy trên giá trị khác nhau của cột để bảng lớn vẫn nhanh. Cột lỗi được xếp từ nghiêm trọng đến nhẹ để giao diện hiển thị thứ quan trọng trước.
