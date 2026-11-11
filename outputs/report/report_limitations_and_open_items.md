# Hạn chế và những điểm cần làm rõ (đi kèm `outputs/report/RA_report_FC_ESG_TWSE_food.docx`)

Cập nhật: 2026-11-07, sau khi winsorize biến ESG và thêm random effects. File này để Tuấn đọc, không nộp cho cô. Số thứ tự `#` là số trong `docs/open_questions.md`, mã `D..` là trong `docs/deviations_from_brief.md`.

---

## 0a. Phiên bản 3 (2026-11-07 20:30): báo cáo chỉ còn random effects, main sample

- **Bảng 4, 5, 6 chỉ còn RE trên main sample (N = 219).** FE chỉ còn xuất hiện ở phần Hausman (mục 4.3 và Phụ lục A3), vì đó là phép so sánh để chọn mô hình.
- **Restricted sample (N = 197) bị bỏ khỏi báo cáo**, kể cả cột trong Bảng 1. Số liệu vẫn nằm trong `outputs/tables/` (Table4, Table5, Table6 .xlsx và các file `*_inference.csv`).
- **Tiêu đề theo brief:**
  - Báo cáo và các phần chính: tên báo cáo, 1 Introduction, 2 Literature Review, 3 Methodology, 4 Empirical Results, 5 Conclusion, References.
  - Các mục con: theo nội dung chính ghi ở brief §6.1 và tên các bước ở Step 2, 3, 5.
  - Bảng 1 đến 6: theo brief §6.3, riêng tiêu đề Bảng 4 lấy từ §3.3.
- **H1 và H2** viết theo bảng giả thuyết của brief.
- **Đoạn kết quả chính** viết theo mẫu §6.2 của brief: "a one-unit increase in the SA Index ... is associated with a 4.805-point decrease in TESG score, supporting H1".
- **Một số trong báo cáo do mình tự tính:** "khoảng 0.45 độ lệch chuẩn between của TESG" = 3.82 / 8.47. Hai số này lấy từ `explore_magnitudes.csv`; phép chia là mình làm.
- **Wild bootstrap đã bỏ khỏi báo cáo**, vì nó chỉ có cho FE.

### Số liệu FE và restricted sample để Tuấn báo riêng với cô

| Mô hình | Hệ số SA | SE (CR1) | p, t(G−1) | p wild bootstrap |
|---|---|---|---|---|
| FE, main sample (N = 219) | 2.245 | 14.032 | 0.874 (G = 22) | 0.887 |
| RE, main sample (N = 219), trong báo cáo | −4.805 | 2.320 | 0.0498 (G = 24) | n/a |
| FE, restricted sample (N = 197) | 0.407 | 14.643 | 0.978 | 0.979 |
| RE, restricted sample (N = 197) | −5.253 | 2.271 | 0.030 | n/a |

FE cho kiểm định độ vững (main sample):
- SA dummy: −3.102 (p = 0.367)
- SA trễ: 10.504 (p = 0.377)
- Thêm SIZE: SA 4.842 (p = 0.827)
- Theo trụ: E 18.869 (p = 0.639), S −29.047 (p = 0.026, wild 0.069), G 25.843 (p = 0.102)

Nguồn: `outputs/tables/table4_inference.csv`, `table5_6_inference.csv`.

### Rủi ro của phiên bản RE-only

- **p = 0.0498 sát ngưỡng 5%.** Với t(21) thay vì t(23), p = 0.051 (mục 1).
- **Model 2 (thêm SIZE) làm SA mất ý nghĩa** (−2.519, p = 0.260). Báo cáo nêu điều này ở mục 4.4.3 và phần kết luận. Nếu bỏ đi thì bảng và chữ sẽ mâu thuẫn.
- **Brief §3.1 và §3.3 viết mô hình chính là two-way FE.** Báo cáo dùng RE dựa trên quy tắc §3.2 (p ≥ 0.05 thì RE chấp nhận được). Cô có thể hỏi vì sao không theo §3.3, nên chuẩn bị câu trả lời: Hausman và Mundlak đều không bác bỏ RE, và FE kém chính xác vì SA gần như không đổi trong từng công ty.

## 0. Những gì đã thay đổi trong lần này

- **Winsorize TESG, E, S, G** ở mức 1%/99% trên mẫu 219 dòng (đúng nghĩa đen của brief §4.4). Mỗi biến bị cắt 3 quan sát ở mỗi đuôi. Bản cũ giữ Y nguyên như TEJ xuất (D18 cũ).
  - Hệ số SA trong FE đổi rất ít: **2.489 → 2.245**, p 0.864 → 0.874. Kết luận FE không đổi.
- **Thêm random effects (RE)** bên cạnh FE trong Bảng 4, 5, 6 (Bảng 5 và 6 có Panel A là FE, Panel B là RE).
- **Bỏ mọi chỗ nhắc "brief"** trong báo cáo. Mẫu "brief-literal" giờ gọi là **"restricted sample"** (chỉ dữ liệu 2016-2025, N = 197).
- Các script đã sửa: `02`, `03`, `03b`, `04`, `05`, `06`, `07`. Bản cũ (script + outputs + data_clean) được sao lưu ở `archive/backup_2026-11-07_before_Y_winsor/`.
- Script chạy trên máy Tuấn bằng môi trường Linux mới (`~/venv_ra`, linearmodels 7.1, statsmodels 0.15, pandas 2.3.3). Môi trường này tái lập đúng số cũ (2.4887) trước khi đổi Y. `.venv/` trong dự án là bản macOS nên không chạy được trong VM.

## 1. Kết quả chính bây giờ nói gì

| | FE (trong từng công ty) | RE (cả trong lẫn giữa các công ty) |
|---|---|---|
| Hệ số SA, mẫu chính | 2.245, p = 0.874 (wild 0.887) | **−4.805, p = 0.0498** |
| Hệ số SA, restricted sample | 0.407, p = 0.978 | −5.253, p = 0.030 |
| Khi thêm SIZE | 4.842, p = 0.827 | −2.519, p = 0.260 (mất ý nghĩa) |
| SA trễ 1 năm | 10.504, p = 0.377 | −3.745, p = 0.055 |
| Trụ S | −29.047, p = 0.026 (wild 0.069) | −8.274, p = 0.002 |

- **Ví dụ dễ hiểu:** FE so một công ty với chính nó qua các năm. RE so cả các công ty với nhau. Công ty lớn (SA thấp) thường có TESG cao, nên RE thấy quan hệ âm. Nhưng trong cùng một công ty, SA gần như không đổi qua 10 năm, nên FE không thấy gì.
- **Cách báo cáo diễn giải (phiên bản 3):** Hausman và Mundlak không bác bỏ RE, nên báo cáo dùng RE làm kết quả chính: SA âm, có ý nghĩa ở mức 5%, ủng hộ H1. FE chỉ được nhắc trong phần Hausman.
- **Vẫn giữ một câu ngắn về SIZE** (mục 4.3 và phần kết luận), vì Bảng 5 Panel B cho thấy hệ số RE mất ý nghĩa khi thêm SIZE (−2.519, p = 0.260). Bỏ câu này thì người đọc nhìn bảng sẽ thấy mâu thuẫn với phần chữ.
- **Rủi ro cần biết:** p = 0.0498 nằm sát ngưỡng 5% và **phụ thuộc vào cách chọn G**. Với cùng SE CR1 (t = −2.071), dùng t(23) (G = 24, như báo cáo) thì p = 0.0498, nhưng dùng t(21) (G = 22, như FE) thì **p = 0.051, tức không còn ý nghĩa ở mức 5%**. (Con số 0.051 mình tính tay từ t = −2.071, chưa có trong script.) Con số p ≈ 0.047 của script 06 dùng SE mặc định của linearmodels, không có hệ số G/(G−1), nên không so trực tiếp được. Nếu cô hỏi về giả định của RE (hiệu ứng công ty không tương quan với biến giải thích), câu trả lời trung thực là: giả định này khó bảo vệ vì SA gần như là hàm của quy mô.

## 2. Những điểm cần hỏi cô

- **FE hay RE là kết quả chính (#20). Đây là câu hỏi quan trọng nhất.**
  - Hausman χ²(6) = 2.94, p = 0.816 và Mundlak χ²(6) = 3.25, p = 0.776: cả hai đều không bác bỏ RE.
  - Theo quy tắc của brief §3.2 (p ≥ 0.05 thì RE chấp nhận được), RE sẽ là mô hình chính, và kết luận sẽ thành "ủng hộ yếu H1". Nhưng brief §3.3 lại yêu cầu two-way FE.
  - Báo cáo hiện trình bày hai mô hình ngang nhau và giải thích vì sao không nên đọc RE như hiệu ứng nhân quả. Cần cô chọn.
- **Winsorize Y (#19).** Đã làm theo yêu cầu của Tuấn. Nên báo cô là bản cũ không winsorize Y, và kết quả FE gần như giống hệt.
- **Cách tính p-value cho RE (quyết định mới, cần cô xác nhận).**
  - Dùng t(G−1) với G = 24, vì 2 công ty chỉ có 1 quan sát vẫn đóng góp vào RE. FE dùng G = 22.
  - Nếu dùng G = 22 cho RE (với SE CR1 như báo cáo) thì p = 0.051, tức là kết luận "có ý nghĩa ở mức 5%" đổi thành "chỉ ở mức 10%". Đây là điểm phải hỏi cô trước khi khẳng định.
  - RE không có wild bootstrap (thư viện `wildboottest` chỉ chạy trên OLS). Bảng ghi "n/a".
- **R² của hai mô hình.**
  - Bảng ghi within R² cho FE và overall R² cho RE.
  - Overall R² của FE trong linearmodels bị âm (−0.444), vì nó chỉ dùng hệ số dốc mà bỏ hiệu ứng công ty. Vì vậy không đưa vào báo cáo; con số vẫn có trong file xlsx.
- **Dữ liệu 2015 làm biến trễ (#6):** nếu cô không đồng ý thì lấy cột (3) và (4) của Bảng 4 làm kết quả chính.
- **Định nghĩa SA (#7):** brief khác Hadlock & Pierce ở 3 điểm. Script 07 (bản H&P đầy đủ) đã chạy lại với Y winsorize, vẫn null, nhưng chưa đưa vào báo cáo.
- **Phân tích between/within của script 06 (#21):** chưa đưa các hồi quy pooled/hybrid vào báo cáo.
  - Báo cáo có dùng 3 con số tính từ output của script 06: khoảng tin cậy của β, hiệu ứng tính theo 1 độ lệch chuẩn within, và MDE = 1.72.
  - Thêm một con số từ cùng file: RE β × độ lệch chuẩn between của SA = −3.82 điểm.
- **Các mục cũ vẫn còn:**
  - #1: làm cả 4 kiểm định độ vững.
  - #2: mẫu đoạn kết quả §6.2 của brief bàn SIZE.
  - #8: dummy theo trung vị chỉ dựa vào 5 công ty đổi trạng thái.
  - #10: hạn nộp và định dạng.
  - #11: Python thay vì R.

## 3. Hạn chế về dữ liệu

- **Chỉ 24 công ty**, 22 công ty có từ 2 quan sát trở lên. Ít cụm làm SE cluster dễ bị thiên lệch xuống.
- **TESG 2016 đến 2020 là điểm hồi tố:** cùng ngày công bố 31/03/2022.
- **3 quan sát 2025 bị mất** (1218, 1219, 1225, hạng W\*), do một quy tắc mới chỉ áp dụng từ kỳ 2026/12.
- **Danh sách công ty là ảnh chụp hiện tại của TEJ:** công ty nào từng thuộc ngành thực phẩm rồi chuyển ngành sẽ không xuất hiện.
- **TESG có thể đã gồm điều chỉnh Event Radar (D4).** Bằng chứng (R² 0.978, tương quan phần dư 0.77) là chạy ad hoc, chưa nằm trong script, nên không đưa vào báo cáo.

## 4. Hạn chế về phương pháp

- **SA gần như không đổi trong một công ty:** chỉ còn 0.32% phương sai sau khi bỏ hiệu ứng công ty và năm. FE có power thấp: MDE = 1.72 điểm TESG cho mỗi độ lệch chuẩn within của SA.
- **Giả định của RE khó bảo vệ:** RE cần hiệu ứng công ty không tương quan với biến giải thích. SA gần như là hàm của quy mô, mà quy mô gần như chắc chắn tương quan với đặc điểm riêng không quan sát được của công ty.
- **Công ty 1216** nằm ở vùng SA quay đầu (Size > 8.57). Script 06 bỏ 1216 ra thì FE β = 4.849, p = 0.744 (chưa đưa vào báo cáo).
- **Trụ S** âm ở cả FE và RE, nhưng có 4 điểm số được kiểm định, và hồi quy theo trụ chưa kiểm soát SIZE. Chỉ nên coi là gợi ý.

## 5. Kiểm tra chéo bằng Stata: hiện đã LỖI THỜI

- Các file `scripts/stata/*.do` và `outputs/stata/out/*` được viết và chạy cho bản cũ (Y không winsorize, chỉ FE). Quy tắc A3 trong `01_stata_independent.do` ghi rõ "TESG, E, S, G are NOT winsorized".
- **Đã chạy lại (07/11, 21:09):** 919/943 kiểm tra PASS; block H (RE) 401/401 PASS, Mundlak và Hausman khớp. 24 FAIL đều thuộc m2, mô hình chẩn đoán (GROWTH winsorize trên 219 dòng), khác Python theo thiết kế; m3 (cách Python làm) PASS toàn bộ. Có thể đưa lại câu "tái lập độc lập bằng Stata" vào báo cáo nếu muốn.
- (Ghi chú cũ) **Đã sửa do-file (07/11):** A3 winsorize Y; thêm RE (`xtreg, re vce(cluster firm)`, id 11-19) và block H trong `02_compare_python.do` để so cột RE. Cần chạy lại `01` rồi `02` trên Stata. Báo cáo vẫn bỏ câu "đã tái lập độc lập bằng Stata" cho tới khi block H PASS.
- Đã xác định (07/11): Mundlak lệch 3.37 so với 3.50 chỉ do hệ số mẫu nhỏ: Python thiếu `group_debias=True`. Script 04 nay dùng G/(G-1) x (N-1)/(N-K), cùng quy ước với các cột RE và với `xtreg, re vce(cluster)`; trên Y chưa winsorize Python cho 3.369739, trùng Stata. Hệ số và SE thường của RE trong Hausman khớp Stata tới 1e-5.

## 6. Về tài liệu tham khảo

- Mọi trích dẫn đã đối chiếu với toàn văn PDF trong `literature/`, ghi số trang theo tạp chí.
- **Fazzari et al. (1988):** URL Brookings lấy từ tìm kiếm web, nên mở ra kiểm tra lại.
- **Hong et al. (2012)** là working paper NBER, chưa qua bình duyệt.
- **Hai trang TEJ** là bản lưu PDF, không có URL. Nên dán URL thật vào khi có.
- **Slide TEJ-NCCU 2026 không được trích dẫn** vì có tuyên bố bản quyền cấm trích dẫn khi chưa được phép.

## 7. Việc Tuấn nên làm trước khi nộp

- Hỏi cô mục FE hay RE (#20) và cách tính p cho RE.
- Chạy lại Stata cross-check (mục 5) nếu muốn giữ câu tái lập độc lập.
- Xem lại trang đầu (tên, đơn vị, email).
- Nếu sửa bất kỳ script nào: chạy lại 02 đến 07, rồi chạy `outputs/report/build/` (README có lệnh).

## 8. Sắp xếp thư mục (2026-11-07)

- Cấu trúc theo brief §1.6: `raw_data/`, `scripts/`, `outputs/tables/`, `outputs/figures/`. Phần phụ trợ nằm trong `scripts/checks/`, `scripts/supplementary/`, `scripts/stata/`, `outputs/report/`, `outputs/stata/`, `archive/`. Sơ đồ đầy đủ ở `README.md`.
- Brief gọi ba file 02a, 02b, 02c, nhưng dữ liệu thô là một file `02_ifrs_concise_annual.xlsx` (một bảng TEJ chứa cả ba báo cáo). Không đổi tên hay tách file thô, vì `raw_data/` là read-only và script đang đọc theo tên hiện tại.
- Chú thích trong các script Python đã rút gọn: docstring đầu file chỉ còn mục đích, input, output, lệnh chạy; bỏ các tham chiếu kiểu `brief §`, `D18`, `CLAUDE.md`. Code không đổi: chạy lại 01 đến 07, mọi file .csv trong `outputs/tables/` và `data_clean/` giống hệt trước (md5).
- Do-file Stata chưa rút gọn chú thích, vì mình không chạy được Stata để kiểm tra; chỉ sửa đường dẫn sang `outputs/stata/`.
- Các tài liệu trong `docs/` viết trước ngày 07/11 vẫn ghi đường dẫn cũ (ví dụ `scripts/06_...`); đây là nhật ký lịch sử nên giữ nguyên.
