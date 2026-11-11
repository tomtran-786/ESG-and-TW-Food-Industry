# Hạn chế và những điểm cần làm rõ (đi kèm `report/RA_report_FC_ESG_TWSE_food.docx`)

Ngày: 2026-11-07. File này để Tuấn đọc, không nộp cho cô. Số thứ tự `#` là số trong `docs/open_questions.md`, mã `D..` là trong `docs/deviations_from_brief.md`.

---

## 1. Kết quả chính nói gì, và không nói gì

- Hệ số SA trong mô hình chính = 2.489, p = 0.864 (t(21)), p wild bootstrap = 0.880. Tức là **không tìm thấy quan hệ**, không ủng hộ H1 lẫn H2.
- "Không tìm thấy" khác với "không có". Với 22 cụm, mô hình chỉ phát hiện được hiệu ứng ≥ 1.76 điểm TESG cho mỗi 1 độ lệch chuẩn within của SA (power 80%). Hiệu ứng nhỏ hơn thì dữ liệu này không thấy được.
- Ví dụ dễ hiểu: SA của một công ty trong 10 năm gần như đứng yên (độ lệch chuẩn within chỉ 0.042, trong khi chênh giữa các công ty là 0.80). Giống như muốn đo tác động của chiều cao lên cân nặng nhưng chỉ được nhìn từng người qua các năm khi họ đã trưởng thành: chiều cao gần như không đổi, nên hồi quy within không học được gì.
- Rủi ro khi trình bày: đừng viết "tài chính bị ràng buộc không ảnh hưởng ESG". Viết đúng như báo cáo: "thay đổi SA trong cùng một công ty không đi kèm thay đổi TESG".

## 2. Những điểm cần hỏi cô (chưa có câu trả lời)

- **Hausman không bác bỏ RE (#20).** Brief §3.2 nói p ≥ 0.05 thì RE "chấp nhận được", nhưng §3.3 lại yêu cầu two-way FE. Báo cáo giữ FE. Cần biết: RE cho hệ số SA ngược dấu (−4.882). Script 06 (thăm dò) cho thấy RE với SE cluster có p = 0.045. Nếu cô muốn áp dụng §3.2 theo nghĩa đen thì kết luận chính sẽ đổi sang "ủng hộ yếu H1". Nên hỏi cô muốn mô hình nào làm kết quả chính.
- **Dùng dữ liệu 2015 làm biến trễ (#6).** Mẫu chính N = 219 dùng doanh thu và tổng tài sản 2015 chỉ để tính GROWTH 2016 và SA trễ 2016. Nếu cô không đồng ý thì lấy cột (2) Bảng 4 (N = 197) làm kết quả chính. Kết luận không đổi (β = 0.503, p = 0.973).
- **Định nghĩa SA (#7).** Brief khác Hadlock & Pierce ở 3 điểm: USD danh nghĩa (H&P: USD năm 2004), tuổi tính từ năm thành lập (H&P: số năm có giá trên Compustat), winsorize 1/99 (H&P: chặn ở $4.5 tỷ và 37 năm). Báo cáo theo brief và nêu rõ khác biệt. Script 07 đã chạy bản H&P đầy đủ: β = −0.87, p = 0.924, vẫn null. Chưa đưa vào báo cáo vì CLAUDE.md §7b nói chỉ đưa vào Bảng 5 khi cô đồng ý.
- **Không winsorize biến phụ thuộc (#19, D18).** Brief §4.4 nói "winsorize mọi biến liên tục". TESG, E, S, G bị chặn 0 đến 100 nên giữ nguyên. Nếu cô muốn làm theo nghĩa đen: sửa 1 dòng trong script 02 rồi chạy lại.
- **Biểu đồ và phân tích between/within (#21).** Báo cáo chỉ dùng số mô tả từ script 03b (tỷ lệ phương sai, Hình 1). Các hồi quy thăm dò của script 06 (pooled OLS, hybrid RE, bỏ 1216) không đưa vào vì header script 06 ghi rõ cần cô duyệt. Riêng khoảng tin cậy 95% của β, hiệu ứng theo 1 độ lệch chuẩn within (0.10 điểm) và MDE (1.76) lấy từ `explore_magnitudes.csv` của script 06; đây chỉ là biến đổi lại kết quả Bảng 4, không phải mô hình mới, nhưng vẫn nên nói với cô.
- **Brief nói "ít nhất 2 trong 3" kiểm định nhưng liệt kê 4 (#1).** Báo cáo làm cả 4.
- **Mẫu đoạn kết quả §6.2 của brief bàn về SIZE (#2)**, mà SIZE không có trong mô hình chính. Báo cáo chỉ bàn SIZE ở Model 2 (§5.4).
- **Python thay vì R (#11).** Brief cho phép, nhưng nên xác nhận cô chấp nhận output dạng này.
- **Dummy SA (#8):** dùng trung vị toàn mẫu. Với FE, hệ số chỉ được nhận diện từ 5 công ty có dummy đổi giá trị. Đây là điểm yếu thật của kiểm định §5.1.
- **Hạn nộp và định dạng (#10):** chưa biết. Báo cáo đang là Word.

## 3. Hạn chế về dữ liệu

- **Chỉ 24 công ty, 22 có ≥ 2 quan sát.** Thấp hơn "25 đến 30" của brief vì TEJ trả về 24 công ty TSE M1200 (đã loại 5 TDR). Ít cụm làm SE cluster dễ bị thiên lệch xuống, nên báo cáo dùng t(G−1) và wild bootstrap.
- **TESG 2016 đến 2020 là điểm tính lại sau.** Tất cả có ngày công bố 31/03/2022 (TESG ra mắt quý 1/2022). Nghĩa là 5/10 năm là điểm "hồi tố" theo phương pháp hiện tại, không phải điểm thị trường thấy vào lúc đó.
- **3 quan sát 2025 bị mất (1218, 1219, 1225) do hạng W\*.** Quy tắc này chỉ áp dụng từ kỳ 2026/12, nên năm 2025 bị chọn mẫu theo một quy tắc mới. Không tự điền điểm cho 3 dòng này vì file gốc không có số.
- **Danh sách công ty lấy từ bảng hiện tại của TEJ.** Công ty nào từng thuộc ngành thực phẩm trong 2016 đến 2025 rồi chuyển ngành hoặc chuyển sàn sẽ không xuất hiện.
- **TESG có thể đã gồm điều chỉnh Event Radar (D4).** Bằng chứng: hồi quy TESG theo E, S, G có R² 0.978, phần dư tương quan 0.77 với điểm Event Radar. Các số này chạy ad hoc, **chưa nằm trong script**, nên không đưa vào báo cáo. Báo cáo chỉ gọi Y là "TESG composite score as exported". Nếu muốn nêu, phải chuyển phép kiểm tra này vào script trước.
- **Hai công ty niêm yết 2025 (7780, 7791)** chỉ có 1 quan sát; nằm trong N = 219 nhưng không ảnh hưởng hệ số FE.

## 4. Hạn chế về phương pháp

- **SA gần như không đổi trong một công ty.** Chỉ còn 0.32% phương sai sau khi bỏ hiệu ứng công ty và năm. Age bị FE hấp thụ gần hết, phần còn lại chủ yếu là thay đổi tổng tài sản tính bằng USD (có lẫn biến động tỷ giá).
- **Firm 1216 (Uni-President)** nằm ở vùng Size > 8.57, nơi công thức SA quay đầu: càng lớn thì SA càng tăng (bị coi là "càng bị ràng buộc"). Ngược hướng với 21 công ty còn lại. Script 06 bỏ 1216 thì β = 5.11, p = 0.737 (chưa đưa vào báo cáo).
- **Model 2 (+SIZE):** SA và SIZE tương quan −0.83 sau khi khử FE, VIF 3.41 và 3.43. SE của SA tăng từ 14.3 lên 22.1, nên cột này khó diễn giải.
- **Trụ S:** p = 0.037 với t(21) nhưng 0.084 với wild bootstrap, và có 3 hồi quy trụ. Không nên xây kết luận trên cột này.
- **Chỉ là quan hệ tương quan.** Không có công cụ cho nhân quả; chiều ngược (ESG ảnh hưởng ràng buộc tài chính) là điều Chang et al. (2025) và Cheng et al. (2014) nghiên cứu.

## 5. Kiểm tra chéo bằng Stata: các chỗ lệch đã biết

- Hệ số, SE cluster, Hausman: khớp Python ở mô hình chính, Bảng 5 và Bảng 6.
- **Cột brief-literal (N = 197):** Stata mặc định winsorize GROWTH theo ngưỡng của 219 dòng (β = 0.551), Python winsorize trên 197 dòng (β = 0.503). Khi Stata dùng cùng quy tắc (mô hình chẩn đoán 2b) thì khớp. Báo cáo dùng số Python và ghi rõ quy tắc trong chú thích Bảng 4. Hai cách đều cho kết quả null.
- **Mundlak:** Stata 3.37 (p = 0.761), Python 3.50 (p = 0.744). Khác do cách ước lượng thành phần phương sai RE giữa hai phần mềm. Kết luận như nhau.

## 6. Về tài liệu tham khảo

- Mọi trích dẫn trong báo cáo đều đã đối chiếu với toàn văn PDF trong `literature/`, kèm số trang theo đánh số của tạp chí (không phải số trang PDF).
- **Fazzari et al. (1988):** file PDF không có URL/DOI. URL Brookings trong danh mục lấy từ tìm kiếm web hôm nay: https://www.brookings.edu/articles/financing-constraints-and-corporate-investment/ . Nên mở kiểm tra lại.
- **Hong et al. (2012)** là working paper NBER, chưa qua bình duyệt. Nếu cô muốn bản đã đăng tạp chí thì cần bổ sung file vào `literature/`.
- **Hai trang TEJ (launch 2022, trang sản phẩm TESG)** là bản lưu PDF của trang web, không chứa URL. Danh mục ghi "Retrieved November 6, 2026, from the TEJ website". Nên dán URL thật vào khi có. Trang sản phẩm ghi ngày "Jan 01 2021" nhưng nội dung có quy tắc 2026/12, nên báo cáo ghi (n.d.).
- **Slide TEJ-NCCU 2026 không được trích dẫn** dù có thông tin hữu ích (26 đến 32 công ty thực phẩm bắt buộc báo cáo, sơ đồ cách tính điểm TESG). Lý do: trang 2 của slide có tuyên bố bản quyền cấm "引用" (trích dẫn) khi chưa có sự đồng ý bằng văn bản của TEJ.
- Phần tổng quan tài liệu ngắn hơn yêu cầu 4 đến 6 trang ở brief §6.1 vì chỉ dùng 10 tài liệu có sẵn. Muốn dài hơn thì cần thêm toàn văn vào `literature/`.

## 7. Việc Tuấn nên làm trước khi nộp

- Đọc lại tên, đơn vị, email ở trang đầu (hiện chỉ có tên và "Ming Chuan University, Taiwan").
- Hỏi cô các mục ở phần 2, nhất là #20 (FE hay RE) và #6 (dữ liệu 2015).
- Nếu cô đồng ý đưa script 06/07 vào: thêm 1 bảng between/within và 1 cột H&P SA vào Bảng 5, rồi chạy lại `report/build/`.
- Nếu sửa bất kỳ script nào: chạy lại 01 đến 05 rồi chạy lại phần build báo cáo, vì mọi số trong bảng đều đọc trực tiếp từ `outputs/tables/`.
