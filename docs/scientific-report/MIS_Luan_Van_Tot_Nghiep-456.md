
# **Chương 5** **Thực nghiệm, Đánh giá Hiệu năng và Tác** **động Nghiệp vụ**

Chương 4 đã hoàn tất việc thiết kếkhung giải pháp **VNAI** với bốn module nghiệp vụ, mô hình SCD
Type 2, pipeline AI lai ghép và khung tái lập SUPA-Bench. Chương này trình bày kết quảcác phép đo
định lượng đã thực hiện trên artifact huấn luyện và benchmark, đồng thời phân tích tác động nghiệp vụ
cùng các rủi ro còn lại. Khác với nhiều nghiên cứu báo cáo duy nhất một chỉsốtổng hợp, đềtài chủ
trương _tách bạch các tầng đo lường_ : chất lượng liên kết dữliệu ( _lineage audit_ ), chất lượng mô hình
ngôn ngữ(NER), chất lượng chuỗi đầu ra ( _end-to-end_ ) và chất lượng truy xuất ngữnghĩa ( _retrieval_ ).
Triết lý này phục vụhai mục tiêu: (i) cô lập được nguyên nhân khi một chỉsốtụt giảm, qua đó hỗtrợ
chẩn đoán hệthống; (ii) tránh diễn giải nhập nhằng giữa chất lượng dữliệu nghiệp vụvà chất lượng
mô hình học máy.
Tất cảsốliệu trong chương được trích trực tiếp từartifact của hệthống — nhật ký huấn luyện
PhoBERT NER, các tệp metric JSON trong thư mục `reports/`, và bảng tổng hợp đã _persist_ trong
schema ath. Các hạng mục chưa có artifact đo được sẽđược khai báo minh bạch là chưa báo cáo, tránh
giảđịnh sốliệu đểbảo vệtính trung thực khoa học.

## **5.1 Khung chỉsốđánh giá và mục tiêu đối chiếu**

### **5.1.1 Hệthống chỉsốđánh giá đa tầng**


Đềtài đềxuất một hệthống chỉsốđánh giá hai tầng, mỗi chỉsốgắn liền với một câu hỏi nghiên cứu
được phát biểu ởMục 1.2.3. Tầng đầu tiên (ký hiệu **P-***, _parametric_ ) đo trực tiếp tham sốđã học của
mô hình; tầng thứhai (ký hiệu **S-***, _structural_ ) đo đầu ra cấu trúc của toàn pipeline. Năm chỉsốcụthể
được liệt kê tại Bảng 5.1.
Sựtách bạch P-* và S-* phản ánh một quan sát phương pháp luận: một mô hình NER có F1 cao
chưa chắc cho ra chuỗi địa chỉchuẩn hoá đúng, vì còn các bước trung gian (retrieval, LLM, kiểm tra
phân cấp). Vì vậy, một báo cáo khoa học cần đo từng tầng riêng và chấp nhận rằng các chỉsốcó thể
không cùng xu hướng.


47


_5.2._ _THỰC NGHIỆM NHẬN DIỆN THỰC THỂTÊN CÓ GIÁM SÁT_


Bảng 5.1: Hệthống chỉsốđánh giá đa tầng của khung giải pháp VNAI


**Ký hiệu** **Tên đầy đủ** **Định nghĩa**


P-F1 Macro-F1 thực thể F1 tổng hợp do thư viện `seqeval` báo cáo trên tập kiểm định BIO,
(seqeval) đồng bộvới khoá `eval_f1` của Hugging Face Trainer [41].
P-Acc Token accuracy Tỷlệtoken được gán đúng nhãn trên toàn tập kiểm định, lưu ởkhoá
`token_accuracy` .
S-NER-EM Exact match cấp Tỷlệcâu có dãy nhãn dựbáo trùng hoàn toàn nhãn chuẩn (chưa có
câu của chuỗi nhãn trong artifact hiện tại).
S-E2E-EM Exact match chuỗi So khớp tuyệt đối sau chuẩn hoá NFC, cắt khoảng trắng đầu cuối và
địa chỉchuẩn hoá gom khoảng trắng nội bộ, giữa `pred_standardized` và tham
chiếu đóng băng.
S-RET Recall@k, MRR, Đo trên cặp `(old_address,` `address)` từ
top-1 string match `prq.ground_truth` ; truy vấn qua
`SiameseMGTE.retrieve_top_k` [6].

### **5.1.2 Ngưỡng Gate B làm tiêu chí đối chiếu**


Tài liệu phương pháp đồng hành thiết lập một ngưỡng nội bộký hiệu **Gate B**, yêu cầu cảP-F1 và
P-Acc đồng thời vượt 96% trên tập có giám sát. Mục đích của Gate B _không_ phải là ngưỡng công bố
trong cộng đồng học thuật, mà là điểm chốt nội bộtrước khi đặt mô hình vào chếđộtựđộng hoàn toàn
( _auto-accept_ ) trong môi trường vận hành thật. Với ngưỡng Gate B, đềtài có cơ sởđịnh lượng đểquyết
định khi nào pipeline được phép bỏqua bước rà soát thủcông.

## **5.2 Thực nghiệm Nhận diện Thực thểtên có giám sát**

### **5.2.1 Thiết lập thực nghiệm**


**Mô** **hình** **và** **tác** **vụ.** Mô hình PhoBERT [5] được tinh chỉnh cho tác vụphân loại token ( _token_
_classification_ ). Tập nhãn gồm nhãn nền `O` và các cặp `B-/I-` cho các kiểu thực thểđịa chỉ `STR`
(đường), `WDS` (xã/phường), `DST` (quận/huyện), `PRO` (tỉnh/thành), `NUM` (sốnhà), `NHB` (khu/khu phố),
`BLD` (toà nhà), `POI` (điểm quan tâm), `ALY` (ngõ/hẻm), `PCD` (mã bưu chính). Cấu hình lớp đầu ra hoàn
toàn nhất quán với mô tảởMục 4.5.
**Tập dữliệu.** Nguồn được ghi tại artifact: tập Hugging Face công khai
`dathuynh1108/ner-address-standard-dataset` ởchếđộ _streaming_, giới hạn 4000 mẫu
huấn luyện và 800 mẫu kiểm định ( `train_cap`, `eval_cap` ). Việc cốđịnh hai siêu tham sốnày
nhằm khoá điều kiện ban đầu của lần thực nghiệm, là một thực hành tái lập ( _reproducibility_ ) được
khuyến nghịtrong các báo cáo NLP hiện đại.
**Siêu tham sốhuấn luyện.** Một _epoch_ hoàn chỉnh, tốc độhọc 2 _×_ 10 _[−]_ [5], kích thước batch là 8.

### **5.2.2 Kết quảđịnh lượng trên tập kiểm định**


Các giá trịtại Bảng 5.2 được trích trực tiếp từnhật ký huấn luyện (các khoá `eval_results` và
`token_accuracy` trong tệp `training_log.json` ).
**Hiệu** **năng** **suy** **luận** **tại** **bước** **eval.** Cùng nhật ký ghi nhận thời gian chạy đánh giá khoảng
17 _,_ 25 giây, lưu lượng xửlý xấp xỉ 46 _,_ 38 mẫu/giây và khoảng 2 _,_ 90 bước/giây (lần lượt qua các


48


_5.3._ _KIỂM THỬNHẤT QUÁN DỮLIỆU LINEAGE (AUDIT BRIDGE)_


Bảng 5.2: Kết quảđịnh lượng PhoBERT NER trên tập kiểm định 800 mẫu


**Chỉsố** **Khoá artifact** **Giá trị**


F1 macro (seqeval) `eval_f1` **93.76 %**
Precision `eval_precision` 92.90 %
Recall `eval_recall` 94.64 %
Token accuracy `token_accuracy` **97.15 %**
Loss kiểm định `eval_loss` 0 _,_ 1573


khoá `eval_runtime`, `eval_samples_per_second`, `eval_steps_per_second` ). Đây là
sốliệu thuần đo trên một cấu hình phần cứng cụthểcủa lần huấn luyện đã đóng băng, không đại diện
cho lưu lượng end-to-end của toàn pipeline (vốn còn các tầng retrieval và LLM nặng hơn).

### **5.2.3 Đối chiếu với Gate B và thảo luận**


Với P-F1 đạt _≈_ 93 _._ 76 % và P-Acc đạt _≈_ 97 _._ 15 %, _cảhai chỉsốđều chưa đạt ngưỡng_ 96% _đồng thời_
_theo định nghĩa Gate B_ . Trên tinh thần báo cáo trung thực, cần nhấn mạnh rằng kết quảnày không phủ
nhận khảnăng cải thiện của khung giải pháp; mà chỉphản ánh _trạng thái một lần huấn luyện đã đóng_
_băng_ trong artifact hiện tại. Ba hướng cụthểcó thểđưa kết quảvượt Gate B đã được xác định: thứ
nhất, mởrộng tập huấn luyện vượt mốc 4000 mẫu (đặc biệt bổsung dữliệu nội bộchứa viết tắt vùng
miền và địa danh dân gian); thứhai, tăng sốepoch kèm _early stopping_ theo F1 trên tập _dev_ ; thứba,
tinh chỉnh trên miền dữliệu nội bộthay vì chỉsửdụng tập công khai.
Điểm quan trọng vềphương pháp luận: việc công bốkhoảng cách so với Gate B thay vì che giấu
chính là _một đóng góp khoa học_ của đềtài — nó định vịrõ _khoảng cách còn lại_ giữa bằng chứng khái
niệm ( _proof-of-concept_ ) và yêu cầu vận hành nghiêm ngặt, tạo cơ sởkhách quan cho các vòng huấn
luyện tiếp theo.

## **5.3 Kiểm thửnhất quán dữliệu lineage (Audit Bridge)**

### **5.3.1 Mục tiêu và phương pháp**


**Audit bridge** là một phép đo _chất lượng join dữliệu_ giữa hàng đợi xửlý địa chỉ
( `prq.address_cleansing_queue` ) và các bảng master hành chính trong schema mat. Phép đo
này _không_ đo F1 của mô hình AI; thay vào đó, nó kiểm chứng giảthiết nền tảng cho mọi phép đo
end-to-end: dữliệu khai báo phân cấp hành chính của các bản ghi địa chỉcó khớp với master hay
không. Nếu một tỷlệlớn bản ghi không khớp _lineage_, mọi metric E2E xây trên đó sẽbịnhiễu —
không phải do mô hình kém mà do dữliệu chưa sạch.
Phương pháp đo bao gồm ba cổng ( _gates_ ) tuần tự: **G1** kiểm tra không có khoá `old_id` bịtrùng
trong tập _smoke test_ trên master; **G2** đo tỷlệbản ghi queue rơi vào kết nối _triple inner join_ ba cấp (tỉnh,
huyện, xã) chuẩn; **G3** đo tỷlệcăn chỉnh giữa các cột _denormalized_ ( `province_id`, `district_id`,
`ward_id` trong queue) với phân cấp lưu trong mat.

### **5.3.2 Kết quảkiểm thử**


Bảng 5.3 tổng hợp kết quảaudit bridge tại thời điểm chốt artifact.


49


_5.3._ _KIỂM THỬNHẤT QUÁN DỮLIỆU LINEAGE (AUDIT BRIDGE)_


Bảng 5.3: Kết quảaudit bridge giữa hàng đợi địa chỉvà master hành chính


**Hạng mục** **Giá trị**


Tổng sốbản ghi hàng đợi 437862 dòng
Cổng G1 (không trùng `old_id` trong smoke test) Đạt (cờ1)
Cổng G2 (tỷlệrơi vào triple inner join) **96.61 %**
Cổng G3 (tỷlệcăn chỉnh denormalized với phân cấp master) **96.79 %**
Sốdòng không thoảđiều kiện G3 14044 dòng


Quy mô 437862 bản ghi cho thấy tải nghiệp vụthực tếđáng kể, đủtin cậy vềmặt thống kê. Hai
cổng G2 và G3 đạt trên 96% chứng tỏphần lớn dữliệu trong hàng đợi có liên kết chuẩn với master; tuy
nhiên, 14044 dòng (tương đương _≈_ 1 _,_ 45 % tổng số) chưa thoảG3 — một khối lượng đáng kểnếu xét
tuyệt đối. Hình 5.1 trực quan hoá phân phối các nhóm thoả/không thoảcổng.


Hình 5.1: Phân phối kết quảaudit bridge trên hàng đợi địa chỉ.

### **5.3.3 Ý nghĩa đối với đánh giá AI end-to-end**


TỷlệG3 đạt 96.79 % mang ba ý nghĩa khoa học. _Thứnhất_, nó là điều kiện tiên quyết đểdiễn giải các
chỉsốS-E2E-EM ởcác mục tiếp theo: nếu dữliệu nguồn đã không khớp lineage, không thểquy mọi
sai lệch vềphía mô hình. _Thứhai_, nó cung cấp _một tham sốchiến lược cho công tác làm sạch dữliệu_ :
14044 dòng cần được tách _stratum_ khi báo cáo metric E2E đểtránh thiên kiến. _Thứba_, nó định vị
_chính sách reconcile_ cần áp dụng trước khi vận hành tựđộng — không một mô hình AI nào có thểlàm
tốt trên dữliệu mâu thuẫn nội tại với master.


50


_5.4._ _KHUNG THỰC NGHIỆM SUPA-BENCH_

## **5.4 Khung thực nghiệm SUPA-Bench**

### **5.4.1 Kịch bản đánh giá cơ bản**


Như đã trình bày ởMục 4.9, SUPA-Bench tách cohort từbảng `prq.ground_truth` (chỉđọc), áp
nhiễu tổng hợp deterministic theo seed, sau đó so khớp chuỗi dựđoán với hai tham chiếu đóng băng
( `ref_address_v2` là hậu cải cách, `ref_address_v1` là tiền cải cách). Bảng 5.4 ghi nhận kết
quảlần chạy cơ bản đầu tiên.


Bảng 5.4: Kết quảSUPA-Bench cơ bản (1000 mẫu, kịch bản oracle)


**Hạng mục** **Giá trị**


Cỡmẫu yêu cầu / thực tếthu được 1000 / 1000
Sốspecimen / sốmẫu có dựđoán không rỗng 1000 / 1000
EM@v2 (so `ref_address_v2` ) **100.0000 %**
EM@v1 (so `ref_address_v1` ) 3.5000 %
Profile nhiễu SUP-1.0.0
Hạt giống ngẫu nhiên ( _seed_ ) 42
Commit Git tại bước extract `3358f90a76deb66343c2b23f5a0`

### **5.4.2 Diễn giải khoa học và giới hạn của kịch bản oracle**


TỷlệEM@v2 đạt 100% trên toàn bộ1000 mẫu _tương thích với kịch bản oracle_, trong đó cờvận hành
`–preds-demo-ref-v2` sao chép trực tiếp cột `ref_address_v2` sang `pred_standardized` .
Mục đích của oracle là _kiểm tra tính đúng đắn của chuỗi đánh giá_ ( _smoke test_ : cohort _→_ nhiễu _→_
import _→_ eval _→_ aggregate), _không_ chứng minh khảnăng khái quát hoá của mô hình chuẩn hoá thực
tế. Ngược lại, EM@v1 = 3 _,_ 5 % phản ánh đúng mức trùng khớp tuyệt đối giữa chuỗi dựđoán (trùng
v2) và chuỗi tham chiếu tiền cải cách (v1); khoảng cách lớn là hệquảcó thểdựđoán được khi hai
chuỗi tham chiếu thuộc hai phiên bản hành chính khác nhau.
**Kịch bản báo cáo mô hình thật.** Đểcó chỉsốS-E2E-EM phản ánh pipeline AI thực sự, cần ba
bước: (i) chạy module chuẩn hoá ngoài trên CSV specimen sau nhiễu đểsinh `pred_standardized` ;
(ii) nhập trởlại bằng lệnh `import-preds` kèm `–source-note` mô tảcheckpoint mô hình và cấu
hình; (iii) chạy lại `eval` . Giá trịEM thu được khi đó mới phản ánh trung thực năng lực của hệthống
và mới có ý nghĩa đối chiếu với các nghiên cứu khác.

### **5.4.3 Thực nghiệm phân tầng với kiểm chứng chéo K = 5**


**Cơ sởkhoa học của phân tầng và lặp K = 5**


Một báo cáo chỉvới một lần chạy ngẫu nhiên duy nhất có hai nguy cơ phương pháp luận: (a) **thiên kiến**
**lựa chọn** ( _selection bias_ ) khi cohort vô tình chứa nhiều mẫu “dễ”; (b) thiếu ước lượng cho **độổn định**
( _stability_ ) của metric giữa các cohort cùng quy tắc lấy mẫu. Đểhoá giải đồng thời hai nguy cơ trên, đề
tài đềxuất một thực nghiệm phân tầng kết hợp lặp K = 5 lần độc lập, có bốn căn cứkhoa học rõ ràng.
_Thứnhất_, lấy mẫu phân tầng ( _stratified sampling_ ) trên `prq.ground_truth` với cơ cấu tỷlệcố
định bốn nhóm D1–D4 đảm bảo cohort không bịnghiêng vềmột loại địa chỉduy nhất; bốn nhóm bao
quát đầy đủcác _kiểu khó_ của miền bài toán (đô thịphức tạp, nhiễu cao, lưỡng thời hành chính, ranh giới


51


_5.4._ _KHUNG THỰC NGHIỆM SUPA-BENCH_


không gian). _Thứhai_, lặp K = 5 lần với các _seed_ lệch bước nhưng cùng cơ cấu tỷlệcho phép ước lượng
độlệch chuẩn của từng chỉsố— một đặc tính cần thiết đểbáo cáo khoảng tin cậy thay vì điểm sốđơn lẻ.
_Thứba_, thực nghiệm này gắn trực tiếp với _khoảng trống nghiên cứu cốt lõi_ : khảnăng duy trì tính nhất
quán địa giới trong giai đoạn chuyển đổi hành chính cực đoan 2025. Tầng D3 cốý chứa thực thểtiền/hậu
cải cách và các quan hệ `MERGES_INTO` trên đồthị `mat.unit_edge`, qua đó tạo bằng chứng cho
hiệu lực của _kiến trúc nhận thức thời điểm_ (epoch detector, ánh xạSCD Type 2, ACS với thành phần
_V_ temporal). _Thứtư_, bảng tổng hợp được _persist_ trong `ath.supa_stratified_eval_summary`
(payload JSON đầy đủkèm phạm vi `run_id` và `git_commit` ) tạo _bằng_ _chứng_ _thực_ _nghiệm_ _có_
_provenance_, phục vụtái lập và bảo vệluận điểm trong quá trình phản biện.


**Cơ cấu phân tầng D1–D4 và ngưỡng kỳvọng**


Mỗi lần chạy lấy _n_ = 2 _._ 000 mẫu phân thành bốn tầng theo cơ cấu `strat-v1` (Bảng 5.5, minh hoạtại
Hình 5.2). Cơ cấu này không phải là phân phối tựnhiên của dữliệu mà là một _phân phối có chủđích_
nhằm cô lập các kiểu khó.


Hình 5.2: Phân phối cohort SUPA-Bench theo cơ cấu `strat-v1`, _n_ = 2 _._ 000/lần chạy.


Các ngưỡng kỳvọng đểđối chiếu khi pipeline chuẩn hoá thật được kích hoạt (không sửdụng
oracle) được tổng hợp tại Bảng 5.6. Cần lưu ý: ngưỡng này _chỉcó giá trịđối chiếu_ khi đầu vào là dự
đoán của pipeline AI thật, không phải kịch bản oracle.


**Kết quảthực nghiệm K = 5 trên kịch bản oracle**


Đợt thực nghiệm `replicate-stratified` với K = 5, _n_ = 2 _._ 000 mỗi lần chạy, profile
`STRATIFIED-strat-v1`, các _seed_ từ 970 _._ 156 _._ 401 đến 970 _._ 160 _._ 401, `run_id` từ56 đến 60. Artifact
tham chiếu: `reports/supa_benchmark_aggregate_stratified_k5_oracle_run56`
`-60_20260513.json` ; bảng tổng hợp đã được _persist_ thành một dòng trong
`ath.supa_stratified_eval_summary` . Kết quả _rollup_ năm lần chạy được trình bày tại
Bảng 5.7.


52


_5.5._ _ĐÁNH GIÁ TRUY XUẤT NGỮNGHĨA_


Bảng 5.5: Cơ cấu phân tầng `strat-v1` cho cohort SUPA-Bench ( _n_ = 2 _._ 000/lần chạy)


**Tầng** **Tỷlệ** **Đặc trưng và mục tiêu kiểm thử**


D1 40% Chuẩn hoá đô thị: địa chỉcó cấu trúc phức tạp với nhiều xuyệt (ngõ, ngách, hẻm,
kiệt, tổ, cụm) tại đô thịlớn hoặc tín hiệu `popular` cao trong ground truth.
D2 20% Nhiễu cao: dữliệu không dấu, sai chính tảnặng, viết tắt vùng miền — kiểm tra độ
bền của tầng trích thực thể(PhoBERT NER) và downstream khi đầu vào cực đoan
(profile `SUP-D2-1.0.0` ).
D3 30% Lưỡng thời và biến động: địa chỉsửdụng thực thểhành chính tiền cải cách (trước
01/07/2025) — kiểm tra module SCD Type 2 và quan hệ `MERGES_INTO` trên mat.
D4 10% Ranh giới không gian: toạđộGPS nằm sát ranh giới hành chính — kiểm tra hiệu
chỉnh polygon (PostGIS + `mat.area_polygon` ).


Bảng 5.6: Ngưỡng kỳvọng cho pipeline chuẩn hoá thật (không oracle)


**Chỉsố** **Ngưỡng** **Mức kỳvọng**


Component F1 (Tỉnh/Thành phố) _≥_ 98 _,_ 5 % Rất cao
Component F1 (Phường/Xã) _≥_ 92 _,_ 0 % Cao
Exact Match toàn chuỗi (EM@v2) _≥_ 85 _,_ 0 % Trung bình
Mean latency / địa chỉ _≤_ 120 ms Cao
P95 latency _≤_ 500 ms Cao
Throughput (chếđộbatch) _≥_ 22 _,_ 0 addr/s Trung bình


**Diễn giải nghiêm túc.** Sốliệu trên _chỉchứng minh chuỗi vận hành_ của thực nghiệm phân tầng đa
lần chạy: cơ chếlấy mẫu theo quota D1–D4 hoạt động đúng, lệnh `replicate-stratified` sinh
được năm cohort độc lập, lệnh `aggregate-runs` `–persist-ath` ghi đúng vào
`ath.supa_stratified_eval_summary` . _Không_ thểkết luận pipeline AI đạt EM@v2 = 100 %
hay F1 thành phần = 100 % trên thực tế; những sốliệu trên là kết quảoracle, có giá trịvềmặt vận hành
chuỗi đánh giá chứkhông phải vềmặt năng lực mô hình.
**Hạng mục latency, P95 và throughput chưa báo cáo.** Đợt chạy batch 56–60 chưa kích hoạt cột
`latency_ms` trong CSV preds (import được thực hiện trước khi bật ghi đo); do đó các chỉsố(3)–(5)
trong bảng ngưỡng kỳvọng _chưa được đo_ . Đểbổsung, cần chạy lại `import-preds` với CSV có cột
`latency_ms` từpipeline thật, hoặc chấp nhận sửdụng đo _thời gian câu lệnh ingest DB_ làm thay thế
bổtrợ(không thay thếđo từpipeline inference).
**Quan sát thống kê đáng chú ý.** Mặc dù dựđoán giống nhau giữa năm lần chạy (oracle), EM@v1
dao động từ 15 _,_ 55 % đến 16 _,_ 65 % với độlệch chuẩn 0 _,_ 44. Đây không phải lỗi tính toán mà là một _tín_
_hiệu đo lường có ý nghĩa_ : cohort khác nhau sẽchứa các tỷlệkhác nhau của các _stratum_ có mức trùng
chuỗi v1/v2 khác nhau, đặc biệt từtầng D3 (lưỡng thời). Quan sát này hỗtrợluận điểm rằng K = 5
cohort độc lập là cần thiết đểbáo cáo khoảng tin cậy — một lần chạy duy nhất có thểcho ra giá trịtừ
15 _,_ 5 % đến 16 _,_ 7 % mà không có cơ chếphân biệt. Hình 5.3 thểhiện trực quan biên độdao động này.

## **5.5 Đánh giá Truy xuất Ngữnghĩa**


**Trạng thái artifact.** Các chỉsốS-RET (R@k, MRR, top-1 string match) chưa có giá trịmặc định trong
kho mã — chỉxuất hiện sau khi chạy thực sựscript đánh giá. Hệthống đã chuẩn bịđầy đủhạtầng:


53


_5.5._ _ĐÁNH GIÁ TRUY XUẤT NGỮNGHĨA_


Bảng 5.7: Kết quảthống kê K = 5 với cohort phân tầng _n_ = 2 _._ 000 (kịch bản oracle)


**Chỉsố** **Mean** **Std** **Min** **Max** **Ghi chú**


EM@v2 (%) 100,00 0,00 100,00 100,00 Oracle: `pred` = ref v2
EM@v1 (%) 16,14 0,44 15,55 16,65 `pred` v2 so khớp tuyệt đối chuỗi v1
F1 Đường (chuỗi, %) 100,00 0,00 100,00 100,00 Cùng điều kiện oracle
F1 Phường (%) 100,00 0,00 100,00 100,00 F1 Quận (%) 100,00 0,00 100,00 100,00 F1 Tỉnh/TP (%) 100,00 0,00 100,00 100,00 

Hình 5.3: Dao động EM@v1 trên năm lần chạy K = 5 độc lập với cohort phân tầng.


tập đo là cặp `(old_address,` `address)` từ `prq.ground_truth`, _corpus_ là tập `address`
đã khửtrùng lặp, truy vấn qua phương thức `SiameseMGTE.retrieve_top_k` với checkpoint
`Alibaba-NLP/gte-multilingual-base` .
**Quy trình thực hiện.** Script `scripts/experiments/eval_retrieval_mgte.py` (hoặc
tương đương qua `python` `-m` `app.ai.evaluate_retriever` ) hỗtrợba tham sốchính: `–k-list`
(ví dụ _{_ 1 _,_ 5 _,_ 10 _,_ 20 _}_ ), `–out-json` (đường dẫn artifact), và `–persist-db` (ghi một dòng vào bảng
`ath.retrieval_eval_run` ).
Điều kiện tiên quyết là migration `20260512_retrieval_eval_and_supa_metrics.sql`
đã được áp lên cơ sởdữliệu. Giao diện web tại mục _Lịch_ _sửthực_ _nghiệm_ đọc qua endpoint `GET`
`/api/experiments/retrieval-runs` đểliệt kê các lần chạy đã _persist_ .
**Phương pháp luận bổsung.** Khi so sánh hai _snapshot_ mô hình, cần giữcốđịnh bốn tham số:
`model_name`, giới hạn corpus `limit`, `top_k` và danh sách `k_list` ; đồng thời ghi `git_commit`
vào cảJSON và DB. Định nghĩa `recall@k` là trùng khớp chuỗi đầy đủvới tham chiếu vàng trong
top- _k_ ứng viên — một định nghĩa nghiêm ngặt phù hợp bài toán chuẩn hoá.


54


_5.6._ _KỊCH BẢN ĐÁNH GIÁ END-TO-END TRÊN ĐỊA CHỈTHỰC TẾ_

## **5.6 Kịch bản đánh giá End-to-End trên địa chỉthực tế**


Theo thiết kếphương pháp đã trình bày, ba kịch bản phân tầng độkhó được dựkiến đo bằng S-E2E-EM:


- **S1 — Đầy đủcó master:** chuỗi địa chỉđầy đủkèm các trường phân cấp tỉnh–huyện–xã đã hợp lệ
trên master. Mục tiêu: kiểm tra giới hạn trên ( _upper bound_ ) của pipeline khi đầu vào thuận lợi nhất.


- **S2 — Chỉ** **`raw_address`** **:** duy nhất chuỗi thô, không có gợi ý lineage. Mục tiêu: kiểm tra năng lực
bóc tách thuần tuý từNER + retrieval, vì không có ràng buộc cứng từtrường khai báo.


- **S3 — Chứa tên hành chính cũ hoặc viết tắt:** đầu vào dùng định danh tiền cải cách hoặc viết tắt
phổbiến. Mục tiêu: kiểm tra trực tiếp _epoch detector_ và ánh xạSCD trong điều kiện thực tế.


**Trạng thái báo cáo.** Bảng sốliệu theo từng kịch bản _chưa có trong artifact đồng bộhiện tại_ . Việc
điền cần chạy pipeline trên tập mẫu được lấy có kiểm soát, ghi nhận cùng `git_commit`, giới hạn
_batch_ và phiên bản LLM cụthể. Khoảng trống này được công bốđểcộng đồng giám sát và đềtài sẽbổ
sung ởcác vòng thực nghiệm tiếp theo.

## **5.7 Tối ưu hoá vận hành và đo lường hiệu năng**


Ba kỹthuật tối ưu hoá đã được đềxuất hoặc cấu hình trong hệthống, song mức độlợi ích định lượng
end-to-end _chưa_ được tổng hợp trong một báo cáo đơn ngoại trừsốliệu suy luận NER ởMục 5.2.2.
_Thứnhất_, **giới hạn corpus khi nhúng** ( _corpus limit_ ): giảm thời gian khởi động và bộnhớ, đổi lấy
rủi ro giảm `recall` của tầng retrieval. Đểđịnh lượng đánh đổi, cần đo song song thời gian khởi động
( _warmup_ ) và R@k khi thay đổi tham số.
_Thứhai_, **lượng tửhoá LLM 4-bit và 8-bit** ( _4-bit/8-bit quantization_ ): cấu hình mặc định của khung
giải pháp đềcập lượng tửhoá 4-bit qua BitsAndBytes [48] cho `Qwen/Qwen2.5-1.5B-Instruct`

[47]. Đánh đổi giữa độchính xác, VRAM và độtrễcần _profiler_ riêng cho từng cấu hình GPU mục tiêu.
_Thứba_, **kích thước batch ghi cơ sởdữliệu** ( `db_batch_size` ): cân bằng giữa _throughput_ xửlý
hàng loạt và tải giao dịch trên PostgreSQL. Lựa chọn tham sốnày phụthuộc loại storage (SSD/NVMe)
và cấu hình `shared_buffers` .
**Sốliệu throughput đã đo.** Như đã trình bày tại Mục 5.2.2, lưu lượng xửlý tại bước eval NER đạt
_≈_ 46 _,_ 38 mẫu/giây trên 800 mẫu kiểm định. Sốliệu này _không thểsuy ra_ throughput của chuỗi đầy đủ
NER + retrieval + LLM, vốn còn các tầng tốn kém hơn vềtính toán.

## **5.8 Tác động Nghiệp vụvà Phân tích Rủi ro**

### **5.8.1 Tác động tích cực trên căn cứđịnh lượng**


Trên cơ sởcác phép đo audit và NER đã trình bày, đềtài rút ra ba kết luận vềtác động nghiệp vụtích
cực.
_Thứnhất_, quy mô 437862 bản ghi trong hàng đợi tại một thời điểm đo cho thấy nhu cầu tựđộng
hoá là có thật và cấp thiết — nếu xửlý thủcông, công sức kiểm tra một bản ghi chỉmột phút cũng
vượt 7 _._ 000 giờ-người, một quy mô không khảthi.


55


_5.9._ _TỔNG KẾT CHƯƠNG_


_Thứhai_, tỷlệ96.61 % bản ghi rơi vào lineage chuẩn G2 chứng minh dữliệu nguồn đủchất lượng
đểcác phân tích và huấn luyện gắn với master vận hành được. Nếu tỷlệnày thấp (ví dụdưới 80%),
khung giải pháp sẽphải đầu tư đáng kểvào lớp tiền xửlý trước khi triển khai AI.
_Thứba_, khung SUPA-Bench cùng NER có giám sát cho phép báo cáo tiến bộ _có kiểm soát phiên_
_bản_ : mỗi cải tiến mô hình sinh ra một bản ghi _persist_ với `git_commit`, `run_id`, `seed`, đảm bảo
tính minh bạch và khảnăng truy vết. Đây là cơ sởđểdoanh nghiệp có thểtựtin đầu tư mởrộng pipeline.

### **5.8.2 Rủi ro và biện pháp giảm thiểu**


Đềtài cũng nhận diện ba nhóm rủi ro cần được khắc phục trong các vòng phát triển tiếp theo.
_Rủi ro 1: khoảng cách tới Gate B trên NER._ P-F1 và P-Acc chưa đồng thời vượt 96% cho thấy mô
hình hiện tại không đủtin cậy đểvận hành chếđộtựđộng hoàn toàn ( _auto-accept_ ). _Biện pháp:_ duy
trì _human-in-the-loop_ trên các bản ghi có ACS thấp; mởrộng tập huấn luyện trên dữliệu nội bộ; tinh
chỉnh trên miền ( _domain adaptation_ ).
_Rủi ro 2: ∼_ 14 _._ 044 _bản ghi không thoảG3._ Nếu các bản ghi này được trộn ngẫu nhiên vào báo
cáo E2E, metric sẽbịlệch không vì lỗi mô hình. _Biện pháp:_ tách _stratum_ khi báo cáo; áp dụng _rule_
_reconcile_ hoặc _re-sync_ master đểgiảm dần khối lượng.
_Rủi ro 3: LLM sinh chuỗi lệch khỏi ứng viên retrieval hoặc master._ Mô hình ngôn ngữlớn có thể
sinh chuỗi hợp ngữpháp nhưng không thuộc tập hành chính hợp lệ(hiện tượng _hallucination_ ). _Biện_
_pháp:_ ràng buộc đầu ra theo _schema_ JSON cốđịnh; áp dụng _constrained decoding_ khớp tập ứng viên
top- _k_ ; kiểm tra phân cấp Phường _∈_ Quận _∈_ Tỉnh bằng thành phần _V_ hier trong công thức ACS.

## **5.9 Tổng kết chương**


Chương này đã trình bày kết quảthực nghiệm trên ba mặt phẳng đo lường tách biệt. Trên _chất lượng_
_mô hình ngôn ngữ_, PhoBERT NER đạt P-F1 _≈_ 93 _._ 76 % và P-Acc _≈_ 97 _._ 15 % — vượt mức tham khảo
của các nghiên cứu trước nhưng chưa đạt ngưỡng nội bộGate B 96%. Trên _chất lượng dữliệu lineage_,
audit bridge ghi nhận G2 = 96.61 % và G3 = 96.79 % trên quy mô 437862 bản ghi — mức cao nhưng
vẫn còn 14044 dòng cần xửlý nghiệp vụ. Trên _chất lượng chuỗi end-to-end_, SUPA-Bench đã chứng
minh chuỗi đánh giá vận hành đúng trên kịch bản oracle (cảlần chạy đơn 1000 mẫu và lần chạy phân
tầng K = 5 với _n_ = 10 _._ 000 tổng), tạo nền tảng cho các đo lường tiếp theo trên pipeline thật.
Đóng góp khoa học cốt lõi của chương này có ba luận điểm. _Thứnhất_, hệthống chỉsốP-* và S-*
phân tách phương pháp luận giữa chất lượng tham sốmô hình và chất lượng cấu trúc đầu ra, hỗtrợ
chẩn đoán có hệthống thay vì báo cáo đơn chỉsố. _Thứhai_, khung audit bridge giải quyết một vấn đề
thường bịbỏqua trong các nghiên cứu chuẩn hoá địa chỉ: đảm bảo điều kiện đầu vào sạch trước khi
quy kết sai lệch vềmô hình. _Thứba_, thực nghiệm phân tầng K = 5 với bảng tổng hợp _persist_ trong ath
thiết lập một chuẩn báo cáo có _provenance_ đầy đủ, sẵn sàng cho mọi vòng thực nghiệm trong tương lai.
Chương 6 đối chiếu các kết quảnày với mục tiêu nghiên cứu ban đầu, tổng hợp đóng góp khoa học,
ghi nhận các hạn chếvà đềxuất hướng phát triển ưu tiên đóng vòng làm giàu không gian tựđộng.


56


# **Chương 6** **Kết luận và Hướng phát triển**

Đềtài được thực hiện trong bối cảnh cuộc cải cách hành chính toàn quốc năm 2025 tạo ra “cú sốc dữ
liệu” chưa có tiền lệvới hạtầng thông tin doanh nghiệp Việt Nam. Khung giải pháp **VN Address In-**
**telligence** (VNAI) được thiết kếvà hiện thực với tham vọng giải quyết đồng thời bốn bài toán mà chưa
nghiên cứu nào trước đây giải quyết một cách tích hợp: đồng bộtựđộng danh mục hành chính, chuẩn
hoá địa chỉphi cấu trúc bằng AI đa tầng, xác thực không gian bằng thuật toán hình học, và làm giàu dữ
liệu đa nguồn theo mô hình thác nước. Chương này tổng kết các kết quảđạt được, đối chiếu với mục
tiêu nghiên cứu, làm rõ đóng góp khoa học, ghi nhận các hạn chếcòn tồn tại, và đềxuất các hướng
phát triển ưu tiên.

## **6.1 Tổng kết các kết quảđạt được**


Các kết quảcủa đềtài có thểđược phân thành ba nhóm theo phương diện trình bày: kiến trúc và triển
khai, định lượng đo được, và phương pháp khoa học.

### **6.1.1 Kết quảvềkiến trúc và triển khai**


Đềtài đã hiện thực hoá một nền tảng thống nhất bao gồm sáu thành phần cốt lõi. _Thứnhất_, cơ sởdữ
liệu quan hệPostgreSQL với phân tách bốn schema chuyên biệt (mat, osm, ath, prq) làm nền tảng dữ
liệu bền vững cho master hành chính, dữliệu OpenStreetMap, hub AI và hàng đợi xửlý. _Thứhai_, lớp
API REST trên FastAPI với hơn sáu mươi _endpoint_ cùng giao diện web tĩnh phục vụvận hành và thực
nghiệm. _Thứba_, luồng đồng bộtựđộng từnguồn danh mục hành chính NSO kết hợp cơ chếSCD Type
2 [8] và đồthịquan hệđơn vị( `mat.unit_edge` ) cho phép quản lý vòng đời thực thểhành chính với
các quan hệ `MERGES_INTO`, `SPLIT_FROM`, `RENAMES_TO` . _Thứtư_, pipeline AI xếp tầng tích hợp
ba mô hình chuyên biệt: PhoBERT cho NER [5], mGTE cho retrieval [6], và họQwen cho tinh chỉnh

[47] với lượng tửhoá 4-bit [48]. _Thứnăm_, module geospatial xửlý polygon, kiểm tra điểm thuộc vùng,
báo cáo _mismatch_ và _edge inject_ cho hiệu chỉnh GPS gần biên. _Thứsáu_, khung đánh giá SUPA-Bench
trên ground truth chỉđọc với khảnăng tái lập đầy đủ.

### **6.1.2 Kết quảđịnh lượng từartifact**


Các phép đo đã thực hiện trên artifact cho ba kết quảđịnh lượng chính. PhoBERT NER đạt F1 kiểm
định (seqeval) _≈_ 93 _._ 76 % và token accuracy _≈_ 97 _._ 15 % trên tập 800 mẫu kiểm định công khai. Audit


57


_6.2._ _ĐỐI CHIẾU VỚI MỤC TIÊU NGHIÊN CỨU_


bridge cho thấy phần lớn bản ghi hàng đợi khớp lineage và phân cấp master ởmức trên 96%, với quy
mô 437862 dòng trong lần đo. SUPA-Bench đã chứng minh chuỗi đánh giá end-to-end hoạt động đúng
trên kịch bản oracle (100.0000 % với 1000 mẫu trong lần chạy đơn và 100 _,_ 00 % _±_ 0 _,_ 00 với năm lần
chạy phân tầng K = 5, mỗi lần 2 _._ 000 mẫu), đồng thời làm rõ giới hạn diễn giải khi so với chuỗi tham
chiếu tiền cải cách v1 (EM@v1 _≈_ 16 _,_ 14 % _±_ 0 _,_ 44).
Đặc biệt, bảng tổng hợp K = 5 đã được _persist_ thành một dòng trong
`ath.supa_stratified_eval_summary` với phạm vi `run_id` 56–60 và `git_commit` đầy
đủ, tạo _bằng chứng tái lập_ cho mọi vòng thẩm định trong tương lai.

### **6.1.3 Kết quảvềphương pháp khoa học**


Đềtài cốđịnh bốn thực hành phương pháp khoa học làm chuẩn mực cho mọi thực nghiệm: (i) _prove-_
_nance_ đầy đủqua bốn yếu tố( `git_commit`, `rng_seed`, `noise_profile_id`, `source_note` );
(ii) tách bạch đo lường giữa chất lượng dữliệu lineage (audit) và chất lượng mô hình AI (NER, E2E);
(iii) phân biệt rõ kịch bản oracle với kịch bản pipeline thật đểtránh phóng đại năng lực; (iv) lưu trữ
bảng tổng hợp trong schema ath với payload JSON đầy đủ, cho phép truy hồi và đối chiếu sau này.

## **6.2 Đối chiếu với Mục tiêu Nghiên cứu**


Ba câu hỏi nghiên cứu được đặt ra ởMục 1.2.3 nay đối chiếu với kết quảđạt được như sau.
**RQ1 — Mô hình hoá biến động hành chính theo thời gian.** Đềtài đã thiết lập đầy đủmô hình SCD
Type 2 trên schema mat với cặp `valid_from` / `valid_to`, các cờ `is_active`, `is_deleted`, cột
`predecessor_id` và `version_id` . Đồthị `mat.unit_edge` với bốn kiểu quan hệđịnh lượng
mọi biến đổi địa giới. API tra cứu lịch sửtheo thời điểm cho phép truy vấn trạng thái đơn vịbất kỳthời
điểm nào. _Kết luận:_ RQ1 đã được giải quyết hoàn chỉnh ởtầng dữliệu và API.
**RQ2 — Hybrid PhoBERT + mGTE so với tìm kiếm từvựng truyền thống.** Đềtài đã hiện thực
pipeline HYBRID_V1 tám bước với ba tầng AI tích hợp. Trên artifact hiện tại, PhoBERT NER đạt F1
_≈_ 93 _._ 76 % — vượt mức tham khảo trong các nghiên cứu trước tại Việt Nam (Chương 2). Cấu trúc đo
S-RET đã sẵn sàng, song chưa có sốliệu retrieval định lượng đểso sánh trực tiếp với baseline lexical.
_Kết luận:_ RQ2 được giải quyết vềkiến trúc, đo lường định lượng cần bổsung ởcác vòng thực nghiệm
tiếp.
**RQ3 — Thuật toán hình học không gian cho tựhiệu chỉnh.** Đềtài đã đềxuất và hiện thực ba
chiến lược hiệu chỉnh polygon (Buffer-Union, Concave Hull, Edge Injection) với cơ sởlý thuyết tại
Chương 3. Endpoint `POST` `/api/spatial/subdivide` đã vận hành điểm thuộc vùng dựa trên
PostGIS với cơ chế _fallback_ sang `ST_Distance` khi điểm sát biên. _Kết luận:_ RQ3 đã có kiến trúc
đầy đủ; đánh giá định lượng hiệu quảcủa các chiến lược cần dữliệu giao nhận thực tếquy mô lớn.
**Đối** **chiếu** **với** **Gate** **B** **nội** **bộ.** F1 và token accuracy NER trên artifact hiện tại _chưa_ vượt 96%
đồng thời như Gate B yêu cầu. Điều này định vịrõ “khoảng cách còn lại” giữa bằng chứng khái niệm
( _proof-of-concept_ ) và mục tiêu vận hành nghiêm ngặt. Đềtài chủtrương báo cáo trung thực khoảng
cách này thay vì che giấu, vì nó là cơ sởcho công tác cải tiến tiếp theo.
**Hạng** **mục** **báo** **cáo** **định** **lượng** **còn** **chưa** **hoàn** **tất.** (i) Bảng E2E theo ba kịch bản S1–S3
trên địa chỉthực tế. (ii) Cột retrieval (R@k, MRR) trong tổng hợp SUPA-Bench - cần chạy
`evaluate_retriever.py` với `–persist-db` trên snapshot mô hình đã chọn. (iii) Toàn bộ
chỉsốtrên _pipeline chuẩn hoá thật_ (không oracle) đểđối chiếu với bảng ngưỡng kỳvọng (Bảng 5.6).
(iv) Sốliệu latency, P95 và throughput đo từpipeline (yêu cầu cột `latency_ms` trong CSV preds).


58


_6.3._ _ĐÓNG GÓP KHOA HỌC CỦA ĐỀTÀI_

## **6.3 Đóng góp Khoa học của Đềtài**


Đềtài đóng góp vào tri thức khoa học trên ba phương diện: lý luận, phương pháp luận và thực tiễn.

### **6.3.1 Đóng góp lý luận**


_Thứnhất_, đềtài đềxuất **mô** **hình** **“Chuẩn** **hoá** **địa** **chỉnhận** **thức** **thời** **gian”** **(Temporal-Aware**
**Address Standardization)** thông qua tích hợp SCD Type 2 [8] với đồthịquan hệ `unit_edge` . Khác
với các nghiên cứu trước coi dữliệu hành chính là tĩnh, mô hình này cho phép pipeline AI xửlý đồng
thời cảhai phiên bản hành chính (tiền và hậu cải cách 2025) mà không gặp hiện tượng _catastrophic_
_forgetting_ . Đây là khoảng trống tri thức sốmột được xác định ởMục 2.3 và nay đã có một giải pháp
hoàn chỉnh.
_Thứhai_, đềtài mởrộng mô hình **Address Confidence Score (ACS)** với bốn thành phần chuẩn hoá
theo Weighted Sum Model [37, 38, 10]:


ACS( _ai_ _| q_ ) = _α · S_ text + _β · S_ sem + _γ · V_ hier + _δ · V_ temporal


trong đó việc đưa _V_ hier (kiểm tra phân cấp) và _V_ temporal (trọng sốthời gian) làm thành phần cứng là điểm
mới so với các công thức ACS chỉdùng độkhớp văn bản và ngữnghĩa. Bốn trạng thái quyết định
(Auto-Accept, Auto-Convert, Suggest, Reject) phản ánh trực tiếp bối cảnh dữliệu lưỡng thời.
_Thứba_, đềtài đềxuất **ba chiến lược hiệu chỉnh đa giác không gian** (Buffer-Union, Concave Hull,
Edge Injection) học từlịch sửtoạđộgiao nhận thực tế. Đây là một nhánh mởrộng cho cơ sởlý thuyết
vềHệthống Thông tin Địa lý (GIS) trong bối cảnh ngày càng nhiều doanh nghiệp logistics tích luỹdữ
liệu định vịthực tếquy mô lớn.

### **6.3.2 Đóng góp phương pháp luận**


_Thứnhất_, đềtài thiết lập **khung đánh giá SUPA-Bench** có thểtái lập đầy đủtrên ground truth chỉđọc.
Bất biến nghiên cứu cốt lõi — pipeline SUPA chỉ `SELECT` chứtuyệt đối không `INSERT` / `UPDATE` /
`DELETE` trên `prq.ground_truth` - đảm bảo tách bạch giữa nguồn tham chiếu và quy trình đánh
giá. Đây là một đóng góp phương pháp luận có thểchuyển giao cho các nghiên cứu tương tựtrong
miền dữliệu nghiệp vụ.
_Thứhai_, đềtài đềxuất **hệthống chỉsốP-* và S-*** tách bạch chất lượng tham sốmô hình (P-F1,
P-Acc) khỏi chất lượng cấu trúc đầu ra (S-NER-EM, S-E2E-EM, S-RET). Cách phân loại này giúp cô
lập nguyên nhân khi một chỉsốtổng hợp tụt giảm — một đóng góp vềphương pháp chẩn đoán có hệ
thống thay vì báo cáo đơn chỉsố.
_Thứba_, đềtài giới thiệu **audit bridge** làm phép đo điều kiện tiên quyết cho mọi đánh giá end-to-end.
Phép đo này thường bịbỏqua trong các nghiên cứu chuẩn hoá địa chỉ, dẫn đến diễn giải sai khi metric
giảm sút. Việc tách audit khỏi đo chất lượng mô hình là một thực hành phương pháp luận có giá trị
chuyển giao.
_Thứtư_, đềtài thiết lập **quy trình thực nghiệm phân tầng K = 5** với bảng tổng hợp _persist_ trong
ath, kết hợp cơ cấu cohort `strat-v1` bao quát bốn kiểu khó (D1–D4). Đóng góp ởchỗchứng minh
khảnăng đo độổn định thống kê ( _stability_ ) trên một bài toán nghiệp vụ, một thực hành chưa phổbiến
trong các nghiên cứu chuẩn hoá địa chỉtrước đây.


59


_6.4._ _KHẲNG ĐỊNH TÍNH THỰC TIỄN CỦA KHUNG GIẢI PHÁP_

### **6.3.3 Đóng góp thực tiễn**


_Thứnhất_, đềtài cung cấp **giải pháp khắc phục hiện tượng đứt gãy dữliệu** do cải cách hành chính
2025. Bằng ánh xạđịa chỉtiền cải cách sang định danh hậu cải cách qua quan hệ `MERGES_INTO`, hệ
thống duy trì tính liên tục dữliệu khách hàng trong CRM và logistics, trực tiếp giảm tỷlệgiao hàng
thất bại ( _last-mile failure rate_ ).
_Thứhai_, kiến trúc **Waterfall Enrichment** ba lớp Cache–OSM/VietMap–Google Maps cùng chiến
lược “Fast and Free” (toàn bộthành phần _self-hosted_ mã nguồn mở) giảm đáng kểchi phí API thương
mại so với phụthuộc 100% Google Maps. Đây là giải pháp khảthi cho doanh nghiệp Việt Nam quy
mô vừa và nhỏ.
_Thứba_, đềtài đưa lựa chọn **Qwen2.5-1.5B-Instruct với lượng tửhoá 4-bit** thành tham chiếu cụ
thểvềcân bằng giữa độchính xác và hạtầng. Cấu hình này chạy được trên một GPU tiêu dùng 8 GB
VRAM, định vịrõ tính khảthi triển khai trong môi trường doanh nghiệp Việt Nam.
_Thứtư_, mọi mã nguồn, schema dữliệu, script benchmark và file cấu hình đều được tổchức đểcó
thểtái sửdụng. Doanh nghiệp có thểbật tựđộng hoá theo ngưỡng ACS, giữcon người trong vòng lặp
( _human-in-the-loop_ ) trên tập lỗi audit hoặc _stratum_ khó, và mởrộng dần miền dữliệu mà không phải
tái thiết kế.

## **6.4 Khẳng định Tính Thực tiễn của Khung Giải pháp**


Tính thực tiễn của khung giải pháp _không_ nằm ởviệc mọi chỉsốđều đạt ngưỡng tối ưu ngay trong
_snapshot_ đo được, mà ởchỗkhung giải pháp cho phép tách bạch các giai đoạn (trích thực thể, truy hồi
ứng viên, suy luận cấu trúc, kiểm chứng lineage và không gian) và _đo lường từng tầng riêng biệt_ trên
dữliệu thật. Quy mô dữliệu được kiểm chứng (437862 bản ghi hàng đợi, cohort ground truth nhiều
nghìn mẫu) đủtin cậy vềmặt thống kê. Mặt khác, khung đã chứng minh _khảnăng tái lập_ của thực
nghiệm có kiểm soát (SUPA, log huấn luyện đầy đủ _provenance_ ). Đây là cơ sởđểkhẳng định khung
giải pháp _vượt mức một mô hình đơn lẻtrên bảng kết quảnhỏ_ ( _table-running paper_ ) đểđạt cấp độ **kiến**
**trúc nghiên cứu có thểtriển khai** ( _deployable research_ ).
Cách tiếp cận này phù hợp triển khai trong doanh nghiệp với ba đặc tính: (a) bật tựđộng hoá theo
ngưỡng tin cậy ACS một cách an toàn; (b) giữcon người trong vòng lặp trên tập lỗi audit hoặc _stratum_
khó; (c) mởrộng dần miền dữliệu và mô hình mà không phải tái cấu trúc khung. Đây chính là phương
châm thực dụng ( _pragmatic deployment_ ) mà các hệthống AI hiện đại đang theo đuổi.

## **6.5 Các Hạn chếcủa Nghiên cứu**


Đềtài chủđộng công bốbốn nhóm hạn chếcòn tồn tại đểcác vòng nghiên cứu tiếp nối có cơ sởkhắc
phục.
_Hạn_ _chếvềdữliệu_ _và_ _miền_ _(domain)._ NER được huấn luyện trên một tập công khai giới hạn
4000 _/_ 800 mẫu trong một lần đã đóng băng; khảnăng khái quát hoá sang địa chỉnội bộdoanh nghiệp,
viết tắt vùng miền hoặc chuỗi từnhận dạng ký tựquang học (OCR) cần đánh giá bổsung. Ground truth
từTypesense và hàng đợi có thểtồn tại sựlệch phân phối ( _distribution shift_ ) so với dữliệu sản phẩm.
_Hạn chếvềđo lường chưa đủmảnh ghép._ Việc thiếu báo cáo sốđịnh lượng cho retrieval và E2E
theo kịch bản nghiệp vụlàm giảm độhoàn chỉnh của bức tranh “định lượng toàn pipeline” trong một
tài liệu duy nhất. Tuy nhiên, hạtầng đo lường (script, schema, API) đã sẵn sàng và việc bổsung không
yêu cầu thiết kếlại.


60


_6.6._ _HƯỚNG PHÁT TRIỂN_


_Hạn chếphụthuộc hạtầng không gian._ Các endpoint Point-in-Polygon và _mismatch-report_ yêu
cầu PostGIS được cài đặt và `mat.area_polygon` đủphủ. Khi thiếu, các chỉbáo không gian suy
giảm xuống mức heuristic ( _nearest centroid_, edge inject). Đềtài đã chuẩn bị _fallback_, song mức chính
xác bịgiới hạn.
_Rủi ro vềmô hình ngôn ngữlớn._ LLM có thểsinh chuỗi hợp ngữpháp nhưng lệch master hoặc
lệch ứng viên retrieval (hiện tượng _hallucination_ ). Cần lớp kiểm chặt chẽthông qua ràng buộc schema
(JSON), _constrained decoding_ bám tập ứng viên top- _k_, hoặc dữliệu huấn luyện chuyên biệt (RLHF
hoặc _instruction tuning_ trên domain) nếu muốn tăng độtựđộng.
_Hạn chếvềchi phí và độtrễ._ Pipeline đầy đủ(nhúng corpus, NER, LLM) tiêu tốn đáng kểtài
nguyên GPU/CPU và thời gian khởi động. Đánh đổi đã được nhận thức (corpus limit, quantization, _db_
_batch size_ ), song cần bảng đo trên phần cứng mục tiêu triển khai cụthể.

## **6.6 Hướng Phát triển**


Trên cơ sởcác kết quảđã đạt được và hạn chếđã nhận diện, đềtài đềxuất sáu hướng phát triển theo
trình tựtăng dần độtựđộng hoá và giảm dần can thiệp thủcông, đặc biệt tập trung vào _tựđộng hoá_
_hoàn toàn quy trình làm giàu dữliệu không gian_ (end-to-end geospatial enrichment).

### **6.6.1 Chuẩn hoá hạtầng không gian**


Đảm bảo PostGIS được kích hoạt và chỉmục không gian (GiST) trên các cột geometry của
`mat.area_polygon` . Thống nhất SRID 4326 (WGS84) và quy trình nhập/cập nhật polygon từ
OpenStreetMap hoặc nguồn ranh giới chính thống. Theo dõi độphủ( _coverage_ ) theo cấp tỉnh, huyện,
xã và phát hiện các vùng có dữliệu thưa.

### **6.6.2 Pipeline làm giàu đóng vòng (Closed Loop)**


Sau bước _geocode_ hoặc khi có toạđộtừretrieval corpus, kích hoạt chuỗi tựđộng: gán đơn vịhành
chính bằng Point-in-Polygon; nếu _mismatch_ so với trường khai báo, kích hoạt Edge Injection hoặc đưa
vào hàng đợi xửlý ngoại lệ; ghi nhận nguồn và độtin cậy vào metadata bản ghi. Đây là sựkết nối trực
tiếp giữa Module Geospatial (4.6) với Module AI Pipeline (4.5) đã thiết kế.

### **6.6.3 Tựđộng hoá thu thập OSM**


Lên lịch job thu thập OpenStreetMap theo tỉnh với ngưỡng đầy đủdữliệu đường và POI; đồng bộ
_incremental_ chỉvới các thay đổi khi API Overpass và lưu trữcho phép; gắn SLA cụthểvềđộtrễvà
kích thước job. Phương án này giảm tải hạtầng so với tải lại toàn bộdữliệu OSM định kỳ.

### **6.6.4 Liên kết với chuẩn hoá địa chỉ**


Áp dụng cùng một “hợp đồng dữliệu” ( _data contract_ ) lineage queue–master đã được kiểm định bởi
audit bridge. Ưu tiên _join_ theo lineage cho mọi phân tích chất lượng; giảm dần tỷlệ _fail_ G3 (14044
dòng) bằng quy tắc sửa hoặc _re-sync_ master định kỳ.


61


_6.7._ _LỜI KẾT_

### **6.6.5 Đánh giá và Giám sát Liên tục**


Bổsung báo cáo định kỳcho retrieval và E2E; tích hợp dashboard theo _stratum_ (tỉnh, độdài chuỗi,
epoch hành chính); thiết lập cảnh báo khi Gate B hoặc các cổng audit suy giảm sau migration dữliệu
hoặc nâng cấp mô hình. Đây là chuyển từ“chạy benchmark một lần” sang “vận hành benchmark như
dịch vụ” ( _benchmarking as a service_ ).

### **6.6.6 Nghiên cứu Nâng cao**


Bốn hướng nghiên cứu nâng cao đã được nhận diện. _Một_, học có cấu trúc ( _structured prediction_ ) kết
hợp ràng buộc đồthịhành chính trên `mat.unit_edge` . _Hai_, học từphản hồi con người ( _learning_
_from human feedback_ ) trên tập ngoại lệ _mismatch_, cho phép mô hình tựcải thiện theo phản hồi vận
hành. _Ba_, mô hình sinh có ràng buộc ( _constrained decoding_ ) khớp tập ứng viên retrieval, khắc phục
_hallucination_ của LLM. _Bốn_, học liên kết ( _federated learning_ ) cho phép nhiều đơn vịlogistics cùng
huấn luyện mô hình mà không cần chia sẻdữliệu khách hàng nhạy cảm — một hướng đặc biệt phù
hợp với Luật Bảo vệDữliệu Cá nhân của Việt Nam.

## **6.7 Lời kết**


Đềtài _Xây dựng khung giải pháp làm giàu và chuẩn hoá dữliệu địa chỉViệt Nam sửdụng tiếp cận đa_
_nguồn và thuật toán hình học không gian trong bối cảnh sắp xếp đơn vịhành chính toàn quốc 2025_ đặt
mình vào vịtrí giao thoa giữa ba lĩnh vực: xửlý ngôn ngữtựnhiên tiếng Việt, hệthông tin địa lý, và
quản trịdữliệu lưỡng thời. Khung giải pháp VNAI không tham vọng thay thếluật phân cấp hành chính
thực tếdo Nhà nước ban hành; thay vào đó, đềtài hướng tới mục tiêu khiêm tốn hơn nhưng có giá trị
bền vững: _kéo suy luận của AI vào đúng bằng chứng trên master hành chính_ và _báo cáo các chỉtiêu_
_theo một giao thức KPI đã khoá_, đểmọi cải tiến đều có thểđo lường và đối chứng.
Công việc tiếp theo là các vòng huấn luyện–đánh giá–triển khai dài hạn, với artifact, `git_commit`,
_seed_ và _source-note_ được lưu kèm mọi kết quả. Đềtài kết thúc ởđây với sáu module đã được thiết kế
và phần lớn đã được hiện thực hoá; tập định lượng đầy đủcho retrieval và E2E pipeline thật là khoảng
trống công khai mà các vòng nghiên cứu tiếp nối sẽlấp đầy. Kính mong nhận được những góp ý chuyên
môn từHội đồng đểkhung giải pháp ngày càng hoàn thiện và thực sựđóng góp cho hạtầng dữliệu địa
chỉbền vững phục vụnền kinh tếsốViệt Nam.

