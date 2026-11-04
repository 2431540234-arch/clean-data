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

## Nhóm 4. Gợi ý ghép tên cột (mapping)

**Làm gì.** Người dùng đưa danh sách tên cột chuẩn (ví dụ `ho_ten`, `email`), hệ thống trả về với mỗi cột trong file đã tải lên: nên đổi thành cột chuẩn nào, hoặc "không khớp".

**Thiết kế chính.** Mọi tên cột được chuẩn hóa trước (bỏ dấu, chữ thường, ký tự lạ thành `_`) nên "Số ĐT" và "so_dt" là một. Sau đó thử lần lượt: trùng tên, cùng nhóm đồng nghĩa trong từ điển (sdt, phone, điện thoại...), chứa đủ các từ của cột chuẩn ("Email liên hệ" chứa "email"), rồi gần giống (sai chính tả nhẹ). Mỗi cột chuẩn chỉ được gán cho một cột nguồn; nếu hai cột tranh nhau thì cặp có điểm tin cậy cao hơn thắng. Kết quả luôn có đủ mọi cột nguồn đúng thứ tự, cột không khớp là `null`. Bước dự phòng bằng AI cho các cột còn lại sẽ được nối ở Nhóm 5 cùng hạ tầng AI.

**Vì sao.** Việc ghép bằng quy tắc là nhanh, miễn phí, giải thích được và không cần khóa AI nên đủ cho phần lớn file tiếng Việt thực tế. Quy tắc "một cột chuẩn một cột nguồn" tránh tình huống hai cột cùng bị đổi tên thành một tên, làm hỏng dữ liệu. Endpoint cũng sửa lỗi cũ của khung code: body phải là một mảng JSON nên cần khai báo `Body()` rõ ràng.

## Nhóm 5. Gợi ý làm sạch (quy tắc + AI tùy chọn)

**Làm gì.** Từ các lỗi đã phát hiện ở Nhóm 3, hệ thống sinh các gợi ý "nên làm gì": mỗi gợi ý có lời giải thích tiếng Việt, độ tin cậy và một đoạn rule JSON để áp dụng sau. Người dùng chấp nhận hoặc từ chối từng gợi ý (đổi ý được); chấp nhận chưa làm thay đổi dữ liệu.

**Thiết kế chính.** Phần cốt lõi là bộ quy tắc cố định: mỗi loại lỗi ứng với một rule (ngày lẫn định dạng thì chuẩn hóa ngày, trùng dòng thì xóa dòng lặp, giá trị bất thường thì chỉ đánh dấu...). Nếu có khóa AI, hệ thống gửi thêm cho AI một bản tóm tắt đã che thông tin cá nhân (email, số điện thoại, tên chỉ còn dạng che; không gửi dòng dữ liệu thật) và nhận về các đề xuất bổ sung. Mọi câu trả lời của AI đều bị kiểm tra chặt (op phải nằm trong danh sách cho phép, cột phải có thật, AI không được đề xuất xóa cột hay xóa dòng) và gợi ý hỏng bị bỏ riêng từng cái. Không có khóa, AI lỗi, hết thời gian hay trả lời sai thì hệ thống lặng lẽ dùng kết quả của quy tắc. Mỗi lần gọi AI được ghi vào bảng `ai_requests` (chỉ số liệu, không có dữ liệu hay khóa), và chính bảng này cho ra `total_ai_calls` ở trang quản trị. Cột nào chưa ghép được bằng quy tắc ở Nhóm 4 cũng được hỏi AI (chỉ gửi tên cột).

**Vì sao.** Chạy bằng quy tắc trước giúp hệ thống luôn dùng được, rẻ, nhanh và giải thích được, còn AI chỉ làm tăng chất lượng chứ không phải điều kiện để chạy. Tách rõ "AI chỉ sinh JSON, engine mới thực thi" giữ nguyên nguyên tắc an toàn của đồ án: không bao giờ chạy code do AI viết. Che dữ liệu cá nhân trước khi gửi ra ngoài là yêu cầu bảo mật tối thiểu khi dùng dịch vụ AI bên thứ ba; khi kiểm thử mình phát hiện và sửa một chỗ lộ nguyên dòng dữ liệu trong phần "ví dụ" của lỗi trùng dòng.

## Nhóm 6. Rule Engine, xem trước, áp dụng và lịch sử phiên bản

**Làm gì.** Thực thi các rule làm sạch (13 loại: cắt khoảng trắng, đổi hoa/thường, thay giá trị, chuẩn hóa ngày/điện thoại/email, ép kiểu, điền ô thiếu, xóa dòng trùng, xóa dòng theo điều kiện, đánh dấu bất thường, đổi tên cột, xóa cột). Người dùng xem trước kết quả, rồi mới áp dụng để tạo phiên bản mới, và có thể hoàn tác, làm lại hoặc quay về bất kỳ phiên bản nào.

**Thiết kế chính.** Rule Engine là nơi duy nhất sửa dữ liệu, theo mẫu "đăng ký": mỗi op là một hàm nhận bảng và trả bảng mới, chỉ op đã đăng ký mới chạy được và không có `eval/exec`. Xem trước chạy thử trên một mẫu dòng đầu để hiện từng ô đổi, còn số dòng bị ảnh hưởng được đếm trên toàn bộ dữ liệu (khi bảng không quá lớn) nên con số là thật. Áp dụng ghi phiên bản mới, từng bước vào `cleaning_operations` và nhật ký trong cùng một giao dịch, có khóa dòng dataset để hai người thao tác cùng lúc không tạo ra hai phiên bản trùng số. Phiên bản không bao giờ bị xóa; "hiện tại" chỉ là một con trỏ nên undo/redo/restore chỉ đổi con trỏ. Rule template (lưu rule dùng lại theo project) cũng nằm trong nhóm này.

**Vì sao.** Tách "xem trước" khỏi "áp dụng" và không bao giờ sửa dữ liệu tại chỗ giúp người dùng yên tâm thử và luôn quay lại được. Lỗi tham số hay cột không tồn tại được báo bằng tiếng Việt kèm số bước bị lỗi, và khi lỗi xảy ra thì không có phiên bản hay file nào được tạo ra. Các gợi ý do AI đề xuất còn được chạy thử trên một mẫu dữ liệu, gợi ý nào Rule Engine không chạy nổi sẽ bị loại trước khi đến tay người dùng.

## Nhóm 7. Điểm chất lượng, xuất file, xem dòng theo trang

**Làm gì.** Cho mỗi phiên bản dữ liệu một điểm chất lượng từ 0 đến 100 (kèm 4 tiêu chí: đầy đủ, không trùng, hợp lệ, nhất quán), cho tải dữ liệu ra CSV hoặc Excel (Excel có thêm sheet báo cáo và sheet lỗi), xem từng trang dòng dữ liệu của bất kỳ phiên bản nào, và hiển thị điểm trung bình của mỗi project trên Dashboard.

**Thiết kế chính.** Điểm là tổng có trọng số của bốn tỉ lệ (đầy đủ 30%, không trùng 20%, hợp lệ 30%, nhất quán 20%), mỗi tỉ lệ dạng "1 trừ số ô xấu chia tổng", tái dùng kết quả của các detector nên con số khớp với danh sách lỗi người dùng đang thấy; công thức và ví dụ tính tay nằm trong `docs/quality_score.md`. Vì phiên bản không đổi nên điểm chỉ tính một lần rồi lưu cache, và được tính luôn khi chạy profiling. File CSV có BOM UTF-8 để Excel tiếng Việt không lỗi chữ; ô bắt đầu bằng `=`, `+`, `-`, `@` (có thể bị Excel hiểu là công thức) được thêm dấu `'` ở CSV, còn ở Excel mọi ô chữ được ghi là chuỗi chứ không bao giờ là công thức. Xem dòng dùng phân trang (tối đa 1000 dòng một lần) và đọc trực tiếp từ file Parquet.

**Vì sao.** Tính điểm từ chính các detector giúp người dùng hiểu "vì sao điểm thấp" và thấy điểm tăng sau khi làm sạch. Chống chèn công thức là biện pháp bảo mật cần thiết vì dữ liệu do người ngoài đưa vào có thể được mở bằng Excel của người khác. Điểm trung bình của project chỉ tính trên phiên bản hiện tại đã có báo cáo, nếu chưa có thì trả `null` để giao diện ẩn đi thay vì hiện con số sai.

## Nhóm 8. Đăng nhập an toàn, quản trị, nhật ký và thống kê

**Làm gì.** Hoàn thiện phần tài khoản: đổi mật khẩu, chặn dò mật khẩu, khóa/mở khóa và đổi quyền người dùng, đặt lại mật khẩu, trang nhật ký hoạt động và thống kê hệ thống cho quản trị viên.

**Thiết kế chính.** Đăng nhập sai 5 lần trong 15 phút (tính theo cặp email + địa chỉ IP) thì bị chặn với mã 429 và thông báo tiếng Việt; thêm một trần theo IP để không dò được bằng cách đổi liên tục email. Bộ đếm dựa ngay trên bảng nhật ký nên không cần thêm hạ tầng, và đăng nhập đúng sẽ đặt lại bộ đếm. Mỗi lần đăng nhập đúng/sai đều được ghi nhật ký, không bao giờ kèm mật khẩu. Khi đổi hoặc đặt lại mật khẩu, hệ thống ghi mốc thời gian `password_changed_at` và từ chối mọi token cấp trước mốc đó, nên token bị đánh cắp mất tác dụng; đổi mật khẩu trả kèm một token mới cho phiên hiện tại. Quản trị viên không thể hạ quyền hay khóa quản trị viên đang hoạt động cuối cùng; thay đổi quyền và khóa trong cùng một yêu cầu thành công hoặc thất bại cùng nhau. Đặt lại mật khẩu sinh mật khẩu tạm ngẫu nhiên, trả về đúng một lần và không ghi vào nhật ký.

**Vì sao.** Chặn dò mật khẩu và thu hồi token là hai biện pháp tối thiểu cho một hệ thống có đăng nhập, và làm chúng bằng chính bảng nhật ký giúp đồ án vừa đủ an toàn vừa đơn giản để bảo vệ. Quy tắc "không để mất quản trị viên cuối cùng" tránh tình huống không còn ai quản trị được hệ thống. Email được so khớp không phân biệt hoa/thường để một người không có hai tài khoản chỉ khác kiểu chữ. Bài kiểm tra "cô lập dữ liệu" gọi 27 endpoint bằng một người dùng khác và xác nhận tất cả trả 403 mà không rò rỉ nội dung.

## Nhóm 9. Nối giao diện với các endpoint bổ sung

**Làm gì.** Giao diện dùng thật các endpoint backend đã thêm: Dashboard hiện số dataset và điểm chất lượng trung bình, chọn lại dataset bằng danh sách thay cho ô nhập ID, trang Tổng quan có tab "Lỗi đã phát hiện", biểu đồ mức độ lỗi và phân bố giá trị từng cột, thẻ gợi ý có viền màu theo mức độ nghiêm trọng của lỗi.

**Thiết kế chính.** Mọi chỉ số mới đều "ẩn khi thiếu": nếu backend chưa trả điểm trung bình thì thẻ không hiện, nếu lấy danh sách lỗi thất bại thì trang vẫn chạy với cảnh báo nhỏ. Sau khi đổi mật khẩu, giao diện nhận `access_token` mới do backend trả về, nên người dùng ở lại trang và thấy thông báo thành công thay vì bị đăng xuất. Mã nhật ký mới đều có nhãn tiếng Việt, mã chưa có nhãn vẫn hiện nguyên văn. Dữ liệu giả (mock) được cập nhật để hành vi khớp backend thật, nên toàn bộ test giao diện vẫn chạy được không cần backend.

**Vì sao.** Giao diện không tự suy diễn: mọi số liệu lấy từ API nên demo thật và demo mock cho cùng kết quả. Việc backend thu hồi token sau khi đổi mật khẩu là yêu cầu bảo mật, nên giao diện phải nhận token mới để không làm hỏng trải nghiệm.

## Khác biệt mock và backend thật (kết quả chạy demo đầy đủ ngày 04/11/2026)

Chạy cùng file `khach_hang_ban.csv` ở hai chế độ cho thấy luồng và hình dạng dữ liệu giống nhau, còn khác ở các điểm sau:

| Điểm | Mock (`FRONTEND_MOCK=1`) | Backend thật |
|---|---|---|
| Số gợi ý trên `khach_hang_ban.csv` | 8 (có 2 gợi ý "AI" giả) | 10, tất cả nguồn "Quy tắc" vì chưa có khóa AI |
| Điểm chất lượng ban đầu | 90,7 | 90,5 (đếm 43 ô không nhất quán thay vì 17; ngưỡng outlier IQR 1,5 thay vì 3) |
| Danh sách lỗi | suy ra từ gợi ý, 1 gợi ý một lỗi | 8 detector độc lập, 13 nhóm lỗi, có ví dụ và số dòng thật; có thêm lỗi chưa có gợi ý tự động (thiếu email/SĐT/ngày, email sai cú pháp...) |
| Tên tỉnh/thành | 5 tỉnh mẫu | đủ 63 tỉnh/thành, tự nhận cả "TP." và không dấu |
| Số dòng bị ảnh hưởng khi xem trước | tính trên mẫu | tính trên toàn bộ dữ liệu (bảng ≤ 200.000 dòng) |
| File Excel xuất ra | 2 sheet | 3 sheet (thêm "Lỗi đã phát hiện"), ô văn bản luôn là chuỗi, CSV chống chèn công thức |
| `total_ai_calls` | đếm số lần bấm "Sinh gợi ý" | đếm số lần gọi AI thật (0 khi không có khóa) |
| Đăng nhập | không giới hạn, không ghi nhật ký | chặn sau 5 lần sai (429); ghi `auth.login` / `auth.login_failed` |
| Đổi mật khẩu | token cũ vẫn dùng được | token cũ bị vô hiệu, frontend nhận token mới |
| Mapping `Email liên hệ` → `email` | không khớp (None) | khớp nhờ quy tắc "chứa đủ các từ của cột chuẩn" |
| Điểm TB của project trên Dashboard | tính ngay | chỉ khi phiên bản hiện tại đã được phân tích hoặc xem điểm |
| File lạ, quá lớn, sai loại | báo lỗi chung | kiểm tra chữ ký file, 413 khi quá `MAX_UPLOAD_MB`, giới hạn dòng/cột |

## CSV lớn theo từng phần (tới 200 MB)

**Làm gì.** Thêm 4 endpoint `/datasets/uploads...` để tải CSV lớn: frontend tự tách file thành các phần 8 MB,
gửi lần lượt, server ghép lại thành một file rồi đọc theo luồng (`services/ingestion/csv_stream.py`) và ghi
Parquet từng khối, không nạp cả file vào RAM. Sau đó làm sạch và xuất trên **cả bộ dữ liệu** như file thường.

**Vì sao không xử lý từng phần riêng.** Xóa dòng trùng, ngoại lai (IQR/z-score), điền trung vị/giá trị phổ biến
và điểm chất lượng cần nhìn toàn bộ dữ liệu; làm riêng từng phần rồi gộp sẽ cho kết quả khác file nhỏ.
Có test so sánh đọc theo luồng với đọc cả file (`tests/unit/test_csv_stream.py`, cỡ khối từ 1 dòng tới 1000).

**Phiên tải.** Lưu trên đĩa ở `UPLOAD_TMP_DIR` (mặc định `data/tmp_uploads`), không có bảng DB; tự dọn sau
`UPLOAD_SESSION_TTL_MINUTES` (60 phút) và dọn ngay khi hoàn tất hoặc khi CSV lỗi. Phiên gắn với người mở.

**Toàn vẹn (server không tin frontend).** Mỗi phiên chốt `part_size` lúc mở; mọi phần trừ phần cuối phải đúng cỡ đó,
tổng dung lượng các phần không được vượt dung lượng khai báo và phải bằng nó khi hoàn tất, trần
`MAX_CHUNKED_UPLOAD_MB` do server giữ. Gửi lại cùng một phần là ghi đè (không ghép trùng). Mã SHA-256 (thư viện
chuẩn `hashlib`, không thêm gói) được kiểm cho từng phần (query `sha256`) và cho cả file (lúc mở phiên): chỉ mã của
cả file mới bắt được việc hai phần cùng kích thước bị đổi chỗ; nếu client không gửi mã thì không phát hiện được
(có test ghi lại giới hạn này). Frontend luôn gửi cả hai mã.

**Dọn dẹp.** Các phần nằm ở `UPLOAD_TMP_DIR` (mặc định `backend/data/tmp_uploads`, tức `/app/data/tmp_uploads` trong
container), KHÔNG nằm trong volume `dcp_storage`. Xóa hết khi hoàn tất, hủy hoặc khi CSV lỗi. Phiên quá
`UPLOAD_SESSION_TTL_MINUTES` (60 phút không hoạt động) bị xóa: khi ứng dụng khởi động, khi có người mở phiên mới, tối đa
mỗi phút một lần khi nhận phần, và ngay khi chính phiên đó bị truy cập. Không có tác vụ định kỳ riêng.

**Nhật ký (audit).** Chỉ lần hoàn tất ghi `dataset.upload` (đã tạo dữ liệu). Mở phiên, gửi phần và hủy không ghi nhật ký.

**Giới hạn Excel.** Một sheet Excel chứa tối đa 1.048.575 dòng dữ liệu; `GET /export/{version_id}/excel` trả 422 với
gợi ý xuất CSV khi vượt (kiểm cả sheet "Lỗi đã phát hiện", báo sớm theo `row_count` trước khi nạp bảng). Không tự cắt dữ liệu.

**Đo thực tế** (Docker, 16 GiB RAM, file 198 MiB / 840.000 dòng / 7 cột, mỗi giai đoạn bắt đầu từ backend mới khởi động):

| Giai đoạn | Thời gian | RAM đỉnh |
|---|---|---|
| Tải 25 phần + ghép + đọc theo luồng + lưu | 12,7 giây | 653 MiB |
| Phân tích (profiling) | 80 giây | 2,2 GiB |
| Sinh gợi ý | 0,1 giây | ~120 MiB |
| Áp dụng 4 bước làm sạch | 9,7 giây | 1,4 GiB |
| Xuất CSV (198 MiB) / Excel (34 MiB) | — / 142 giây | 3,4 GiB |

Timeout của frontend cho các thao tác này đã nới (phân tích 600 giây, xuất Excel 900 giây).

## Cải thiện sau

- **403 hay 404:** hiện tài nguyên của người khác trả 403 ("không có quyền"), nên người ngoài biết được ID đó có tồn tại. Có thể đổi thành 404 cho mọi trường hợp không phải của mình.
- **Kiểm thử AI với khóa thật:** đã kiểm thử bằng client giả và cơ chế dự phòng thật (khóa Anthropic sai, backend tạm: cả 3 lần sinh gợi ý rơi về quy tắc, không traceback, `ai_requests` ghi `status=error` kèm `AuthenticationError`, không chứa dữ liệu thô hay khóa; "Lượt gọi AI" đếm đúng). **Chưa có lần gọi AI thành công** vì chưa nạp credit API, nên prompt chưa được xem lại với câu trả lời thật.
- **Xử lý nền cho file rất lớn:** upload, profiling và áp dụng rule chạy đồng bộ trong request. CSV tới 200 MB được tải theo từng phần (xem mục "CSV lớn theo từng phần" bên dưới) nhưng phân tích và xuất vẫn đồng bộ (đo ở 198 MiB / 840.000 dòng: phân tích ~80 giây, xuất Excel ~140 giây, RAM đỉnh ~3,4 GiB). Muốn vượt 200 MB hoặc tránh request kéo dài thì chuyển sang tác vụ nền (`workers/tasks.py` còn là khung).
- **Excel lớn hơn 50 MB:** chưa hỗ trợ (openpyxl phải nạp cả file); hãy lưu thành CSV.
- **Lưu mapping và schema chuẩn của project:** endpoint #4, #5 (`column_mappings`, `target-schema`) chưa làm; hiện mapping được áp dụng bằng bước `rename_column`.
- **Dọn file lưu trữ mồ côi:** nếu ghi DB thất bại sau khi ghi file, hệ thống đã dọn; còn trường hợp tiến trình bị tắt đột ngột giữa chừng thì cần một tác vụ quét định kỳ.
- **Chặn đăng nhập sai nhiều tiến trình:** bộ đếm đọc từ DB nên dùng chung được, nhưng chưa có giới hạn tốc độ chung cho các API khác (nên đặt ở reverse proxy khi deploy).
- **Deploy online:** `deploy.yml` còn là khung; cần URL công khai theo yêu cầu đề.
