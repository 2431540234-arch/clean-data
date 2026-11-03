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
