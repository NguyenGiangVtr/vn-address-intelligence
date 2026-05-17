### **ĐẠI HỌC QUỐC GIA TP. HỒCHÍ MINH** **TRƯỜNG ĐẠI HỌC BÁCH KHOA** **KHOA KHOA HỌC & KỸTHUẬT MÁY TÍNH** **NGÀNH HỆTHỐNG THÔNG TIN QUẢN LÝ** —————o0o————— **ĐỀÁN TỐT NGHIỆP** **XÂY DỰNG KHUNG GIẢI PHÁP** **LÀM GIÀU VÀ CHUẨN HÓA DỮLIỆU ĐỊA CHỈVIỆT NAM** **SỬDỤNG TIẾP CẬN ĐA NGUỒN** **VÀ THUẬT TOÁN HÌNH HỌC KHÔNG GIAN** **TRONG BỐI CẢNH** **SẮP XẾP ĐƠN VỊHÀNH CHÍNH TOÀN QUỐC 2025** Giảng viên hướng dẫn: PGS. TS. Trần Minh Quang Học viên: Nguyễn Vũ Trọng Giang MSHV: 2470279 TP. HồChí Minh, 05/2026


# **Lời cảm ơn**

Trước hết, tôi xin bày tỏlòng biết ơn sâu sắc đến PGS.TS Trần Minh Quang, người thầy đã trực tiếp
hướng dẫn và đồng hành cùng tôi trong suốt quá trình thực hiện đềtài. Những định hướng khoa học,
góp ý chuyên môn và sựtận tâm của Thầy không chỉgiúp tôi hoàn thiện nội dung nghiên cứu mà còn
hình thành cho tôi phương pháp tư duy nghiêm túc, hệthống trong nghiên cứu khoa học.
Tôi xin chân thành cảm ơn Ban Giám hiệu Trường Đại học Bách Khoa – Đại học Quốc gia Thành
phốHồChí Minh, Phòng Đào tạo Sau đại học cùng quý Thầy/Cô Khoa Khoa học và Kỹthuật Máy
tính đã truyền đạt những kiến thức nền tảng và chuyên sâu, đồng thời tạo điều kiện thuận lợi đểtôi
hoàn thành chương trình học tập và nghiên cứu tại trường.
Tôi cũng xin gửi lời cảm ơn đến Ban lãnh đạo và các đồng nghiệp tại Công ty Cổphần Con Cưng
đã hỗtrợtôi trong việc tiếp cận dữliệu thực tếvà tạo điều kiện đểtriển khai các thửnghiệm, đánh giá
hệthống. Những trao đổi và góp ý từgóc độnghiệp vụthực tiễn đã giúp đềtài gắn kết chặt chẽhơn
giữa lý thuyết và ứng dụng.
Cuối cùng, tôi xin bày tỏlòng tri ân đến gia đình và bạn bè, những người luôn động viên, chia sẻ
và là điểm tựa tinh thần vững chắc, giúp tôi vượt qua những khó khăn trong suốt quá trình học tập và
nghiên cứu. Mặc dù đã rất nỗlực trong quá trình thực hiện, đềtài khó tránh khỏi những hạn chếnhất
định. Tôi kính mong nhận được sựgóp ý và chỉdẫn của quý Thầy/Cô trong Hội đồng bảo vệđểđềtài
được hoàn thiện hơn.


i


# **Bảng ký hiệu**

Bảng 1: Bảng ký hiệu sửdụng trong báo cáo


**Ký hiệu** **Ý nghĩa**


_q_ Chuỗi truy vấn (địa chỉngười dùng nhập)
_ai_ Ứng viên địa chỉthứ _i_ (candidate address)
_D_ = _{d_ 1 _, . . ., dN_ _}_ Bộsưu tập tài liệu địa chỉchuẩn trong cơ sởtri thức
**q** _, ⃗q_ Vector embedding của truy vấn _q_ trong không gian R _[d]_

**a** _i, d_ _[⃗]_ Vector embedding của ứng viên _ai_ hoặc tài liệu _d_
_Q, K, V_ Ma trận Truy vấn, Khoá, Giá trịtrong cơ chếSelf-Attention
_W_ _[Q]_ _, W_ _[K]_ _, W_ _[V]_ Ma trận trọng sốhọc đểchiếu đầu vào sang _Q, K, V_
_dk_ Sốchiều vector Khoá; phép chia _[√]_ _dk_ ổn định softmax
head _i_ Đầu attention thứ _i_ trong Multi-Head Attention
_hi,_ _h_ [˜] _i_ Vector ngữcảnh do BERT/PhoBERT sinh; _h_ [˜] _i_ qua BiLSTM
_y_ = ( _y_ 1 _, . . ., yn_ ) Chuỗi nhãn BIO dựbáo cho chuỗi đầu vào dài _n_
_A_ Ma trận chuyển trạng thái CRF, kích thước _|L| × |L|_
_Y_ Tập tất cảchuỗi nhãn hợp lệ
Sim( _q, d_ ) Hàm đo độtương đồng ngữnghĩa tổng quát

    -    cos _⃗q, d_ _[⃗]_ Cosine similarity giữa hai vector


                        -                         
SimLate Late Interaction MaxSim: [�] _i_ [max] _[j]_ [ cos] _⃗qi, d_ _[⃗]_ _j_

_k_ Sốkết quảtop- _k_ trảvềtừretrieval

_D_ = _⃗q −_ _⃗d_ Khoảng cách Euclidean giữa hai vector
��� ���
_α_ (Triplet) Margin trong Triplet Loss
_L_ cont _, L_ triplet Hàm mất mát Contrastive và Triplet
_P, P_ _[′]_ Polygon ranh giới gốc và sau hiệu chỉnh
_P_ = _{p_ 1 _, . . ., pk}_ Đám mây điểm (cloud) toạđộgiao nhận thực tế
_B_ ( _p, r_ ) = _{x_ : Vùng đệm (buffer) bán kính _r_ quanh điểm _p_
_∥x −_ _p∥≤_ _r}_

_S_ text Điểm khớp theo văn bản (BM25 / Typesense text score), chuẩn
hoá [0 _,_ 1]
_S_ sem Điểm khớp theo ngữnghĩa (cosine similarity), chuẩn hoá [0 _,_ 1]
_V_ hier _∈{_ 0 _,_ 1 _}_ Chỉsốkiểm tra phân cấp Phường _∈_ Quận _∈_ Tỉnh trong `mat`
_V_ temporal _∈_ [0 _,_ 1] Trọng sốthời gian: 1 nếu hậu cải cách, 0 _,_ 7 nếu cũ trong cửa sổ
_α, β, γ, δ_ Trọng sốWSM trong công thức ACS, ràng buộc _α_ + _β_ + _γ_ + _δ_ =
1


ii


_(tiếp Bảng 1)_


**Ký hiệu** **Ý nghĩa**



ACS( _ai_ _| q_ ) Điểm tin cậy địa chỉcho ứng viên _ai_ trước truy vấn _q_
_A_ = _{a_ 1 _, a_ 2 _, a_ 3 _, a_ 4 _}_ Không gian quyết định: {Auto-Accept, Auto-Convert, Suggest,
Reject}
_θ_ high _, θ_ low Ngưỡng quyết định ( _θ_ high = 0 _,_ 85; _θ_ low = 0 _,_ 50)
_Bm_ Khoảng giá trị(bin) thứ _m_ trong tính ECE
acc( _Bm_ ) _,_ conf( _Bm_ ) Độchính xác thực nghiệm và độtin cậy trung bình trong bin
ECE = Sai sốhiệu chuẩn kỳvọng

- _|Bm|_



Sai sốhiệu chuẩn kỳvọng



_|Bm|_
_m_ _n_




- _m_ _nm_ _[|]_ [acc(] _[B][m]_ [)] _−_

conf( _Bm_ ) _|_



_K_ = 5 Sốlần lặp độc lập trong thực nghiệm phân tầng
_n_ = 2 _._ 000 Cỡcohort mỗi lần chạy SUPA-Bench phân tầng


iii


# **Tóm tắt đềtài**

Trong bối cảnh chuyển dịch cơ cấu mạnh mẽtừmô hình bán lẻtruyền thống (offline) sang thương mại
điện tử(online), nhu cầu vềđộchính xác của dữliệu địa chỉgiao nhận đã trởthành yếu tốquyết định
năng lực cạnh tranh của các doanh nghiệp logistics và chuỗi cung ứng. Tuy nhiên, các hệthống quản
lý địa chỉhiện hành tại Việt Nam đang bộc lộnhiều điểm nghẽn: sựthiếu nhất quán dữliệu giữa các
doanh nghiệp đối tác, khảnăng xửlý kém đối với văn bản phi cấu trúc, và đặc biệt là sai sốlớn trong
việc định vịkhông gian tại các ranh giới tiếp giáp địa lý.
Nghiên cứu này đềxuất một khung giải pháp toàn diện mang tên **VN Address Intelligence (VNAI)** .
Hệthống VNAI triển khai pipeline AI đa tầng tích hợp PhoBERT (NER), mGTE (Retrieval) và LLM
đểchuẩn hóa, làm giàu dữliệu địa chỉViệt Nam lưỡng thời, đảm bảo tính nhất quán dữliệu và độ
chính xác không gian trong bối cảnh cải cách hành chính 2025. Hệthống được kiến trúc dựa trên ba
trụcột công nghệcốt lõi:


   - **Tựđộng hóa đồng bộ(Data Orchestration):** Ứng dụng quy trình _workflow_ qua n8n kết hợp
với SOAP API đểchủđộng đồng bộdanh mục hành chính từcơ sởdữliệu của Chính phủ(Gov),
đảm bảo tính nhất quán và cập nhật liên tục cho toàn bộmạng lưới doanh nghiệp kết nối.


   - **Chuẩn hóa bằng Trí tuệnhân tạo (AI-driven Normalization):** Thiết kếluồng xửlý ngôn ngữ
tựnhiên (NLP) đa tầng bao gồm tác vụNhận dạng thực thểcó tên (NER) bằng PhoBERT, so
khớp ngữnghĩa qua mạng Siamese (mGTE), và vận dụng khảnăng suy luận của Mô hình ngôn
ngữlớn (LLM) nhằm xửlý các biến thểđịa danh phi cấu trúc phức tạp.


   - **Xửlý Hình học Không gian (Geospatial Computation):** Ứng dụng các thuật toán không gian
trong PostGIS đểphân giải chính xác vịtrí tại các ranh giới nhạy cảm. Nghiên cứu đềxuất cơ
chếtựđộng hiệu chỉnh đa giác (polygon) ranh giới dựa trên việc phân tích lịch sửtọa độgiao
nhận thực tếcủa hệthống logistics.


Bên cạnh đó, giải pháp còn tích hợp khảnăng tựđộng làm giàu thông tin từcác nguồn dữliệu mở
(Open Data) như Google Maps và OpenStreetMap (OSM). Hệthống cung cấp cơ chếtra cứu chuẩn
xác lịch sửthay đổi của các đơn vịhành chính (trước và sau các đợt sáp nhập), giúp duy trì tính toàn
vẹn của dữliệu trong dài hạn. Kết quảcủa nghiên cứu kỳvọng mang lại một dịch vụchuẩn hóa địa chỉ
có tính ứng dụng cao, giúp tối ưu hóa chi phí vận hành chặng cuối (last-mile delivery) cho các doanh
nghiệp bán lẻvà giao nhận tại Việt Nam.


iv


# **Mục lục**

**Lời cảm ơn** **i**


**Bảng ký hiệu** **ii**


**Tóm tắt** **iv**


**Mục Lục** **viii**


**Danh sách bảng** **ix**


**Danh sách hình** **x**


**Danh sách từviết tắt** **xi**


**1** **MỞĐẦU** **1**
1.1 Lý do hình thành đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 1
1.2 Mục tiêu đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
1.2.1 Mục tiêu tổng quát . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
1.2.2 Mục tiêu cụthể. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
1.2.3 Câu hỏi nghiên cứu . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
1.3 Phạm vi và Đối tượng nghiên cứu . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1.3.1 Đối tượng nghiên cứu: . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1.3.2 Phạm vi nghiên cứu: . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1.4 Ý nghĩa Khoa học và Thực tiễn . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1.4.1 Ý nghĩa khoa học . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1.4.2 Ý nghĩa thực tiễn . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
1.5 Bốcục đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5


**2** **TỔNG QUAN NGHIÊN CỨU** **7**
2.1 Các nghiên cứu quốc tếvềchuẩn hóa địa chỉ. . . . . . . . . . . . . . . . . . . . . . 7
2.2 Các nghiên cứu tại Việt Nam và bài toán đặc thù . . . . . . . . . . . . . . . . . . . . 7
2.2.1 Tiếp cận dựa trên mô hình học máy truyền thống và Deep Learning . . . . . 7
2.2.2 Các tiêu chuẩn hành chính và bưu chính . . . . . . . . . . . . . . . . . . . . 8
2.2.3 Xu hướng ứng dụng LLM trong phân tích ngữnghĩa tiếng Việt . . . . . . . . 8
2.3 Phân tích khoảng trống nghiên cứu (Research Gaps) . . . . . . . . . . . . . . . . . . 8
2.4 Xác lập hướng tiếp cận của đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9


v


_MỤC LỤC_


**3** **Cơ sởlý thuyết** **10**
3.1 Tổng quan định vị. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
3.2 Kiến trúc Transformer . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
3.2.1 Bối cảnh ra đời và động lực . . . . . . . . . . . . . . . . . . . . . . . . . . 11
3.2.2 Cơ chếSelf-Attention . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
3.2.3 Multi-Head Attention . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
3.2.4 Kiến trúc Encoder-Decoder và Positional Encoding . . . . . . . . . . . . . . 12
3.3 PhoBERT cho Nhận diện thực thểtên . . . . . . . . . . . . . . . . . . . . . . . . . 14
3.3.1 TừBERT đến RoBERTa . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
3.3.2 PhoBERT — Đơn ngữhóa cho tiếng Việt . . . . . . . . . . . . . . . . . . . 14
3.3.3 Bài toán NER và sơ đồnhãn BIO . . . . . . . . . . . . . . . . . . . . . . . 14
3.3.4 PhoBERT + BiLSTM-CRF cho NER địa chỉ . . . . . . . . . . . . . . . . . 15
3.3.5 So sánh PhoBERT với mô hình đa ngôn ngữ. . . . . . . . . . . . . . . . . . 16
3.4 mGTE và truy xuất ngữnghĩa đa tầng . . . . . . . . . . . . . . . . . . . . . . . . . 17
3.4.1 Bài toán Semantic Retrieval . . . . . . . . . . . . . . . . . . . . . . . . . . 17
3.4.2 Mô hình nhúng văn bản và kiến trúc Bi-encoder . . . . . . . . . . . . . . . . 17
3.4.3 mGTE và Late Interaction . . . . . . . . . . . . . . . . . . . . . . . . . . . 18
3.4.4 Approximate Nearest Neighbo - ANN . . . . . . . . . . . . . . . . . . . . . 18
3.5 Mạng Siamese (Siamese Network) và Học sâu so khớp (Deep Metric Learning) . . . 19
3.5.1 Kiến trúc Siamese . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
3.5.2 Hàm mất mát: Contrastive Loss và Triplet Loss . . . . . . . . . . . . . . . . 19
3.5.3 Ứng dụng cho bài toán so khớp địa chỉ. . . . . . . . . . . . . . . . . . . . . 20
3.6 Hình học không gian và PostGIS . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20
3.6.1 Mô hình dữliệu không gian . . . . . . . . . . . . . . . . . . . . . . . . . . 20
3.6.2 Hệtọa độđịa lý và hệtọa độphẳng . . . . . . . . . . . . . . . . . . . . . . 21
3.6.3 Phép toán không gian PostGIS . . . . . . . . . . . . . . . . . . . . . . . . . 21
3.6.4 Thuật toán Point-in-Polygon: Ray Casting . . . . . . . . . . . . . . . . . . . 22
3.6.5 Ba chiến lược hiệu chỉnh polygon . . . . . . . . . . . . . . . . . . . . . . . 22
3.7 Mô hình ACS — Điểm tin cậy địa chỉ . . . . . . . . . . . . . . . . . . . . . . . . . 23
3.7.1 Bài toán ra quyết định trong chuẩn hóa địa chỉ. . . . . . . . . . . . . . . . . 23
3.7.2 Mô hình tổng trọng số(WSM) . . . . . . . . . . . . . . . . . . . . . . . . . 24
3.7.3 Công thức ACS với bốn thành phần . . . . . . . . . . . . . . . . . . . . . . 24
3.7.4 Bảng quyết định bốn trạng thái . . . . . . . . . . . . . . . . . . . . . . . . . 25
3.7.5 Đánh giá hiệu chuẩn: Expected Calibration Error . . . . . . . . . . . . . . . 25
3.8 Tóm tắt chương . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26


**4** **Phân tích yêu cầu và thiết kếkhung giải pháp** **27**
4.1 Phân tích yêu cầu hệthống . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
4.1.1 Yêu cầu nghiệp vụ . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
4.1.2 Yêu cầu phi chức năng . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
4.1.3 Phân tích luồng dữliệu . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
4.2 Kiến trúc tổng thểVNAI . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
4.2.1 Triết lý thiết kế. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
4.2.2 Công nghệ(Technology Stack) . . . . . . . . . . . . . . . . . . . . . . . . . 29
4.2.3 Kiến trúc phân lớp và cấu trúc mã nguồn . . . . . . . . . . . . . . . . . . . 29
4.3 Thiết kếcơ sởdữliệu đa schema . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31


vi


_MỤC LỤC_


4.3.1 Quy ước chung và mô hình SCD Type 2 . . . . . . . . . . . . . . . . . . . . 31
4.3.2 Schema mat — Đơn vịhành chính và ranh giới . . . . . . . . . . . . . . . . 32
4.3.3 Schema osm — Dữliệu OpenStreetMap . . . . . . . . . . . . . . . . . . . . 32
4.3.4 Schema ath — Hub AI, benchmark và nhật ký . . . . . . . . . . . . . . . . . 32
4.3.5 Schema prq — Hàng đợi xửlý và ground truth . . . . . . . . . . . . . . . . 33
4.3.6 Bảng SUPA-Bench cho thực nghiệm . . . . . . . . . . . . . . . . . . . . . . 33
4.4 Module 1: Đồng bộdanh mục hành chính (Gov-Sync) . . . . . . . . . . . . . . . . . 34
4.4.1 Luồng đồng bộtừnguồn NSO . . . . . . . . . . . . . . . . . . . . . . . . . 34
4.4.2 SCD Type 2 và đồthịquan hệunit_edge . . . . . . . . . . . . . . . . . . . . 34
4.4.3 Vai trò orchestration n8n . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
4.4.4 Chuyển đổi địa chỉtheo kỷnguyên hành chính . . . . . . . . . . . . . . . . 35
4.5 Module 2: Pipeline AI chuẩn hóa địa chỉ. . . . . . . . . . . . . . . . . . . . . . . . 35
4.5.1 Lớp tiền xửlý và PreLabeler . . . . . . . . . . . . . . . . . . . . . . . . . . 35
4.5.2 Huấn luyện PhoBERT NER . . . . . . . . . . . . . . . . . . . . . . . . . . 36
4.5.3 Retrieval đa tầng với Siamese mGTE . . . . . . . . . . . . . . . . . . . . . 36
4.5.4 Tinh chỉnh cấu trúc bằng LLM Qwen . . . . . . . . . . . . . . . . . . . . . 36
4.5.5 Pipeline production HYBRID_V1 . . . . . . . . . . . . . . . . . . . . . . . 37
4.5.6 So sánh đa mô hình trên API nghiên cứu . . . . . . . . . . . . . . . . . . . . 38
4.6 Module 3: Geospatial và hiệu chỉnh polygon . . . . . . . . . . . . . . . . . . . . . . 39
4.6.1 Thu thập OpenStreetMap . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
4.6.2 Lưu trữpolygon và trực quan hóa ranh giới . . . . . . . . . . . . . . . . . . 39
4.6.3 API spatial: Point-in-Polygon và Mismatch Report . . . . . . . . . . . . . . 39
4.6.4 Edge Injection cho hiệu chỉnh GPS gần biên . . . . . . . . . . . . . . . . . . 39
4.7 Module 4: Làm giàu dữliệu đa nguồn . . . . . . . . . . . . . . . . . . . . . . . . . 40
4.7.1 Chiến lược thu thập đa nguồn và Waterfall Enrichment . . . . . . . . . . . . 40
4.7.2 Bộnhớđệm Redis và xóa cache có chọn lọc . . . . . . . . . . . . . . . . . . 42
4.7.3 Provenance và quản lý nguồn gốc dữliệu . . . . . . . . . . . . . . . . . . . 42
4.8 Tầng API REST và giao diện người dùng . . . . . . . . . . . . . . . . . . . . . . . . 42
4.8.1 Kiến trúc client SPA . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42
4.8.2 Phân nhóm endpoint REST . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
4.8.3 Xác thực JWT và bảo mật . . . . . . . . . . . . . . . . . . . . . . . . . . . 43
4.9 Khung thực nghiệm SUPA-Bench . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
4.9.1 Định nghĩa và mục tiêu . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
4.9.2 Quy trình SUPA-Bench năm bước . . . . . . . . . . . . . . . . . . . . . . . 44
4.9.3 Lệnh gộp workflow . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
4.9.4 Reproducibility và truy vết . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
4.10 Tóm tắt chương . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46


**5** **Thực nghiệm, Đánh giá Hiệu năng và Tác động Nghiệp vụ** **47**
5.1 Khung chỉsốđánh giá và mục tiêu đối chiếu . . . . . . . . . . . . . . . . . . . . . . 47
5.1.1 Hệthống chỉsốđánh giá đa tầng . . . . . . . . . . . . . . . . . . . . . . . . 47
5.1.2 Ngưỡng Gate B làm tiêu chí đối chiếu . . . . . . . . . . . . . . . . . . . . . 48
5.2 Thực nghiệm Nhận diện Thực thểtên có giám sát . . . . . . . . . . . . . . . . . . . 48
5.2.1 Thiết lập thực nghiệm . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 48
5.2.2 Kết quảđịnh lượng trên tập kiểm định . . . . . . . . . . . . . . . . . . . . . 48
5.2.3 Đối chiếu với Gate B và thảo luận . . . . . . . . . . . . . . . . . . . . . . . 49


vii


_MỤC LỤC_


5.3 Kiểm thửnhất quán dữliệu lineage (Audit Bridge) . . . . . . . . . . . . . . . . . . . 49
5.3.1 Mục tiêu và phương pháp . . . . . . . . . . . . . . . . . . . . . . . . . . . . 49
5.3.2 Kết quảkiểm thử. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 49
5.3.3 Ý nghĩa đối với đánh giá AI end-to-end . . . . . . . . . . . . . . . . . . . . 50
5.4 Khung thực nghiệm SUPA-Bench . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
5.4.1 Kịch bản đánh giá cơ bản . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
5.4.2 Diễn giải khoa học và giới hạn của kịch bản oracle . . . . . . . . . . . . . . 51
5.4.3 Thực nghiệm phân tầng với kiểm chứng chéo K = 5 . . . . . . . . . . . . . . 51
5.5 Đánh giá Truy xuất Ngữnghĩa . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 54
5.6 Kịch bản đánh giá End-to-End trên địa chỉthực tế. . . . . . . . . . . . . . . . . . . 55
5.7 Tối ưu hoá vận hành và đo lường hiệu năng . . . . . . . . . . . . . . . . . . . . . . 55
5.8 Tác động Nghiệp vụvà Phân tích Rủi ro . . . . . . . . . . . . . . . . . . . . . . . . 56
5.8.1 Tác động tích cực trên căn cứđịnh lượng . . . . . . . . . . . . . . . . . . . 56
5.8.2 Rủi ro và biện pháp giảm thiểu . . . . . . . . . . . . . . . . . . . . . . . . . 56
5.9 Tổng kết chương . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 56


**6** **Kết luận và Hướng phát triển** **58**
6.1 Tổng kết các kết quảđạt được . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 58
6.1.1 Kết quảvềkiến trúc và triển khai . . . . . . . . . . . . . . . . . . . . . . . 58
6.1.2 Kết quảđịnh lượng từartifact . . . . . . . . . . . . . . . . . . . . . . . . . 58
6.1.3 Kết quảvềphương pháp khoa học . . . . . . . . . . . . . . . . . . . . . . . 59
6.2 Đối chiếu với Mục tiêu Nghiên cứu . . . . . . . . . . . . . . . . . . . . . . . . . . . 59
6.3 Đóng góp Khoa học của Đềtài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 60
6.3.1 Đóng góp lý luận . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 60
6.3.2 Đóng góp phương pháp luận . . . . . . . . . . . . . . . . . . . . . . . . . . 60
6.3.3 Đóng góp thực tiễn . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 61
6.4 Khẳng định Tính Thực tiễn của Khung Giải pháp . . . . . . . . . . . . . . . . . . . 61
6.5 Các Hạn chếcủa Nghiên cứu . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 61
6.6 Hướng Phát triển . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 62
6.6.1 Chuẩn hoá hạtầng không gian . . . . . . . . . . . . . . . . . . . . . . . . . 62
6.6.2 Pipeline làm giàu đóng vòng (Closed Loop) . . . . . . . . . . . . . . . . . . 62
6.6.3 Tựđộng hoá thu thập OSM . . . . . . . . . . . . . . . . . . . . . . . . . . . 62
6.6.4 Liên kết với chuẩn hoá địa chỉ. . . . . . . . . . . . . . . . . . . . . . . . . 62
6.6.5 Đánh giá và Giám sát Liên tục . . . . . . . . . . . . . . . . . . . . . . . . . 63
6.6.6 Nghiên cứu Nâng cao . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 63
6.7 Lời kết . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 63


**TÀI LIỆU THAM KHẢO** **64**


viii


# **Danh sách bảng**

1 Bảng ký hiệu sửdụng trong báo cáo . . . . . . . . . . . . . . . . . . . . . . . . . . ii


1.1 Quy mô thay đổi đơn vịhành chính theo Nghịquyết 202/2025/QH15 và 35/2023/UBTVQH15 1


2.1 So sánh các công trình nghiên cứu liên quan . . . . . . . . . . . . . . . . . . . . . . 8


3.1 Định vịnền tảng lý thuyết theo câu hỏi nghiên cứu . . . . . . . . . . . . . . . . . . 10
3.2 So sánh PhoBERT với mô hình đa ngôn ngữtrên tác vụNER tiếng Việt . . . . . . . 17
3.3 So sánh ba kiến trúc encoder cho bài toán retrieval . . . . . . . . . . . . . . . . . . 19
3.4 Các phép toán không gian PostGIS sửdụng trong VNAI . . . . . . . . . . . . . . . 21
3.5 So sánh ba chiến lược hiệu chỉnh polygon . . . . . . . . . . . . . . . . . . . . . . . 23
3.6 Bảng quyết định theo điểm ACS . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25


4.1 Năm luồng dữliệu chính của khung giải pháp VNAI . . . . . . . . . . . . . . . . . 28
4.2 Chồng công nghệphân lớp của khung giải pháp VNAI . . . . . . . . . . . . . . . . 29
4.3 Các bảng cốt lõi trong schema mat . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
4.4 Các bảng cốt lõi trong schema ath . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
4.5 Tám bước của pipeline production HYBRID_V1 . . . . . . . . . . . . . . . . . . . 37
4.6 Bốn nguồn dữliệu trong module làm giàu . . . . . . . . . . . . . . . . . . . . . . . 41
4.7 Các endpoint REST cốt lõi theo nhóm chức năng . . . . . . . . . . . . . . . . . . . 43
4.8 Năm bước của quy trình SUPA-Bench . . . . . . . . . . . . . . . . . . . . . . . . . 45


5.1 Hệthống chỉsốđánh giá đa tầng của khung giải pháp VNAI . . . . . . . . . . . . . 48
5.2 Kết quảđịnh lượng PhoBERT NER trên tập kiểm định mẫu . . . . . . . . . . . . . 49
5.3 Kết quảaudit bridge giữa hàng đợi địa chỉvà master hành chính . . . . . . . . . . . 50
5.4 Kết quảSUPA-Bench cơ bản ( mẫu, kịch bản oracle) . . . . . . . . . . . . . . . . . 51
5.5 Cơ cấu phân tầng `strat-v1` cho cohort SUPA-Bench ( _n_ = 2 _._ 000/lần chạy) . . . . 53
5.6 Ngưỡng kỳvọng cho pipeline chuẩn hoá thật (không oracle) . . . . . . . . . . . . . 53
5.7 Kết quảthống kê K = 5 với cohort phân tầng _n_ = 2 _._ 000 (kịch bản oracle) . . . . . . 54


ix


# **Danh sách hình vẽ**

3.1 Kiến trúc tổng thểTransformer. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
3.2 Kiến trúc PhoBERT + BiLSTM-CRF cho tác vụNER địa chỉtiếng Việt. . . . . . . . 16
3.3 Ba kiến trúc retrieval: Bi-encoder, Late Interaction và Cross-encoder. . . . . . . . . . 18
3.4 Mạng Siamese và minh hoạhiệu ứng của Triplet Loss trong không gian embedding. . 20
3.5 Minh họa thuật toán Ray Casting cho bài toán Point-in-Polygon. . . . . . . . . . . . 22
3.6 Ba chiến lược hiệu chỉnh polygon: Buffer-Union, Concave Hull, Edge Injection. . . . 23
3.7 Sơ đồluồng ra quyết định dựa trên Điểm tin cậy địa chỉ(ACS) với bốn trạng thái. . . 25


4.1 Kiến trúc phân lớp bốn tầng của khung giải pháp VNAI. . . . . . . . . . . . . . . . 30
4.2 Cấu trúc thư mục logic kho mã nguồn VNAI. . . . . . . . . . . . . . . . . . . . . . 30
4.3 Lược đồER đầy đủcủa bốn schema cơ sởdữliệu VNAI. . . . . . . . . . . . . . . . 31
4.4 Luồng đồng bộGov-Sync sáu bước với nền tảng n8n. . . . . . . . . . . . . . . . . . 35
4.5 Pipeline production HYBRID_V1 tám bước. . . . . . . . . . . . . . . . . . . . . . . 38
4.6 Kiến trúc Waterfall Enrichment ba lớp Cache–OSM/VietMap–Google. . . . . . . . . 41
4.7 Workflow SUPA-Bench. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45


5.1 Phân phối kết quảaudit bridge trên hàng đợi địa chỉ. . . . . . . . . . . . . . . . . . . 50
5.2 Phân phối cohort SUPA-Bench theo cơ cấu `strat-v1`, _n_ = 2 _._ 000/lần chạy. . . . . . 52
5.3 Dao động EM@v1 trên năm lần chạy K = 5 độc lập với cohort phân tầng. . . . . . . 54


x


# **Danh sách từviết tắt**

**Từviết tắt** **Nghĩa tiếng Anh** **Nghĩa tiếng Việt**


ACS Address Confidence Score Điểm tin cậy địa chỉ(chỉsốđánh giá độ
chính xác của địa chỉ)
AI Artificial Intelligence Trí tuệnhân tạo
ANN Approximate Nearest Neighbor Tìm láng giềng gần nhất xấp xỉ(FAISS,
HNSW)
API Application Programming Inter- Giao diện lập trình ứng dụng
face

BERT Bidirectional Encoder Represen- Mô hình ngôn ngữtiền huấn luyện hai
tations from Transformers chiều
BI Business Intelligence Trí tuệkinh doanh
BIO Beginning-Inside-Outside Sơ đồnhãn cho NER
BPE Byte-Pair Encoding Mã hoá subword theo cặp byte
ColBERT Contextualized Late Interaction Mô hình retrieval Late Interaction
over BERT

CORS Cross-Origin Resource Sharing Chia sẻtài nguyên giữa nguồn gốc khác
nhau
CRF Conditional Random Field Trường ngẫu nhiên có điều kiện (mô
hình gán nhãn chuỗi)
CRS Coordinate Reference System Hệtham chiếu toạđộ(WGS84, VN2000, UTM)
CSAT Customer Satisfaction Score Điểm hài lòng khách hàng
CSV Comma-Separated Values Định dạng giá trịphân tách bằng dấu
phẩy
DBMS Database Management System Hệquản trịcơ sởdữliệu
DPR Dense Passage Retrieval Truy xuất đoạn văn dày đặc
DQC Data Quality Check Kiểm tra chất lượng dữliệu
DSS Decision Support System Hệhỗtrợra quyết định
DTO Data Transfer Object Đối tượng truyền dữliệu
ECE Expected Calibration Error Sai sốhiệu chuẩn kỳvọng (đo độtin cậy
của mô hình)
EM Exact Match Trùng khớp tuyệt đối (chỉsốđánh giá
chuỗi đầu ra)
ERD Entity-Relationship Diagram Sơ đồthực thể–quan hệ


xi


_DANH SÁCH HÌNH VẼ_


**Từviết tắt** **Nghĩa tiếng Anh** **Nghĩa tiếng Việt**


ETL Extract, Transform, Load Quy trình Trích xuất, Chuyển đổi, Tải
dữliệu
F1 F1-Score (harmonic mean of P Trung bình điều hoà giữa Precision và
and R) Recall
FAISS Facebook AI Similarity Search Thư viện tìm kiếm vector quy mô lớn
FastBPE Fast Byte-Pair Encoding Triển khai BPE hiệu suất cao của
PhoBERT
FFN Feed-Forward Network Mạng nơ-ron lan truyền tiến
FNR False Negative Rate Tỷlệâm tính giả(từchối sai địa chỉ
đúng)
FPR False Positive Rate Tỷlệdương tính giả(chấp nhận sai địa
chỉlỗi)
GeoJSON Geographic JSON Định dạng JSON cho dữliệu hình học
không gian
GIS Geographic Information System Hệthống thông tin địa lý
GPS Global Positioning System Hệthống định vịtoàn cầu
GPU Graphics Processing Unit Bộxửlý đồhoạ
GSO General Statistics Office Tổng cục Thống kê Việt Nam
HNSW Hierarchical Navigable Small Đồthịtìm láng giềng phân cấp
World

HTTP HyperText Transfer Protocol Giao thức truyền siêu văn bản
IVF Inverted File Index Chỉmục tệp ngược (FAISS)
JIT Just-In-Time Compilation Biên dịch tức thời
JSON JavaScript Object Notation Định dạng trao đổi dữliệu
JWT JSON Web Token Token xác thực dạng JSON
KPI Key Performance Indicator Chỉsốhiệu năng then chốt
LLM Large Language Model Mô hình ngôn ngữlớn (Qwen, GPT, ...)
LSTM Long Short-Term Memory Mạng nơ-ron hồi quy có cổng
MCDM Multi-Criteria Decision Making Ra quyết định đa tiêu chí
mGTE Multilingual Generalized Text Mô hình nhúng văn bản đa ngữ
Embedding

MLM Masked Language Modeling Tác vụtiền huấn luyện che ngẫu nhiên
token
MRR Mean Reciprocal Rank Thứhạng nghịch đảo trung bình
NER Named Entity Recognition Nhận diện thực thểcó tên
NFC Normalization Form Canonical Dạng chuẩn hợp thành Unicode
Composition

NFR Non-Functional Requirement Yêu cầu phi chức năng (hiệu năng, bảo
mật, ...)
NLP Natural Language Processing Xửlý ngôn ngữtựnhiên
NSO National Statistics Office (API) API danh mục hành chính Tổng cục
Thống kê
OCR Optical Character Recognition Nhận dạng ký tựquang học
OOV Out-of-Vocabulary Từngoài từđiển huấn luyện


xii


_DANH SÁCH HÌNH VẼ_


**Từviết tắt** **Nghĩa tiếng Anh** **Nghĩa tiếng Việt**


OSM OpenStreetMap Bản đồmởcộng đồng
P95 95th Percentile Phân vịthứ95 (đo độtrễhệthống)
P99 99th Percentile Phân vịthứ99
PE Positional Encoding Mã hoá vịtrí trong Transformer
PhoBERT Pre-trained BERT for Viet- Mô hình BERT chuyên cho tiếng Việt
namese

PIP Point-in-Polygon Bài toán điểm thuộc đa giác
POI Point of Interest Điểm quan tâm / địa điểm cụthể
PostGIS Spatial extension for Post- Mởrộng không gian cho PostgreSQL
greSQL

QPS Queries Per Second Sốtruy vấn xửlý mỗi giây
RAG Retrieval-Augmented Genera- Sinh có hỗtrợtruy xuất
tion

RAM Random Access Memory Bộnhớtruy cập ngẫu nhiên
REST Representational State Transfer Kiến trúc API trạng thái biểu diễn
RNN Recurrent Neural Network Mạng nơ-ron hồi quy
RoBERTa Robustly Optimized BERT Ap- Phiên bản BERT tối ưu mạnh
proach

RQ Research Question Câu hỏi nghiên cứu
SCD Slowly Changing Dimension Chiều thay đổi chậm (quản lý lịch sửdữ
liệu)
SLA Service Level Agreement Cam kết mức dịch vụ
SOAP Simple Object Access Protocol Giao thức truy cập đối tượng đơn giản
SOTA State-of-the-Art Trạng thái tiên tiến nhất
SPA Single Page Application Ứng dụng web đơn trang
SRID Spatial Reference System Iden- Mã định danh hệtham chiếu không gian
tifier

SUPA Synthetic User-style Perturba- Khung benchmark địa chỉcó nhiễu tổng
tion Address hợp
TF-IDF Term Frequency–Inverse Docu- Trọng sốtừvựng cổđiển
ment Frequency

UTM Universal Transverse Mercator Hệchiếu toạđộphẳng
UUID Universally Unique Identifier Mã định danh duy nhất toàn cục
VnCoreNLP Vietnamese Core NLP toolkit Bộcông cụtách từtiếng Việt
VNAI VN Address Intelligence Tên hệthống đềxuất
VRAM Video Random Access Memory BộnhớGPU
WGS84 World Geodetic System 1984 Hệtoạđộđịa lý chuẩn quốc tế(SRID
4326)
WSM Weighted Sum Model Mô hình tổng trọng số(thuật toán tính
ACS)
XLM-R Cross-lingual Language Model Mô hình đa ngôn ngữdựa trên
RoBERTa RoBERTa


xiii


# **Chương 1** **MỞĐẦU**

## **1.1 Lý do hình thành đềtài**

Trong kỷnguyên sốhóa, sựchuyển dịch mạnh mẽtừmô hình bán lẻtruyền thống sang thương mại điện
tửđã làm gia tăng đột biến khối lượng giao dịch kỹthuật số. Yếu tốnày kéo theo nhu cầu khắt khe về
độchính xác của dữliệu địa chỉgiao nhận. đối với các doanh nghiệp hoạt động trong lĩnh vực logistics
và chuỗi cung ứng, dữliệu địa chỉkhông chỉđơn thuần là thông tin định vịmà đã trởthành một tài sản
chiến lược, quyết định hiệu quảvận hành và tối ưu hóa chi phí chặng cuối (last-mile logistics) [1].
Tuy nhiên, cơ sởdữliệu địa chỉtại Việt Nam đang đối mặt với một thách thức mang tính lịch sử.
Từnăm 2025, Việt Nam chính thức thực thi chính sách sắp xếp, sáp nhập các đơn vịhành chính trên
phạm vi toàn quốc theo Nghịquyết số202/2025/QH15 [2]. Cuộc cải cách này làm giảm sốlượng đơn
vịhành chính cấp tỉnh từ63 xuống còn 34, đồng thời sáp nhập hàng nghìn đơn vịcấp xã/phường [3].
Quy mô thay đổi được tóm lược tại Bảng 1.1. Sựkiện này tạo ra một “cú sốc dữliệu” (data shock) đối
với các hệthống thông tin, gây ra hiện tượng đứt gãy và bất đồng bộkhi địa chỉcũ không còn tồn tại về
mặt pháp lý nhưng vẫn được người dân sửdụng rộng rãi trong giao dịch. Hiện nay, sựthiếu hụt một hệ
thống quản trịdữliệu lưỡng thời (dual-epoch) có khảnăng truy vết và ánh xạlịch sửbiến động đơn vị
hành chính đang là rào cản lớn cho tính toàn vẹn dữliệu doanh nghiệp.


Bảng 1.1: Quy mô thay đổi đơn vịhành chính theo Nghịquyết 202/2025/QH15 và 35/2023/UBTVQH15


**Cấp hành chính** **Trước 01/07/2025** **Sau 01/07/2025** **Ghi chú**


Tỉnh / Thành phốtrực 63 **34** Giảm gần một nửa; nhiều tỉnh sáp nhập
thuộc Trung ương

Quận / Huyện / Thịxã / 705 **0** Cấp này bịbãi bỏtrong định dạng địa chỉ
Thành phốthuộc tỉnh chuẩn
Phường / Xã / Thịtrấn 10.033 **3.321** Sáp nhập sâu rộng, đặc biệt tại nông thôn
Tổng sốánh xạmã định _∼_ 10.571 quan hệchuyển đổi Lưu trong `mat.ward_mapping` và
danh `mat.unit_edge`


Đứng trước bối cảnh đó, việc đảm bảo tính nhất quán và khảnăng cập nhật liên tục từnguồn
dữliệu chính thống của Chính phủtrởthành yêu cầu cấp thiết. Giải pháp công nghệtất yếu là ứng
dụng các luồng công việc tựđộng (Data Orchestration) thông qua nền tảng n8n kết hợp với giao thức
SOAP/REST API từcác cổng thông tin quốc gia [4]. Cơ chếnày cho phép thiết lập một "nguồn sựthật


1


_1.2._ _MỤC TIÊU ĐỀTÀI_


duy nhất" (Single Source of Truth), giúp doanh nghiệp chủđộng đồng bộdanh mục hành chính ngay
khi có biến động địa giới.
Vềmặt kỹthuật xửlý, đặc thù phi cấu trúc và thói quen nhập liệu tựdo của người Việt — như viết
tắt, thiếu dấu hoặc sửdụng địa danh dân gian — đòi hỏi một cơ chếchuẩn hóa thông minh vượt ra
ngoài các bộquy tắc (rule-based) truyền thống. Điều này thúc đẩy việc ứng dụng các mô hình Học sâu
(Deep Learning) tiên tiến trong xửlý ngôn ngữtựnhiên (NLP). Hệthống cần một pipeline AI đa tầng,
tích hợp mô hình PhoBERT cho tác vụnhận diện thực thểtên (NER) [5], mạng Siamese với mô hình
nhúng mGTE cho bài toán truy xuất ngữnghĩa (Retrieval) [6], và khảnăng suy luận của mô hình ngôn
ngữlớn (LLM) Qwen đểtinh chỉnh các trường hợp địa chỉphức tạp.
Bên cạnh đó, tính chính xác của địa chỉcòn phụthuộc chặt chẽvào dữliệu địa không gian. Việc
xác định ranh giới đơn vịhành chính thường gặp sai sốlớn tại các khu vực tiếp giáp, gây ảnh hưởng
trực tiếp đến việc phân vùng giao nhận. Do đó, việc tích hợp các thuật toán hình học không gian trong
PostGIS đểtựđộng hiệu chỉnh đa giác ranh giới (polygon) dựa trên lịch sửtọa độthực tếlà hướng tiếp
cận mang tính đột phá nhằm thu hẹp khoảng cách giữa địa giới pháp lý và thực tếvận hành [7].
Thực tiễn vận hành cũng cho thấy việc phụthuộc hoàn toàn vào các nền tảng bản đồthương mại
như Google Maps hay cộng đồng như OpenStreetMap (OSM) đang bộc lộhai điểm nghẽn:


   - **Độtrễcập nhật (Update Latency):** Sựphản ứng chậm trước các quyết định sáp nhập địa giới
hành chính gây rủi ro sai lệch dữliệu.


   - **Gánh** **nặng** **chi** **phí** **(Operational** **Cost):** Chi phí truy vấn API khổng lồđối với các doanh
nghiệp có lưu lượng đơn hàng lớn làm giảm đáng kểbiên lợi nhuận.


Từnhững thách thức trên, nghiên cứu đềxuất xây dựng hệthống **VN Address Intelligence (VNAI)**
dựa trên **Khung giải pháp tiếp cận đa nguồn (Multi-source Approach)** . Giải pháp này sửdụng mô
hình thác nước (Waterfall Enrichment): ưu tiên dữliệu hành chính lõi đồng bộtrực tiếp từChính phủ
và chỉkhai thác tài nguyên từOSM hay Google Maps khi cần thiết. Cách tiếp cận này không chỉkhắc
phục triệt đểđộtrễdữliệu, tối ưu hóa chi phí API mà còn duy trì khảnăng truy vết thông tin hành
chính xuyên suốt cột mốc cải cách 2025.
Xuất phát từthực tiễn đó, đềtài **“Xây dựng khung giải pháp làm giàu và chuẩn hóa dữliệu địa**
**chỉViệt Nam sửdụng tiếp cận đa nguồn và thuật toán hình học không gian trong bối cảnh sắp**
**xếp đơn vịhành chính toàn quốc 2025”** được lựa chọn đểnghiên cứu và triển khai nhằm cung cấp
một giải pháp hạtầng dữliệu địa chỉbền vững cho kinh tếsốtại Việt Nam.

## **1.2 Mục tiêu đềtài**

### **1.2.1 Mục tiêu tổng quát**


Mục tiêu cốt lõi của đềtài là xây dựng một khung giải pháp (Framework) toàn diện và có khảnăng mở
rộng cho bài toán làm giàu, chuẩn hóa dữliệu địa chỉViệt Nam. Hệthống được thiết kếđểgiải quyết
triệt đểsựđứt gãy dữliệu địa chính trong bối cảnh thực thi chính sách sáp nhập đơn vịhành chính cấp
tỉnh, huyện và xã vào năm 2025. Khung giải pháp này chuyển đổi các truy vấn địa chỉphi cấu trúc,
chứa nhiễu thành dữliệu định danh chuẩn hóa có gắn tọa độkhông gian và lịch sửbiến động, hỗtrợtối
ưu hóa các hệthống logistics và thương mại điện tử.


2


_1.2._ _MỤC TIÊU ĐỀTÀI_

### **1.2.2 Mục tiêu cụthể**


Đểhiện thực hóa khung giải pháp, đềtài tập trung vào các mục tiêu kỹthuật cụthểsau:


1. **Xây dựng cơ sởtri thức hành chính đa phiên bản (Temporal-Aware Ontology):** Thiết lập
mô hình biểu diễn tri thức dựa trên kỹthuật _Slowly Changing Dimension_ (SCD Type 2) đểquản
lý vòng đời các đơn vịhành chính [8]. Mục tiêu là duy trì tính toàn vẹn của dữliệu thông qua
các quan hệ _mergesInto_, _renamedTo_ và _splitFrom_, cho phép ánh xạchính xác từđịa danh cũ sang
địa danh mới theo trục thời gian [9].


2. **Phát triển Pipeline xửlý ngôn ngữtựnhiên đa tầng:**


      - Ứng dụng mô hình **PhoBERT** kết hợp **Bi-LSTM-CRF** đểnhận diện thực thểtên (NER),
bóc tách địa chỉthô thành các thành phần: sốnhà, tên đường, phường, quận, tỉnh [5].

      - Triển khai kiến trúc **Siamese Network** với mô hình nhúng **mGTE** đểthực hiện so khớp
ngữnghĩa (Semantic Matching), ánh xạkết quảNER vềmã định danh GSOID trong cơ sở
dữliệu.

      - Tích hợp khảnăng suy luận của **Large Language Models (Qwen)** đểphân giải các trường
hợp địa chỉcực kỳmơ hồhoặc chỉchứa thông tin mô tảvịtrí dân gian.


3. **Đồng bộhóa dữliệu đa nguồn (Multi-source Enrichment):** Thiết kếluồng tựđộng hóa thông
qua _n8n workflow_ đểthu thập dữliệu từCổng dịch vụcông Quốc gia (SOAP/REST API) và làm
giàu dữliệu không gian từOpenStreetMap (OSM), Google Maps.


4. **Tối ưu hóa và tựhiệu chỉnh không gian (Geospatial Geometry):** Ứng dụng các thuật toán
hình học không gian trong **PostGIS** đểkiểm tra điểm thuộc vùng ( _Point-in-Polygon_ ). Đềxuất
các chiến lược _Buffer-Union_ và _Concave Hull_ đểtựđộng hiệu chỉnh ranh giới polygon hành
chính dựa trên tập hợp các tọa độgiao nhận thực tếcủa doanh nghiệp.


5. **Thiết lập hệthống đánh giá và Benchmarking:** Xây dựng bộchỉsốđánh giá đa chiều bao
gồm _Address Confidence Score_ (ACS) dựa trên mô hình _Weighted Sum Model_ (WSM) [10].



_ACS_ ( _d|q_ ) =



_n_


_wj_ _× vij_ (1.1)

_j_ =1



Đồng thời đo lường hiệu năng thông qua các chỉsố: _F_ 1-Score, _Precision_ @ _K_, _P_ 95 Latency và
_Throughput_ [11].

### **1.2.3 Câu hỏi nghiên cứu**


Đềtài tập trung giải đáp các vấn đềkhoa học sau:


   - **RQ1:** Làm thếnào đểmô hình hóa sựthay đổi ranh giới và định danh của đơn vịhành chính
theo thời gian nhằm đảm bảo khảnăng truy vết (traceability) dữliệu lịch sử?


   - **RQ2:** Sựkết hợp giữa mô hình học sâu đơn ngữ(PhoBERT) và mô hình nhúng đa ngôn ngữ
ngữcảnh dài (mGTE) mang lại hiệu quảnhư thếnào so với các phương pháp tìm kiếm từvựng
(Lexical Search) truyền thống?


   - **RQ3:** Các thuật toán hình học không gian có thểđóng góp gì vào việc tựhiệu chỉnh sai lệch
giữa ranh giới hành chính pháp lý và thực tếvận hành logistics?


3


_1.3._ _PHẠM VI VÀ ĐỐI TƯỢNG NGHIÊN CỨU_

## **1.3 Phạm vi và Đối tượng nghiên cứu**

### **1.3.1 Đối tượng nghiên cứu:**


   - Đối tượng chính của đềtài là dữliệu địa chỉtiếng Việt, bao gồm các cấu trúc phi tuyến (ngõ,
ngách, hẻm), địa danh dân gian và các biến thểkhông dấu, viết tắt trong các hệthống thông tin
logistics, thương mại điện tửvà hành chính công.


   - Các mô hình học máy và xửlý ngôn ngữtựnhiên (NLP) tiên tiến như PhoBERT (nhận diện thực
thể- NER), mGTE (so khớp ngữnghĩa - Siamese), và Qwen3 (Mô hình ngôn ngữlớn - LLM).


   - Các thuật toán hình học không gian (Geospatial Geometry) phục vụbài toán đối soát và tựhiệu
chỉnh ranh giới đa giác (polygon self-adjustment)

### **1.3.2 Phạm vi nghiên cứu:**


   - _Phạm vi không gian:_ Toàn lãnh thổViệt Nam, ưu tiên các vùng chịu ảnh hưởng mạnh bởi chính
sách sáp nhập và các đô thịlớn như TP. HồChí Minh, Hà Nội, Đà Nẵng.


   - _Phạm vi thời gian:_ Dữliệu địa chỉtrong giai đoạn chuyển giao trước và sau cuộc cải cách hành
chính toàn quốc có hiệu lực từngày 01/07/2025. Tập dữliệu thực nghiệm được giới hạn ởphạm
vi hơn 100.000 mẫu địa chỉthô.


   - _Phạm vi công nghệ:_ Triển khai khung giải pháp trên kiến trúc microservices với hệquản trị
PostgreSQL/PostGIS, công cụtìm kiếm Typesense, engine điều phối workflow n8n, và các
framework AI như PyTorch, HuggingFace.

## **1.4 Ý nghĩa Khoa học và Thực tiễn**

### **1.4.1 Ý nghĩa khoa học**


Nghiên cứu mang lại những đóng góp có giá trịvềmặt học thuật trong lĩnh vực giao thoa giữa Xửlý
ngôn ngữtựnhiên (NLP), Hệthống thông tin địa lý (GIS) và Quản trịdữliệu, cụthểtrên bốn phương
diện:


   - **Thứnhất**, nghiên cứu đềxuất một khung giải pháp (framework) toàn diện giải quyết bài toán
"nghịch lý độmịn" ( _granularity dilemma_ ) trong chuẩn hóa địa chỉtiếng Việt. Hệthống tích hợp
kiến trúc đa mô hình lai (Hybrid AI Architecture) kết hợp mô hình PhoBERT cho tác vụNhận
diện thực thểcó tên (NER) [5], mô hình nhúng đa ngữmGTE [6] áp dụng theo kiến trúc Siamese

[12] cho tìm kiếm ngữnghĩa mờ, và mô hình ngôn ngữlớn Qwen cho suy luận xửlý các trường
hợp ngoại lệ. Thực nghiệm cho thấy việc kết hợp kỹthuật RAG với LLM có tiềm năng cải thiện
độchính xác đáng kểso với các phương pháp đơn mô hình truyền thống.


   - **Thứhai**, nghiên cứu mởrộng cơ sởlý thuyết vềGIS bằng việc phát triển và đánh giá thực
nghiệm các chiến lược hiệu chỉnh đa giác không gian ( _polygon adjustment_ ) có khảnăng tựhọc
từlịch sửtọa độgiao nhận thực tếthông qua các thuật toán hình học không gian tích hợp trong
PostGIS. Các chiến lược bao gồm: ( _i_ ) mởrộng vùng phủtheo kỹthuật _Buffer-Union_ ; ( _ii_ ) tái


4


_1.5._ _BỐCỤC ĐỀTÀI_


dựng ranh giới theo thuật toán _Concave Hull_ / _Alpha Shape_ ; và ( _iii_ ) chỉnh sửa vi mô theo phương
pháp _Edge Injection_ .


   - **Thứba**, nghiên cứu xây dựng mô hình "Chuẩn hóa địa chỉnhận thức thời gian" ( _Temporal-_
_Aware_ _Address_ _Standardization_ ) thông qua kỹthuật SCD Type 2. Mô hình này cho phép hệ
thống xửlý "lưỡng thời" ( _dual-epoch_ ) — ánh xạchính xác các địa chỉthuộc cảhai giai đoạn
trước và sau sáp nhập hành chính 2025 theo Nghịquyết số202/2025/QH15 và Nghịquyết
số35/2023/UBTVQH15 [13] — mà không gặp hiện tượng quên lãng thảm họa ( _catastrophic_
_forgetting_ ).


   - **Thứtư**, nghiên cứu giải quyết vấn đềthiếu hụt bộdữliệu chuẩn quy mô lớn bằng việc ứng dụng
AI Agent kết hợp LLM đểtựđộng tạo sinh và gán nhãn dữliệu từcác nguồn mở. Phương pháp
này đảm bảo tính tái lập ( _reproducibility_ ) và minh bạch ( _transparency_ ) theo các tiêu chuẩn của
hệthống thu hồi thông tin hiện đại [11].

### **1.4.2 Ý nghĩa thực tiễn**


Nghiên cứu mang lại giá trịứng dụng trực tiếp cho các hệthống thông tin tại Việt Nam trong bối cảnh
cải cách địa chính:


   - **Thứnhất**, hệthống cung cấp giải pháp khắc phục hiện tượng "đứt gãy dữliệu" ( _data drift_ ) do
sáp nhập hành chính 2025. Bằng cách tựđộng ánh xạđịa chỉcũ sang định danh mới, nghiên cứu
giúp duy trì tính liên tục của dữliệu khách hàng trong các hệthống CRM và logistics, trực tiếp
giảm thiểu tỷlệgiao hàng thất bại ( _last-mile failure rate_ ).


   - **Thứhai**, thiết lập nguồn dữliệu hành chính nhất quán ( _single source of truth_ ) thông qua quy
trình ETL tựđộng kết hợp SOAP API từTổng cục Thống kê [3]. Cơ chếnày cho phép doanh
nghiệp chủđộng cập nhật danh mục đơn vịhành chính chính thức mà không phụthuộc vào các
nguồn dữliệu cộng đồng thiếu tính pháp lý.


   - **Thứba**, tối ưu hóa chi phí vận hành hạtầng dữliệu thông qua chiến lược "Fast and Free". Thay
vì phụthuộc vào các API thương mại đắt tiền như Google Maps [14], hệthống tích hợp nguồn
dữliệu mởtừOpenStreetMap và engine tìm kiếm nội bộTypesense [15] đểtựđộng bổsung tọa
độvà ranh giới hành chính.


   - **Thứtư**, module hiệu chỉnh đa giác không gian mang lại ứng dụng thực tiễn trong vận hành tại
các khu vực ven ranh giới địa lý. Hệthống có khảnăng học từlịch sửtọa độcác đơn hàng đã xử
lý thành công đểtựđộng tinh chỉnh ranh giới phân vùng, từđó tối ưu hóa việc điều phối và phân
bổđơn hàng trong chuỗi cung ứng chặng cuối.

## **1.5 Bốcục đềtài**


Nội dung nghiên cứu được tổchức thành 06 chương chính với cấu trúc logic như sau:


   - **Chương 1: Mởđầu.** Trình bày bối cảnh và tính cấp thiết của nghiên cứu trước sựbiến động địa
chính. Chương này xác định mục tiêu, đối tượng, phạm vi nghiên cứu và khẳng định các đóng
góp vềmặt khoa học trong việc xây dựng khung giải pháp làm giàu dữliệu địa chỉtại Việt Nam.


5


_1.5._ _BỐCỤC ĐỀTÀI_


   - **Chương 2: Tổng quan.** Phân tích và đánh giá các công trình nghiên cứu hiện đại vềxửlý ngôn
ngữtựnhiên (NLP) và hệthống thông tin địa lý (GIS). Chương này tập trung nhận diện các
khoảng trống tri thức trong việc chuẩn hóa địa chỉphi cấu trúc và xửlý dữliệu hành chính lưỡng
thời, từđó làm cơ sởcho hướng tiếp cận của đềtài.


   - **Chương 3: Cơ sởlý thuyết.** Thiết lập nền tảng lý luận vềkiến trúc Transformer, trọng tâm là
mô hình PhoBERT cho tác vụnhận diện thực thểtên (NER) và mô hình mGTE cho bài toán truy
xuất ngữnghĩa (Semantic Retrieval). Chương này cũng trình bày lý thuyết vềhọc sâu, cơ chế
Siamese Network trong so khớp dữliệu và các thuật toán hình học không gian trong PostGIS
nhằm xửlý ranh giới polygon.


   - **Chương 4: Phân tích yêu cầu và thiết kếkhung giải pháp.** Chi tiết hóa kiến trúc hệthống
VNAI với trọng tâm là pipeline xửlý AI toàn diện. Chương này mô tảquy trình thu nạp dữliệu
đa nguồn, thiết kếpipeline huấn luyện mô hình NER, kiến trúc retrieval đa tầng đểánh xạđịa chỉ
và logic suy luận của mô hình ngôn ngữlớn (LLM) trong việc xửlý các biến động hành chính
phức tạp.


   - **Chương 5: Thực nghiệm, Đánh giá hiệu năng và Tác động nghiệp vụ.** Trình bày kết quảthực
hiện các kịch bản kiểm thửtrên tập dữliệu địa chỉthực tế. Chương này tập trung đánh giá định
lượng hiệu năng của mô hình AI thông qua các chỉsốF1-score, Exact Match cho tác vụNER và
độchính xác của thuật toán retrieval, đồng thời phân tích khảnăng tối ưu hóa vận hành thông
qua các kỹthuật AI đã đềxuất.


   - **Chương 6: Kết luận và Hướng phát triển.** Tổng kết các kết quảđạt được, đối chiếu với mục
tiêu ban đầu và khẳng định tính thực tiễn của khung giải pháp AI. Chương này cũng thảo luận về
các hạn chếvà đềxuất định hướng phát triển hệthống theo hướng tựđộng hóa hoàn toàn quy
trình làm giàu dữliệu không gian.


6


# **Chương 2** **TỔNG QUAN NGHIÊN CỨU**

Chương này tập trung phân tích các công trình nghiên cứu trong và ngoài nước liên quan đến bài toán
chuẩn hóa địa chỉ, nhận diện thực thểtên (NER) và hệthông tin địa lý (GIS). Từviệc đánh giá các
phương pháp tiếp cận hiện đại, nghiên cứu xác định các khoảng trống tri thức (research gaps) còn tồn
tại, từđó xác lập tính cấp thiết và hướng đi của đềtài.

## **2.1 Các nghiên cứu quốc tếvềchuẩn hóa địa chỉ**


Trên bình diện quốc tế, bài toán chuẩn hóa địa chỉđã được tiếp cận thông qua các mô hình học sâu
(Deep Learning) mạnh mẽ. Điển hình là thư viện **DeepParse** (2020), một giải pháp sửdụng kiến trúc
Bi-LSTM đa tầng hạt (multi-national) đểbóc tách địa chỉdựa trên chuỗi [16]. Mặc dù đạt trạng thái
SOTA (State-of-the-art) cho các ngôn ngữhệLatinh như tiếng Anh hay tiếng Pháp, DeepParse bộc lộ
hạn chếkhi xửlý tiếng Việt do sựkhác biệt vềcấu trúc đơn vịhành chính và đặc thù từghép.
Nghiên cứu về **GeoAgent** (2024) đã mởra hướng đi mới bằng cách kết hợp sức mạnh suy luận
của Mô hình ngôn ngữlớn (LLM) với các công cụkhông gian [17]. GeoAgent có khảnăng hiểu các
thực thểtương đối như "đối diện", "rẽphải", tuy nhiên, rào cản vềđộtrễ(Latency > 1s) và chi phí vận
hành API cao khiến giải pháp này chưa thực sựtối ưu cho các hệthống xửlý hàng triệu vận đơn trong
logistics thời gian thực.

## **2.2 Các nghiên cứu tại Việt Nam và bài toán đặc thù**


Tại Việt Nam, các nghiên cứu trong 05 năm gần đây bắt đầu chuyển dịch từcác phương pháp dựa trên
tập luật (Rule-based) sang học máy và học sâu.

### **2.2.1 Tiếp cận dựa trên mô hình học máy truyền thống và Deep Learning**


**Đặng Đức Tùng (2019)** đã thực hiện các thực nghiệm so sánh giữa CRF, Bi-LSTM-CRF và SAGEL
trên tập dữliệu chuyên biệt vềbất động sản [18]. Nghiên cứu đạt độchính xác từ85% đến 95%, khẳng
định ưu thếcủa Bi-LSTM-CRF trong việc gán nhãn thực thểđịa chỉ. Tuy nhiên, do dataset có quy mô
nhỏvà tính chuyên biệt cao, mô hình khó có khảnăng tổng quát hóa cho toàn bộcác dạng địa chỉthô
đa dạng trong logistics.
Công trình của **Cao Hải Nam và Trần Việt Trung (2021)** tại hội nghịIEEE RIVF là một bước
tiến quan trọng khi ứng dụng kiến trúc _Siamese Network_ kết hợp với _Learning to Rank_ [12]. Phương


7


_2.3._ _PHÂN TÍCH KHOẢNG TRỐNG NGHIÊN CỨU (RESEARCH GAPS)_


pháp này đạt chỉsố _F_ 1 _>_ 85% thông qua việc so khớp vector ngữnghĩa. Tuy nhiên, nghiên cứu này
chỉtập trung vào dữliệu tĩnh, chưa tính đến các yếu tốbiến đổi hành chính lưỡng thời và sựsai lệch
ranh giới polygon.

### **2.2.2 Các tiêu chuẩn hành chính và bưu chính**


Ởkhía cạnh quản lý, **Vũ Chí Kiên và nhóm nghiên cứu BộThông tin và Truyền thông (2021)** đã đề
xuất xây dựng mã địa chỉbưu chính dựa trên tiêu chuẩn ISO 19160 cho hơn 23.4 triệu địa chỉ[19].
Mặc dù tạo ra bộkhung định danh tốt, nhưng hướng tiếp cận này thuần túy vềmặt hành chính, thiếu
các thuật toán AI đểtựđộng hóa việc làm sạch và chuẩn hóa các dữliệu đầu vào phi cấu trúc từphía
người dùng.

### **2.2.3 Xu hướng ứng dụng LLM trong phân tích ngữnghĩa tiếng Việt**


Gần đây, chiến dịch **VLSP 2025** với nhiệm vụ **viSemParse** đã đưa các dòng LLM hiện đại như Qwen3,
Gemma-3 vào thực nghiệm [20]. Kết quảcho thấy chỉsốSmatch đạt khoảng 0.58, cho thấy tiềm năng
lớn trong việc hiểu ý định người dùng. Tuy nhiên, các mô hình này vẫn chưa được tinh chỉnh chuyên
biệt cho bài toán chuẩn hóa địa chỉlưỡng thời và ánh xạGSOID chính xác.

## **2.3 Phân tích khoảng trống nghiên cứu (Research Gaps)**


Dựa trên việc tổng hợp các công trình tại Bảng 2.1, nghiên cứu nhận diện các khoảng trống tri thức cốt
lõi sau:


Bảng 2.1: So sánh các công trình nghiên cứu liên quan


**Tác giả/ Công trình** **Phương pháp chính** **Chỉsố** **Hạn chếcốt lõi**


Cao Hải Nam (2021) Siamese Network F1 > 85% Chưa xửlý biến động 2025
Đặng Đức Tùng (2019) Bi-LSTM-CRF 85-95% Dataset nhỏ, chuyên biệt BĐS
Vũ Chí Kiên (2021) ISO 19160 Quy mô lớn Thiếu cơ chếchuẩn hóa AI
GeoAgent (2024) LLM + Geospatial Hiểu ngữcảnh Độtrễvà chi phí cao
**VNAI (Đềxuất)** **Hybrid Pipeline (NER+Retrieval)** **P95 < 200ms** **Tối ưu cho bối cảnh 2025**


1. **Khoảng trống vềtính nhận thức thời gian (Temporal Awareness):** Hầu hết các hệthống hiện
tại đều coi dữliệu hành chính là tĩnh. Chưa có công trình nào tích hợp kỹthuật SCD Type 2 để
xửlý bài toán ánh xạ"địa chỉcũ - định danh mới" phát sinh từNghịquyết sáp nhập 2025 [2].


2. **Sựđứt gãy giữa NLP và GIS:** Các mô hình NLP hiện nay chỉdừng lại ởviệc bóc tách văn bản,
chưa có sựkết nối chặt chẽvới các thuật toán hiệu chỉnh polygon thực tế. Điều này dẫn đến tình
trạng địa chỉđã được chuẩn hóa vềmặt ký tựnhưng vẫn sai lệch vềvịtrí địa lý trên bản đồgiao
nhận.


3. **Nghịch lý giữa độchính xác và hiệu năng:** Các giải pháp dựa trên LLM nguyên bản có độ
chính xác cao nhưng không thểđáp ứng yêu cầu vềthroughput của hệthống logistics. Cần một
kiến trúc lai (Hybrid) đểtận dụng khảnăng suy luận của LLM trong khi vẫn đảm bảo độtrễthấp
thông qua PhoBERT và Typesense.


8


_2.4._ _XÁC LẬP HƯỚNG TIẾP CẬN CỦA ĐỀTÀI_

## **2.4 Xác lập hướng tiếp cận của đềtài**


Đểlấp đầy các khoảng trống trên, đềtài xác lập hướng nghiên cứu tập trung vào việc xây dựng hệ
thống **VNAI** với các điểm mới:


   - Thiết kế **Temporal-Aware Pipeline** sửdụng PhoBERT kết hợp mGTE đểxửlý dữliệu hành
chính xuyên suốt các thời kỳ.


   - Ứng dụng **Siamese Network** đểchuyển đổi bài toán chuẩn hóa thành bài toán truy xuất ngữ
nghĩa (Retrieval), giúp tăng tốc độxửlý.


   - Đềxuất thuật toán **Self-adjusting Polygon** trong PostGIS đểtựđộng thu hẹp sai lệch giữa ranh
giới hành chính và thực tếvận hành logistics.


9


# **Chương 3** **Cơ sởlý thuyết**

Chương 2 đã xác lập tính cấp thiết của khung giải pháp VNAI cùng các khoảng trống nghiên cứu trong
bài toán chuẩn hóa và làm giàu dữliệu địa chỉViệt Nam. Đểhiện thực hóa các mục tiêu nghiên cứu và
giải đáp ba câu hỏi cốt lõi đã đặt ra tại Mục 1.2.3, chương này thiết lập nền tảng lý luận cho toàn bộ
kiến trúc hệthống được trình bày ởChương 4.

## **3.1 Tổng quan định vị**


Khung giải pháp VNAI hợp nhất ba lĩnh vực kỹthuật: xửlý ngôn ngữtựnhiên (NLP) tiếng Việt, truy
xuất thông tin (Information Retrieval) và xửlý dữliệu địa lý (Geospatial Computing). Tương ứng với
mỗi câu hỏi nghiên cứu (RQ) là một chùm nền tảng lý thuyết cần thiết, được tóm lược tại Bảng 3.1.


Bảng 3.1: Định vịnền tảng lý thuyết theo câu hỏi nghiên cứu


**Câu hỏi** **Bài toán cốt lõi** **Nền tảng lý thuyết**


RQ1 Mô hình hóa biến động hành chính theo thời gian, đảm bảo truy Slowly Changing
vết _(traceability)_ Dimension Type 2; tích
hợp trong Mục 3.7
RQ2 So sánh hybrid PhoBERT + mGTE với tìm kiếm từvựng truyền Transformer (3.2);
thống PhoBERT NER (3.3);
mGTE Retrieval (3.4);
Siamese Network (3.5)
RQ3 Thuật toán hình học không gian cho tựhiệu chỉnh polygon Geospatial & PostGIS
(3.6)


Chương được tổchức theo trình tựlogic từkiến trúc nền đến ứng dụng cụthể: Mục 3.2 giới thiệu
kiến trúc Transformer làm cơ sởcho mọi mô hình ngôn ngữtiên tiến; Mục 3.3 đi sâu vào PhoBERT
cho tác vụnhận diện thực thểtên; Mục 3.4 phân tích mGTE và kiến trúc truy xuất ngữnghĩa đa tầng;
Mục 3.5 trình bày mạng Siamese cùng các hàm mất mát học so khớp; Mục 3.6 đi vào các thuật toán
hình học không gian trong PostGIS phục vụđịnh vịvà hiệu chỉnh ranh giới; Mục 3.7 thiết lập mô hình
Điểm tin cậy địa chỉ(ACS) cho tầng hỗtrợra quyết định.


10


_3.2._ _KIẾN TRÚC TRANSFORMER_

## **3.2 Kiến trúc Transformer**

### **3.2.1 Bối cảnh ra đời và động lực**


Trước khi kiến trúc Transformer được đềxuất, các mô hình tiên tiến trong xửlý ngôn ngữtựnhiên chủ
yếu dựa trên mạng nơ-ron hồi quy (Recurrent Neural Network — RNN) và các biến thểnhư LSTM
(Long Short-Term Memory) [21]. Mặc dù có khảnăng xửlý chuỗi văn bản với phụthuộc dài hạn,
các mô hình hồi quy bộc lộhai hạn chếcốt lõi cản trởkhảnăng mởrộng. Thứnhất, tính tuần tự
(sequential nature) của phép tính hồi quy khiến quá trình huấn luyện không thểsong song hóa hiệu
quảtrên GPU, làm tăng đáng kểthời gian huấn luyện trên các tập ngữliệu lớn. Thứhai, sựsuy giảm
gradient (vanishing gradient) khi chuỗi dài làm giảm khảnăng nắm bắt ngữcảnh xa, đặc biệt bất lợi
cho các bài toán mà thông tin quan trọng phân tán trên toàn chuỗi như nhận diện thực thểđịa chỉ(số
nhà thường ởđầu chuỗi nhưng phụthuộc vềmặt phân cấp vào tên tỉnh ởcuối chuỗi).
Năm 2017, Vaswani và cộng sựđềxuất kiến trúc **Transformer** trong công trình _Attention Is All_
_You Need_ [22], hoàn toàn loại bỏcơ chếhồi quy và thay thếbằng cơ chếchú ý (attention mechanism)
thuần túy. Kiến trúc này nhanh chóng trởthành nền tảng cho các mô hình ngôn ngữhiện đại như BERT,
GPT, RoBERTa, T5 và các mô hình ngôn ngữlớn (LLM) thếhệmới.

### **3.2.2 Cơ chếSelf-Attention**


Cơ chếchú ý bản thân (Self-Attention) cho phép mỗi vịtrí (token) trong chuỗi đầu vào tham chiếu đến
tất cảcác vịtrí khác, qua đó xây dựng biểu diễn ngữcảnh giàu thông tin. Cụthể, với chuỗi đầu vào
được biểu diễn dưới dạng ma trận _X_ _∈_ R _[n][×][d]_, trong đó _n_ là độdài chuỗi và _d_ là sốchiều embedding,
ba ma trận trọng sốcó thểhọc _W_ _[Q]_ _, W_ _[K]_ _, W_ _[V]_ _∈_ R _[d][×][d][k]_ được sửdụng đểsinh ra ba biểu diễn Truy vấn
(Query), Khóa (Key) và Giá trị(Value):


_Q_ = _XW_ _[Q]_ _,_ _K_ = _XW_ _[K]_ _,_ _V_ = _XW_ _[V]_ (3.1)


Đầu ra của lớp Self-Attention được tính theo công thức Scaled Dot-Product Attention:




         - _QK_ _⊤_
Attention( _Q, K, V_ ) = softmax ~~_√_~~
_dk_




_V_ (3.2)



Trong đó _dk_ là sốchiều của vector Khóa. Phép chia cho _[√]_ _dk_ đóng vai trò ổn định gradient, ngăn không
cho hàm softmax rơi vào vùng bão hòa khi _dk_ lớn. Ma trận _QK_ _[⊤]_ _∈_ R _[n][×][n]_ biểu diễn điểm tương tác
giữa mọi cặp vịtrí; sau khi chuẩn hóa qua softmax, kết quảlà một ma trận trọng sốchú ý mô tảmức
độliên quan giữa các token.

### **3.2.3 Multi-Head Attention**


Đểmô hình có thểnắm bắt nhiều khía cạnh ngữnghĩa khác nhau cùng lúc, Transformer áp dụng cơ
chếchú ý đa đầu (Multi-Head Attention). Đầu vào được chiếu vào _h_ không gian con khác nhau, mỗi
không gian được xửlý bởi một đầu attention độc lập:


MultiHead( _Q, K, V_ ) = Concat(head1 _, . . .,_ head _h_ ) _W_ _[O]_ (3.3)


head _i_ = Attention( _QWi_ _[Q][,]_ _[KW][ K]_ _i_ _[,]_ _[V W][ V]_ _i_ [)] (3.4)


11


_3.2._ _KIẾN TRÚC TRANSFORMER_


Trong bối cảnh xửlý địa chỉViệt Nam, cơ chếđa đầu cho phép một đầu tập trung vào quan hệphân
cấp hành chính (Phường _→_ Quận _→_ Tỉnh), trong khi đầu khác nắm bắt quan hệvịtrí tương đối giữa
các thành phần ký tự(Sốnhà _→_ Tên đường _→_ Phường), giúp mô hình hiểu được cấu trúc lồng nhau
đặc thù của địa chỉ.

### **3.2.4 Kiến trúc Encoder-Decoder và Positional Encoding**


Transformer nguyên bản gồm hai khối chính: Encoder (ngăn xếp 6 lớp encoder giống nhau) và Decoder
(ngăn xếp 6 lớp decoder). Mỗi khối Encoder bao gồm một lớp Multi-Head Self-Attention nối tiếp một
lớp Feed-Forward Network (FFN), kết hợp với Residual Connection và Layer Normalization đểổn
định quá trình huấn luyện sâu. Khối Decoder bổsung lớp Encoder-Decoder Attention (cross-attention)
đểkhớp thông tin giữa chuỗi nguồn và chuỗi đích.
Các mô hình ngôn ngữhiện đại thường chỉsửdụng một trong hai khối: BERT [23] và RoBERTa

[24] chỉdùng Encoder (phù hợp cho phân loại, NER, truy xuất); GPT chỉdùng Decoder (phù hợp cho
sinh văn bản). Trong khung giải pháp VNAI, kiến trúc encoder-only được lựa chọn cho hai pipeline cốt
lõi (NER và Retrieval) do bài toán chuẩn hóa địa chỉchủyếu yêu cầu hiểu (understanding) thay vì sinh
văn bản (generation).
Do cơ chếself-attention không có khảnăng tựnhận biết thứtựtoken (tính chất hoán vịbất biến),
Transformer bổsung biểu diễn vịtrí (Positional Encoding — PE) vào embedding đầu vào. Vaswani và
cộng sựđềxuất sửdụng các hàm sin/cos:




      - _pos_
_PE_ ( _pos,_ 2 _i_ ) = sin
10000 [2] _[i/d]_ [model]




- - _pos_
_,_ _PE_ ( _pos,_ 2 _i_ +1) = cos
10000 [2] _[i/d]_ [model]




(3.5)



Cách mã hóa này cho phép mô hình tổng quát hóa với chuỗi dài hơn so với chuỗi đã thấy trong huấn
luyện và học các quan hệvịtrí tương đối thông qua các phép biến đổi tuyến tính của PE.


12


_3.2._ _KIẾN TRÚC TRANSFORMER_


Hình 3.1: Kiến trúc tổng thểTransformer.


13


_3.3._ _PHOBERT CHO NHẬN DIỆN THỰC THỂTÊN_

## **3.3 PhoBERT cho Nhận diện thực thểtên**

### **3.3.1 TừBERT đến RoBERTa**


BERT (Bidirectional Encoder Representations from Transformers) [23] là mô hình tiên phong áp dụng
kiến trúc Encoder-only của Transformer cho học biểu diễn ngôn ngữphổquát. BERT được tiền huấn
luyện (pre-training) trên hai tác vụ: Masked Language Modeling (MLM) — dựđoán các token bịche
ngẫu nhiên trong câu — và Next Sentence Prediction (NSP) — dựđoán quan hệgiữa hai câu liên tiếp.
Sau giai đoạn tiền huấn luyện trên ngữliệu lớn, mô hình được tinh chỉnh (fine-tuning) cho các tác vụ
hạnguồn cụthể.
RoBERTa (Robustly Optimized BERT Approach) [24] cải tiến BERT thông qua bốn thay đổi chính:
(i) loại bỏtác vụNSP do thực nghiệm cho thấy không cải thiện chất lượng; (ii) áp dụng mặt nạđộng
(dynamic masking) thay vì mặt nạtĩnh; (iii) huấn luyện với kích thước batch lớn hơn và sốbước nhiều
hơn; (iv) sửdụng ngữliệu lớn hơn 10 lần so với BERT gốc. Những cải tiến này cho phép RoBERTa đạt
hiệu năng vượt trội trên các benchmark chuẩn như GLUE và SQuAD, đồng thời trởthành nền tảng cho
các mô hình ngôn ngữđơn ngữ(monolingual) chất lượng cao.

### **3.3.2 PhoBERT — Đơn ngữhóa cho tiếng Việt**


PhoBERT [5] là mô hình ngôn ngữtiền huấn luyện chuyên biệt cho tiếng Việt, được phát triển dựa trên
kiến trúc RoBERTa. Mô hình có hai phiên bản: PhoBERT-base (135M tham số, 12 lớp encoder) và
PhoBERT-large (370M tham số, 24 lớp encoder). PhoBERT được huấn luyện trên ngữliệu khoảng
20GB văn bản tiếng Việt thu thập từWikipedia tiếng Việt và tập tin tức. Ba lựa chọn thiết kếcốt lõi
của PhoBERT đáng chú ý đối với bài toán xửlý địa chỉ.
Thứnhất, tách từbằng VnCoreNLP [25]: tiếng Việt là ngôn ngữđơn lập với ranh giới từmờ, một từ
tiếng Việt có thểgồm nhiều âm tiết phân tách bởi khoảng trắng (ví dụ: "Hà Nội", "Đại học"). PhoBERT
yêu cầu văn bản đầu vào được tách từtrước khi mã hóa, qua đó giảm thiểu độmơ hồngữnghĩa so với
việc xửlý ởmức âm tiết hoặc ký tự.
Thứhai, mã hóa subword bằng FastBPE: phương pháp Byte-Pair Encoding (BPE) cho phép xửlý
các từngoài từđiển (Out-of-Vocabulary — OOV) bằng cách phân rã chúng thành các đơn vịsubword.
Đây là tính chất cực kỳquan trọng cho dữliệu địa chỉvốn chứa nhiều biến thểviết tắt, sai chính tảnhẹ,
hoặc tên địa danh mới chưa có trong từđiển huấn luyện.
Thứba, đơn ngữhóa (monolingual): so với các mô hình đa ngôn ngữnhư mBERT hay XLM-R,
PhoBERT tập trung toàn bộsức biểu diễn vào tiếng Việt, qua đó đạt hiệu năng cao hơn trên các tác vụ
tiếng Việt với cùng sốtham số. Theo [5], PhoBERT-base vượt XLM-R-base khoảng 1.6–1.9 điểm F1
trên VLSP NER, một cách biệt có ý nghĩa thống kê đối với bài toán nhận diện thực thể.

### **3.3.3 Bài toán NER và sơ đồnhãn BIO**


Nhận diện thực thểtên (Named Entity Recognition — NER) là tác vụgán nhãn cho mỗi token trong văn
bản nhằm xác định nó có thuộc vềmột thực thểnào không, và nếu có thì thuộc loại thực thểnào. Đối
với bài toán bóc tách địa chỉViệt Nam, tập nhãn được thiết kếgồm các loại thực thể: `HOUSENUM` (số
nhà), `ALLEY` (ngõ/ngách/hẻm), `STREET` (tên đường), `WARD` (phường/xã), `DISTRICT` (quận/huyện

- vẫn cần cho dữliệu lưỡng thời), `PROVINCE` (tỉnh/thành phố), và `LOCATION` (địa danh dân gian,
POI).


14


_3.3._ _PHOBERT CHO NHẬN DIỆN THỰC THỂTÊN_


Sơ đồnhãn được sửdụng rộng rãi nhất là BIO (Beginning, Inside, Outside): mỗi loại thực thể _T_ tạo
ra hai nhãn `B-T` (token bắt đầu của thực thể) và `I-T` (token nằm bên trong thực thể), kèm theo nhãn `O`
(outside, không thuộc thực thểnào). Ví dụ, chuỗi đầu vào hậu cải cách 2025 sau khi tách từ“ _268 Lý_
_Thường_Kiệt, Phường Diên_Hồng, TP. HCM_ ” sẽđược gán nhãn:


_268_ _Lý_ _Thường_Kiệt_ _Phường_ _Diên_Hồng_ _TP._HCM_
B-HOUSENUM B-STREET I-STREET O B-WARD B-PROVINCE


Lưu ý: cặp nhãn `B-DISTRICT` / `I-DISTRICT` vẫn được giữtrong tập nhãn đểxửlý dữliệu _lưỡng_
_thời_ - các địa chỉtiền cải cách (ví dụ“ _268 Lý Thường_Kiệt, Phường 14, Quận 10, TP._HCM_ ”) sẽ
kích hoạt thêm hai nhãn này khi mô hình nhận ra cấp huyện cũ.

### **3.3.4 PhoBERT + BiLSTM-CRF cho NER địa chỉ**


Kiến trúc kết hợp PhoBERT với một lớp BiLSTM (Bidirectional LSTM) và một lớp Conditional
Random Field (CRF) đã trởthành chuẩn de facto cho NER tiếng Việt [5]. Luồng xửlý gồm ba giai
đoạn:


1. PhoBERT mã hóa chuỗi đầu vào thành các vector biểu diễn ngữcảnh _h_ 1 _, h_ 2 _, . . ., hn_ _∈_ R _[d][h]_
( _dh_ = 768 cho PhoBERT-base).


2. Lớp BiLSTM tinh chỉnh các vector này, bổsung thông tin tuần tựcục bộmà self-attention có thểbỏ
sót: _h_ [˜] _i_ = [ _[−→]_ _hi_ ; _[←−]_ _hi_ ].


3. Lớp CRF mô hình hóa quan hệgiữa các nhãn liên tiếp. Khác với việc dựđoán độc lập từng nhãn
(token-wise softmax), CRF học một ma trận chuyển trạng thái _A_ _∈_ R _[|][L][|×|][L][|]_ ( _|L|_ là sốnhãn) để
áp đặt các ràng buộc cấu trúc: ví dụ, nhãn `I-WARD` không được phép xuất hiện ngay sau nhãn
`B-PROVINCE` .


Hàm mất mát của CRF được định nghĩa qua xác suất có điều kiện của chuỗi nhãn _y_ = ( _y_ 1 _, . . ., yn_ )
cho chuỗi đầu vào _x_ :



�� _n_     exp _i_ =1 _[h]_ [˜] _[i]_ [[] _[y][i]_ [] +] [�] _i_ _[n]_ =1 _[−]_ [1] _[A]_ [[] _[y][i][, y][i]_ [+1][]]
_P_ ( _y_ _| x_ ) =



(3.6)
�� _n_   _y_ _[′]_ _∈Y_ [exp] _i_ =1 _[h]_ [˜] _[i]_ [[] _[y]_ _i_ _[′]_ [] +] [�] _i_ _[n]_ =1 _[−]_ [1] _[A]_ [[] _[y]_ _i_ _[′][, y]_ _i_ _[′]_ +1 []]







Trong đó _Y_ là tập tất cảcác chuỗi nhãn hợp lệ. Quá trình giải mã ởthời điểm suy luận sửdụng thuật
toán Viterbi đểtìm chuỗi nhãn _y_ _[∗]_ = arg max _y P_ ( _y_ _| x_ ) với độphức tạp _O_ ( _n · |L|_ [2] ). Toàn bộluồng xử
lý ba giai đoạn này được tóm lược tại Hình 3.2.


15


_3.3._ _PHOBERT CHO NHẬN DIỆN THỰC THỂTÊN_


Hình 3.2: Kiến trúc PhoBERT + BiLSTM-CRF cho tác vụNER địa chỉtiếng Việt.

### **3.3.5 So sánh PhoBERT với mô hình đa ngôn ngữ**


Bảng 3.2 so sánh PhoBERT với hai mô hình đa ngôn ngữphổbiến trên tác vụNER tiếng Việt. Các
con sốhiệu năng được lấy từkết quảcông bốtrong tài liệu PhoBERT [5] trên benchmark VLSP NER
2018, làm cơ sởcho lựa chọn PhoBERT trong khung giải pháp VNAI.


16


_3.4._ _MGTE VÀ TRUY XUẤT NGỮNGHĨA ĐA TẦNG_


Bảng 3.2: So sánh PhoBERT với mô hình đa ngôn ngữtrên tác vụNER tiếng Việt


**Mô hình** **Tham số** **Đơn/Đa ngôn ngữ** **F1 VLSP NER** **Đặc điểm**


mBERT-base 110M 104 ngôn ngữ _∼_ 92.7 Word-piece tokenizer, không tách từ
tiếng Việt
XLM-R-base 270M 100 ngôn ngữ _∼_ 93.8 SentencePiece, ngữliệu CC100 đa
ngôn ngữ
PhoBERT-base 135M Tiếng Việt _∼_ 94.5–95.4 FastBPE + VnCoreNLP, ngữliệu
20GB tiếng Việt

## **3.4 mGTE và truy xuất ngữnghĩa đa tầng**

### **3.4.1 Bài toán Semantic Retrieval**


Sau khi pipeline NER tách chuỗi địa chỉthô thành các thành phần có cấu trúc, bài toán tiếp theo là ánh
xạcác thành phần này vềcơ sởtri thức hành chính chuẩn (Master Administrative Table) đểgán mã
định danh. Đây là bài toán Truy xuất ngữnghĩa (Semantic Retrieval): cho một truy vấn _q_ (chuỗi tên
đơn vịhành chính có thểchứa lỗi chính tả, viết tắt, hoặc dùng tên dân gian) và một bộsưu tập tài liệu
_D_ = _{d_ 1 _, d_ 2 _, . . ., dN_ _}_ (các đơn vịhành chính chuẩn), tìm tài liệu _d_ _[∗]_ _∈D_ sao cho:


_d_ _[∗]_ = arg max (3.7)
_d∈D_ [Sim(] _[q, d]_ [)]


Trong đó Sim( _·, ·_ ) là một hàm đo độtương đồng ngữnghĩa.
Khác với tìm kiếm từvựng truyền thống dựa trên BM25 hoặc TF-IDF [11] vốn chỉkhớp khi chuỗi
truy vấn và tài liệu chia sẻtoken cụthể, truy xuất ngữnghĩa cho phép khớp các biến thểkhông chia sẻ
ký tựnhư "Sài Gòn" _↔_ "TP. HồChí Minh" hoặc "Q. Nhất" _↔_ "Quận 1".

### **3.4.2 Mô hình nhúng văn bản và kiến trúc Bi-encoder**


Nguyên lý cốt lõi của truy xuất ngữnghĩa là biểu diễn cảtruy vấn lẫn tài liệu dưới dạng vector mật
độcao trong cùng một không gian, sao cho khoảng cách giữa hai vector phản ánh độtương đồng ngữ
nghĩa. Các mô hình nhúng văn bản hiện đại như Sentence-BERT [26], DPR [27], và mGTE [6] áp
dụng kiến trúc Bi-encoder (còn gọi là dual-encoder hoặc twin-encoder).
Trong kiến trúc Bi-encoder, hai encoder _Eq_ và _Ed_ (thường chia sẻtrọng số) độc lập mã hóa truy
vấn và tài liệu thành các vector cốđịnh:


_⃗q_ = _Eq_ ( _q_ ) _∈_ R _[d]_ _,_ _⃗d_ = _Ed_ ( _d_ ) _∈_ R _[d]_ (3.8)


Sau đó, độtương đồng được tính bằng tích vô hướng hoặc cosine:


                 -                 - _⃗q ·_ _d_ _[⃗]_
Sim( _q, d_ ) = cos _⃗q, d_ _[⃗]_ = (3.9)

_∥⃗q∥·_ �� _⃗d_ ��

                       -                        

Ưu điểm cốt lõi của Bi-encoder là khảnăng tiền tính toán: toàn bộvector _d_ _[⃗]_ của các tài liệu trong cơ
sởtri thức được tính trước và lưu vào chỉmục vector. Tại thời điểm truy vấn, hệthống chỉcần mã hóa _⃗q_
một lần và thực hiện tìm kiếm láng giềng gần nhất, qua đó đạt độtrễthấp ngay cảvới cơ sởtri thức
hàng triệu bản ghi.


17


_3.4._ _MGTE VÀ TRUY XUẤT NGỮNGHĨA ĐA TẦNG_

### **3.4.3 mGTE và Late Interaction**


mGTE (multilingual Generalized long-context Text Embedding) [6] là mô hình embedding đa ngôn
ngữthếhệmới với hai đặc điểm phù hợp đặc biệt cho bài toán địa chỉViệt Nam: (i) cửa sổngữcảnh
dài 8192 token cho phép mã hóa các tài liệu địa chỉkèm metadata phong phú; (ii) hỗtrợđa ngôn ngữ
giúp xửlý các trường hợp địa chỉpha tạp tiếng Việt và tiếng Anh (ví dụ: "District 1, HCMC").
Tuy nhiên, kiến trúc Bi-encoder cổđiển có một hạn chếcốt lõi gọi là **Granularity** **Dilemma**
(nghịch lý độmịn). Việc nén toàn bộchuỗi thành một vector duy nhất có thểlàm mất các chi tiết hạt
mịn quan trọng cho bài toán địa chỉ— ví dụ, sựkhác biệt giữa sốnhà 90 và 92 trên cùng một con
đường có thểbịtriệt tiêu trong quá trình pooling. Đểgiải quyết, các nghiên cứu gần đây như ColBERT

[28] và mGTE-rerank đềxuất cơ chếLate Interaction: thay vì nén thành một vector, tài liệu được biểu
diễn bằng tập hợp vector tại từng token, và độtương đồng được tính như sau:



SimLate( _q, d_ ) =



_|q|_



_i_ =1



_|d|_  -  max _⃗qi, d_ _[⃗]_ _j_ (3.10)
_j_ =1 [cos]



Toán tửMaxSim (cực đại của cosine giữa mỗi token truy vấn với mọi token tài liệu, sau đó tổng
hợp qua các token truy vấn) cho phép duy trì độchi tiết hạt mịn trong khi vẫn đảm bảo hiệu năng tương
đối tốt thông qua việc đánh chỉmục các vector token trước. Hình 3.3 minh hoạtrực quan ba kiến trúc;
Bảng 3.3 tóm lược điểm khác biệt.


Hình 3.3: Ba kiến trúc retrieval: Bi-encoder, Late Interaction và Cross-encoder.

### **3.4.4 Approximate Nearest Neighbo - ANN**


Trong thực tếtriển khai với cơ sởtri thức hàng triệu vector, việc tính cosine với toàn bộcorpus (Exact
Search) trởnên không khảthi vềmặt hiệu năng. Khung giải pháp VNAI áp dụng kỹthuật Tìm kiếm
Láng giềng gần nhất Xấp xỉ(Approximate Nearest Neighbor — ANN) đểđạt độtrễdưới mili-giây trên
hàng triệu vector, với hai kỹthuật cốt lõi:


18


_3.5._ _MẠNG SIAMESE (SIAMESE NETWORK) VÀ HỌC SÂU SO KHỚP (DEEP METRIC_
_LEARNING)_


Bảng 3.3: So sánh ba kiến trúc encoder cho bài toán retrieval


**Tiêu chí** **Bi-encoder** **Late Interaction** **Cross-encoder**


Biểu diễn 1 vector/tài liệu N vector/tài liệu Không tách rời
Tiền tính toán Có (toàn bộcorpus) Có (toàn bộtoken) Không thể
Độchi tiết Thô (single vector) Hạt mịn (per-token Cao nhất (full attention)
MaxSim)

Latency truy Rất thấp ( _∼_ ms) Thấp ( _∼_ 10ms) Cao ( _∼_ 100ms/cặp)
vấn

Phù hợp cho Truy xuất sơ tuyển Re-ranking giữchi tiết Re-ranking độchính xác
cao


- **IVF (Inverted File Index)** [29]: phân cụm không gian vector thành _k_ cluster (sửdụng k-means), tại
thời điểm truy vấn chỉtìm trong nprobe cluster gần nhất với truy vấn, qua đó giảm sốphép tính tích
vô hướng từ _N_ xuống _∼_ _N/k ·_ nprobe.


- **HNSW (Hierarchical Navigable Small World)** [30]: xây dựng đồthịphân cấp với các "đường tắt"
ởtầng cao, tìm kiếm bằng cách di chuyển từnode bất kỳởtầng cao xuống tầng đáy theo nguyên tắc
tham lam, đạt độphức tạp _O_ (log _N_ ) với độphục hồi (recall) cao.


Cụthể, thư viện FAISS được lựa chọn cho VNAI do hỗtrợtốt cảCPU và GPU, có thểtích hợp trực
tiếp với pipeline PyTorch.

## **3.5 Mạng Siamese (Siamese Network) và Học sâu so khớp (Deep** **Metric Learning)**

### **3.5.1 Kiến trúc Siamese**


Mạng Siamese (Siamese Network) [31] là một kiến trúc gồm hai (hoặc nhiều) nhánh mạng nơ-ron chia
sẻtrọng số, được thiết kếđểhọc một hàm đo khoảng cách giữa các đầu vào. Mục tiêu của Siamese là
học một không gian biểu diễn (embedding space) sao cho các mẫu tương tựnằm gần nhau và các mẫu
khác biệt nằm xa nhau theo metric được chọn (thường là Euclidean hoặc cosine).
Trong bài toán so khớp địa chỉ, kiến trúc Siamese được áp dụng theo mô hình: hai đầu vào là cặp
( _q, d_ ) gồm truy vấn và ứng viên đơn vịhành chính, hai nhánh encoder cùng kiến trúc (ví dụcùng dùng
mGTE) chia sẻtrọng sốsinh ra cặp embedding ( _⃗q, d_ _[⃗]_ ), và đầu ra là điểm tương đồng. Việc chia sẻtrọng
sốđảm bảo tính đối xứng: Sim( _q, d_ ) = Sim( _d, q_ ), đây là tính chất quan trọng cho bài toán matching.

### **3.5.2 Hàm mất mát: Contrastive Loss và Triplet Loss**


Đểhuấn luyện mạng Siamese, hai hàm mất mát phổbiến được sửdụng. Thứnhất, Contrastive Loss

[32] hoạt động trên các cặp mẫu kèm nhãn nhịphân _y_ _∈{_ 0 _,_ 1 _}_ (1: cặp tương đồng, 0: cặp khác biệt):


_L_ cont = _y · D_ [2] + (1 _−_ _y_ ) _·_ max(0 _, m −_ _D_ ) [2] (3.11)


Trong đó _D_ = _⃗q −_ _⃗d_ là khoảng cách Euclidean, _m_ là margin (biên cách ly). Hàm mất mát này phạt
��� ���

khoảng cách lớn giữa cặp tương đồng và phạt khoảng cách nhỏhơn margin giữa cặp khác biệt.


19


_3.6._ _HÌNH HỌC KHÔNG GIAN VÀ POSTGIS_


Thứhai, Triplet Loss [33] hoạt động trên bộba mẫu ( _a, p, n_ ) gồm anchor, positive (mẫu tương tự
anchor) và negative (mẫu khác biệt anchor):


              -              _L_ triplet = max 0 _,_ _∥⃗a −_ _⃗p∥_ [2] _−∥⃗a −_ _⃗n∥_ [2] + _α_ (3.12)


Trong đó _α_ là margin yêu cầu khoảng cách anchor-negative phải lớn hơn anchor-positive ít nhất một
lượng _α_ . Triplet Loss thường cho hiệu năng vượt trội Contrastive Loss trong các bài toán similarity
learning quy mô lớn nhờtính chất "học tương đối" giữa ba mẫu. Hình 3.4 minh hoạcấu trúc Siamese
và hiệu ứng kéo gần — đẩy xa của Triplet Loss trong không gian embedding.


Hình 3.4: Mạng Siamese và minh hoạhiệu ứng của Triplet Loss trong không gian embedding.

### **3.5.3 Ứng dụng cho bài toán so khớp địa chỉ**


Trong khung VNAI, mạng Siamese được áp dụng đểfine-tune mô hình mGTE cho domain địa chỉViệt
Nam. Cách tiếp cận như sau:


1. **Sinh dữliệu huấn luyện** : từcơ sởtri thức hành chính, sinh các bộba (anchor, positive, negative)
với anchor là chuỗi địa chỉthô, positive là phiên bản chuẩn hóa của cùng đơn vị, negative là đơn vị
khác (ưu tiên hard negative — các đơn vịcó tên gần giống nhưng khác mã).


2. **Fine-tuning** : huấn luyện mGTE với Triplet Loss trên tập dữliệu sinh ra, qua đó kéo gần các biến
thểcủa cùng đơn vịvà đẩy xa các đơn vịkhác biệt.


3. **Suy luận** : tại thời điểm truy vấn, áp dụng pipeline retrieval đã trình bày tại Mục 3.4 với encoder đã
được fine-tune.

## **3.6 Hình học không gian và PostGIS**

### **3.6.1 Mô hình dữliệu không gian**


Tiêu chuẩn OGC Simple Feature Access [34] định nghĩa các kiểu hình học cơ bản tạo nên ngôn ngữ
chung cho mọi hệthống thông tin địa lý hiện đại, được PostGIS triển khai đầy đủ:


- **Point** : cặp tọa độ ( _x, y_ ) biểu diễn một vịtrí (ví dụ: tọa độgiao hàng).


- **LineString** : dãy các điểm liên tiếp tạo thành đường (ví dụ: đường phố).


20


_3.6._ _HÌNH HỌC KHÔNG GIAN VÀ POSTGIS_


- **Polygon** : vùng kín được giới hạn bởi một hoặc nhiều LineString khép kín, có thểcó các "lỗ" bên
trong (ví dụ: ranh giới phường).


- **MultiPolygon** : tập hợp các Polygon độc lập (ví dụ: ranh giới một tỉnh có đảo).


- **GeometryCollection** : tập hợp hỗn hợp nhiều kiểu hình học.


Trong VNAI, ranh giới đơn vịhành chính được lưu dưới dạng MultiPolygon trong bảng `mat.area_polygon`,
cho phép biểu diễn chính xác các đơn vịhành chính có nhiều phần tách rời (đảo, vùng tách).

### **3.6.2 Hệtọa độđịa lý và hệtọa độphẳng**


Một điểm thiết yếu khi xửlý dữliệu không gian là phân biệt hai loại HệTham chiếu Tọa độ(Coordinate
Reference System — CRS):


- **Hệtọa độđịa lý (Geographic CRS)** : đơn vịđo là độvĩ/kinh (degree). Phổbiến nhất là WGS84
(EPSG:4326), được sửdụng bởi GPS và hầu hết các API bản đồ. Tuy nhiên, WGS84 không phù hợp
đểđo khoảng cách trực tiếp do bềmặt Trái Đất cong và một độkinh tuyến tại xích đạo dài hơn nhiều
so với tại cực.


- **Hệtọa độphẳng (Projected CRS)** : đơn vịđo là mét, sửdụng các phép chiếu (projection) đểbiểu
diễn bềmặt cong lên mặt phẳng. Tại Việt Nam, hệphổbiến là VN-2000 (EPSG:3405 đến 3409 tùy
múi chiếu) và UTM Zone 48N (EPSG:32648).


Trong các phép toán liên quan đến đo khoảng cách hoặc tính buffer theo đơn vịmét (ví dụ:
mởrộng polygon thêm 50 mét), bắt buộc phải chuyển đổi từWGS84 sang một hệphẳng metric
trước khi tính toán, sau đó chuyển ngược lại đểlưu trữ. PostGIS hỗtrợđiều này thông qua hàm
`ST_Transform(geom,` `srid)` .

### **3.6.3 Phép toán không gian PostGIS**


PostGIS cung cấp hàng trăm hàm thao tác không gian. Bảng 3.4 liệt kê các phép toán cốt lõi được sử
dụng trong VNAI.


Bảng 3.4: Các phép toán không gian PostGIS sửdụng trong VNAI


**Hàm** **Ý nghĩa**


`ST_Contains(A,` `B)` TrảvềTRUE nếu hình học A bao trùm hoàn toàn hình học B
`ST_Within(A,` `B)` TrảvềTRUE nếu A nằm trong B (đối ngẫu của ST_Contains)
`ST_Intersects(A,` TrảvềTRUE nếu A và B có ít nhất một điểm chung

```
 B)
```

`ST_Distance(A,` `B)` Khoảng cách ngắn nhất giữa A và B (theo đơn vịcủa CRS)
`ST_Buffer(A,` `r)` Tạo polygon là vùng đệm bán kính _r_ quanh A
`ST_Union(A,` `B)` Hợp hình học của A và B
`ST_ConcaveHull(A,` Bao lồi lõm với tham số“target percent” _t_

```
 t)
```

`ST_Transform(A,` Chuyển A sang hệtọa độmới có mã SRID

```
 srid)

```

21


_3.6._ _HÌNH HỌC KHÔNG GIAN VÀ POSTGIS_

### **3.6.4 Thuật toán Point-in-Polygon: Ray Casting**


Bài toán Point-in-Polygon (PIP) là nền tảng cho việc xác định một tọa độ(lat, lng) thuộc vềđơn vị
hành chính nào. Thuật toán cổđiển và phổbiến nhất là Ray Casting (thuật toán phóng tia) [35]: từđiểm
cần kiểm tra _P_, vẽmột tia kéo dài vô hạn vềmột hướng tùy ý (thường là chiều dương trục _x_ ), đếm số
lần tia đó cắt biên của polygon. Nếu sốlần cắt là sốlẻ, _P_ nằm trong polygon; nếu chẵn, _P_ nằm ngoài.
Thuật toán có độphức tạp _O_ ( _n_ ) với _n_ là sốđỉnh của polygon. Trong PostGIS, thuật toán này được
tối ưu hóa thông qua chỉmục không gian R-tree (GiST index) cho phép truy vấn nhanh ngay cảtrên
hàng nghìn polygon: PostGIS trước tiên dùng bounding box đểloại bỏcác polygon không thểchứa
điểm, sau đó chỉáp dụng Ray Casting trên các ứng viên còn lại. Truy vấn xác định đơn vịhành chính
chứa một tọa độtrong VNAI có dạng:

```
SELECT ward_id FROM mat.area_polygon

WHERE ST_Contains(geom,

           ST_SetSRID(ST_MakePoint(lng, lat), 4326));

```

Hình 3.5: Minh họa thuật toán Ray Casting cho bài toán Point-in-Polygon.

### **3.6.5 Ba chiến lược hiệu chỉnh polygon**


Trong thực tiễn vận hành, có nhiều trường hợp tọa độgiao nhận thực tếkhông nằm trong polygon hành
chính được lưu trữ, do bốn nguyên nhân chính: (i) sai sốGPS từthiết bịdi động (thường 5–15m), (ii)
polygon trong cơ sởdữliệu lỗi thời so với thực tế, (iii) ranh giới địa lý thực tếkhác ranh giới pháp lý,
và (iv) các điểm giao thông phức tạp tại ranh giới tiếp giáp. Đểgiải quyết, VNAI đềxuất ba chiến lược
hiệu chỉnh polygon, mỗi chiến lược phù hợp với một dạng sai lệch khác nhau.


**Chiến lược 1: Buffer-Union.** Khi điểm ngoại vi _p_ nằm sát biên polygon _P_ với độlệch nhỏ, hệthống
tạo một vùng đệm bán kính _r_ quanh _p_ rồi hợp với _P_ :


_P_ _[′]_ = _P_ _∪_ _B_ ( _p, r_ ) _,_ _B_ ( _p, r_ ) = _{x ∈_ R [2] : _∥x −_ _p∥≤_ _r}_ (3.13)


Cách tiếp cận này an toàn vềmặt cấu trúc nhưng có rủi ro xâm phạm vùng lân cận khi _r_ quá lớn, do đó
cần kiểm tra ràng buộc topology với các polygon kề.


**Chiến lược 2: Concave Hull (Alpha Shape).** Khi tích lũy đủmột đám mây điểm _P_ = _{p_ 1 _, p_ 2 _, . . ., pk}_
(ví dụ: tập các điểm giao nhận thành công trong một phường), hệthống tái dựng biên polygon từ _P_
bằng thuật toán Alpha Shape [36]. Khác với bao lồi (Convex Hull) chỉcho ra đa giác lồi, Alpha Shape
cho phép biên có tính chất lõm (concave), bám sát hơn phân bốthực tếcủa các điểm. Tham số _α_ kiểm
soát độchi tiết: _α →∞_ cho ra Convex Hull, _α →_ 0 cho biên rất chi tiết với nhiều ngóc ngách.


22


_3.7._ _MÔ HÌNH ACS — ĐIỂM TIN CẬY ĐỊA CHỈ_


**Chiến lược 3: Edge Injection.** Khi chỉcó một (hoặc rất ít) điểm bất thường mà không muốn thay
đổi lớn cấu trúc polygon, hệthống áp dụng phẫu thuật vi mô: tìm cạnh ( _vi, vi_ +1) của polygon gần _p_
nhất, sau đó chèn _p_ vào danh sách đỉnh đểtạo cạnh mới ( _vi, p, vi_ +1). Đây là chiến lược ít xâm lấn nhất,
phù hợp khi cần điều chỉnh nhỏmà giữnguyên tổng thểpolygon.
Hình 3.6 minh hoạtrực quan ba chiến lược; Bảng 3.5 tổng hợp vềđiều kiện áp dụng và mức độ
thay đổi cấu trúc.


Hình 3.6: Ba chiến lược hiệu chỉnh polygon: Buffer-Union, Concave Hull, Edge Injection.


Bảng 3.5: So sánh ba chiến lược hiệu chỉnh polygon


**Chiến lược** **Điều kiện áp dụng** **Rủi ro chính** **Mức xâm**
**lấn**


Buffer-Union Điểm sát biên, sai sốnhỏ( _<_ 50m) Xâm phạm polygon kề Trung bình
Concave Hull Đủmật độđiểm ( _≥_ 30 điểm/khu Cần chất lượng dữliệu cao Cao
vực)

Edge Injection Một vài điểm bất thường, cần giữ Tạo polygon “răng cưa” Thấp
cấu trúc

## **3.7 Mô hình ACS — Điểm tin cậy địa chỉ**

### **3.7.1 Bài toán ra quyết định trong chuẩn hóa địa chỉ**


Trong nghiệp vụlogistics và thương mại điện tử, kết quảchuẩn hóa địa chỉkhông chỉphục vụmục
đích lưu trữmà trực tiếp dẫn đến các hành động vận hành: tựđộng phân tuyến giao hàng, yêu cầu
khách hàng xác nhận lại, hay từchối đơn hàng. Vì vậy, bên cạnh kết quảchuẩn hóa thuần túy, hệthống
cần cung cấp một độtin cậy định lượng đểdẫn đường ra quyết định.


23


_3.7._ _MÔ HÌNH ACS — ĐIỂM TIN CẬY ĐỊA CHỈ_


Bài toán này được hình thức hóa thành HệHỗtrợRa Quyết định (Decision Support System —
DSS) với không gian quyết định mởrộng cho bối cảnh dữliệu lưỡng thời:


_A_ = _{a_ 1 _, a_ 2 _, a_ 3 _, a_ 4 _}_ = _{_ Auto-Accept _,_ Auto-Convert _,_ Suggest _,_ Reject _}_ (3.14)


Trong đó hành động Auto-Convert là điểm khác biệt cốt lõi của VNAI so với các hệthống truyền thống,
cho phép tựđộng ánh xạđịa chỉtiền cải cách (Pre-2025) sang định danh hậu cải cách (Post-2025) khi
độtin cậy đủcao.

### **3.7.2 Mô hình tổng trọng số(WSM)**


Đểtích hợp nhiều tín hiệu chất lượng khác nhau thành một điểm sốduy nhất, VNAI sửdụng Mô hình
Tổng Trọng số(Weighted Sum Model — WSM) thuộc họĐa Tiêu chí Ra Quyết định (Multi-Criteria
Decision Making — MCDM) [37, 38, 10]. WSM được lựa chọn nhờba ưu điểm phù hợp với bối cảnh
DSS:


- **Tính minh bạch (Transparency)** : mỗi thành phần đóng góp vào điểm cuối cùng có thểtruy vết,
đáp ứng yêu cầu giải thích quyết định (Decision Explanation).


- **Tính đơn giản tính toán** : chi phí tính toán _O_ ( _n_ ) với _n_ là sốtiêu chí, phù hợp với yêu cầu thời gian
thực.


- **Khảnăng tinh chỉnh trọng số** : cho phép điều chỉnh động dựa trên ngữcảnh nghiệp vụhoặc qua
phản hồi người dùng.

### **3.7.3 Công thức ACS với bốn thành phần**


Điểm tin cậy địa chỉ(Address Confidence Score — ACS) cho ứng viên _ai_ trước truy vấn _q_ được định
nghĩa:


ACS( _ai_ _| q_ ) = _α · S_ text( _q, ai_ ) + _β · S_ sem( _q, ai_ ) + _γ · V_ hier( _ai_ ) + _δ · V_ temporal( _ai_ ) (3.15)


với ràng buộc _α_ + _β_ + _γ_ + _δ_ = 1 và _α, β, γ, δ_ _≥_ 0. Các thành phần được giải nghĩa như sau:


- _S_ text( _q, ai_ ) _∈_ [0 _,_ 1]: điểm khớp văn bản, lấy từTypesense BM25 score đã chuẩn hóa min-max trên
tập ứng viên.


- _S_ sem( _q, ai_ ) _∈_ [0 _,_ 1]: độtương đồng cosine giữa vector embedding của truy vấn và ứng viên (Mục 3.4).


- _V_ hier( _ai_ ) _∈{_ 0 _,_ 1 _}_ : chỉsốkiểm tra tính hợp lệphân cấp — liệu Phường có thuộc Quận, Quận có thuộc
Tỉnh trong cơ sởtri thức `mat` hay không.


- _V_ temporal( _ai_ ) _∈_ [0 _,_ 1]: trọng sốthời gian, ưu tiên các phiên bản hành chính hậu cải cách ( `is_current`
`=` `TRUE` ) nhưng không loại bỏphiên bản cũ; cụthể _V_ temporal = 1 nếu là phiên bản hiện hành, 0 _._ 7
nếu là phiên bản cũ vẫn nằm trong cửa sổchuyển tiếp.


So với các phương pháp baseline chỉdùng tích hợp tuyến tính giữa độkhớp văn bản và ngữnghĩa,
công thức ACS mởrộng có hai đóng góp cốt lõi: (i) đưa kiểm tra phân cấp _V_ hier thành thành phần cứng
đểchống các lỗi mâu thuẫn cấu trúc mà mô hình ngôn ngữcó thểbỏqua; (ii) đưa thời gian trởthành
chiều quyết định bậc nhất qua _V_ temporal, đồng bộvới mô hình SCD Type 2 ởtầng dữliệu.


24


_3.7._ _MÔ HÌNH ACS — ĐIỂM TIN CẬY ĐỊA CHỈ_

### **3.7.4 Bảng quyết định bốn trạng thái**


Dựa trên giá trịACS, hệthống thực hiện ánh xạvềmột trong bốn hành động trong _A_, theo bảng quyết
định tại Bảng 3.6. Ngưỡng _θ_ high = 0 _._ 85 và _θ_ low = 0 _._ 50 được hiệu chuẩn từphân tích chi phí–lợi ích
trong nghiệp vụlogistics, sao cho cân bằng giữa tỷlệchấp nhận sai (False Positive — gây hoàn hàng)
và tỷlệtừchối sai (False Negative — gây phiền khách hàng).


Bảng 3.6: Bảng quyết định theo điểm ACS


**Khoảng ACS** **Hành động** **Phản hồi cho người dùng / hệthống**


ACS _≥_ 0 _._ 85 + Auto-Accept “Địa chỉchính xác hoàn toàn.”
_V_ temporal = 1

ACS _≥_ 0 _._ 85 + Auto-Convert “Đã cập nhật sang đơn vịhành chính mới 2025.”
_V_ temporal _<_ 1

0 _._ 50 _≤_ ACS _<_ 0 _._ 85 Suggest “Có phải bạn muốn tìm ...?”
ACS _<_ 0 _._ 50 Reject / Human “Không tìm thấy địa chỉhợp lệ. Vui lòng nhập lại hoặc chuyển
Review nhân viên xác minh.”

### **3.7.5 Đánh giá hiệu chuẩn: Expected Calibration Error**


Một mô hình DSS được coi là well-calibrated khi điểm tin cậy mô hình dựbáo phù hợp với xác suất
đúng quan sát được trong thực tế— nghĩa là, trong tất cảcác trường hợp mô hình dựbáo độtin cậy
0.9, khoảng 90% thực sựđúng. Đểđo lường hiệu chuẩn, đềtài sửdụng chỉsốSai sốHiệu chuẩn Kỳ
vọng (Expected Calibration Error — ECE) [39].
Quy trình tính toán: chia dải điểm ACS thành _M_ khoảng giá trịbằng nhau (binning), với mỗi
khoảng _Bm_ tính độchính xác thực nghiệm acc( _Bm_ ) và độtin cậy trung bình conf( _Bm_ ). ECE là trung
bình trọng sốcủa độlệch tuyệt đối:



ECE =



_M_



_m_ =1



_|Bm|_

_n_



��acc( _Bm_ ) _−_ conf( _Bm_ )�� (3.16)



Trong đó _n_ = [�] _m_ _[|][B][m][|]_ [ là tổng sốmẫu. Giá trịECE thấp (dưới 0.05) cho thấy mô hình hiệu chuẩn tốt]

và có thểtin cậy điểm sốđầu ra đểtựđộng ra quyết định, đây là yêu cầu thiết yếu cho DSS hoạt động ở
chếđộAuto-Accept và Auto-Convert. Toàn bộluồng ra quyết định từtruy vấn đầu vào tới một trong
bốn hành động cuối cùng được tóm lược tại Hình 3.7.


Hình 3.7: Sơ đồluồng ra quyết định dựa trên Điểm tin cậy địa chỉ(ACS) với bốn trạng thái.


25


_3.8._ _TÓM TẮT CHƯƠNG_

## **3.8 Tóm tắt chương**


Chương này đã thiết lập sáu cụm nền tảng lý thuyết liên kết chặt chẽvới các bài toán cốt lõi của VNAI.
Kiến trúc Transformer (3.2) làm nền cho mọi thành phần học sâu trong khung giải pháp; PhoBERT
(3.3) cụthểhóa Transformer cho bài toán nhận diện thực thểtên tiếng Việt với sơ đồnhãn BIO và
lớp CRF cho dựđoán có cấu trúc; mGTE (3.4) cùng cơ chếLate Interaction giải quyết nghịch lý độ
mịn trong truy xuất ngữnghĩa, hỗtrợbởi tìm kiếm láng giềng gần xấp xỉvới FAISS/HNSW; mạng
Siamese (3.5) cùng các hàm mất mát Contrastive và Triplet là khung huấn luyện đểtinh chỉnh mGTE
cho domain địa chỉViệt Nam; PostGIS (3.6) cung cấp các phép toán không gian cốt lõi cùng ba chiến
lược hiệu chỉnh polygon dựa trên dữliệu giao nhận thực tế; cuối cùng, mô hình ACS (3.7) tích hợp các
tín hiệu trên thành một điểm tin cậy duy nhất, dẫn đường tầng ra quyết định bốn trạng thái với cơ chế
đánh giá hiệu chuẩn ECE.
Các nền tảng này sẽđược vận dụng trong Chương 4 đểxây dựng kiến trúc hệthống VNAI, mô tả
chi tiết pipeline xửlý đa nguồn, thiết kếmodule huấn luyện NER, kiến trúc retrieval đa tầng và logic
suy luận của tầng LLM cho các trường hợp địa chỉphức tạp.


26


# **Chương 4** **Phân tích yêu cầu và thiết kếkhung giải pháp**

Chương 3 đã thiết lập nền tảng lý thuyết vềkiến trúc Transformer, các mô hình PhoBERT và mGTE,
mạng Siamese, các thuật toán hình học không gian trong PostGIS và mô hình Điểm tin cậy địa chỉ.
Chương này vận dụng các nền tảng đó đểcụthểhóa khung giải pháp **VN Address Intelligence** (VNAI)
trên hai phương diện: phân tích yêu cầu hệthống và thiết kếchi tiết bốn module chức năng. Trọng tâm
của chương là pipeline AI toàn diện, bao gồm thu nạp dữliệu đa nguồn, huấn luyện mô hình NER,
kiến trúc retrieval đa tầng và logic suy luận của tầng LLM trong việc xửlý các biến động hành chính
phức tạp.

## **4.1 Phân tích yêu cầu hệthống**

### **4.1.1 Yêu cầu nghiệp vụ**


Khung giải pháp VNAI được đặt trong bối cảnh chuyển đổi hành chính 2025 với mục tiêu phục vụ
đồng thời các nhóm tác vụnghiệp vụlogistics, thương mại điện tửvà quản lý hành chính công. Phân
tích các kịch bản vận hành thực tếcho phép xác định sáu yêu cầu nghiệp vụ(Business Requirements

- BR) cốt lõi.


- **BR1 — Đồng bộhành chính.** Hệthống phải chủđộng cập nhật danh mục đơn vịhành chính từ
nguồn Chính phủ(NSO — General Statistics Office) mà không cần can thiệp thủcông, đảm bảo dữ
liệu hành chính trong kho luôn đồng bộvới văn bản pháp lý hiện hành.


- **BR2 — Chuẩn hóa địa chỉthô.** Hệthống tiếp nhận đầu vào là chuỗi địa chỉtựdo (freetext), trảvề
cấu trúc chuẩn hóa kèm mã định danh đơn vịhành chính ba cấp.


- **BR3 — Quản lý lịch sửhành chính.** Hệthống cho phép tra cứu trạng thái của một đơn vịhành
chính tại bất kỳthời điểm nào trong lịch sử, hỗtrợánh xạđịa chỉtiền cải cách sang định danh hậu
cải cách.


- **BR4 — Xác định không gian.** Với đầu vào là tọa độ(latitude, longitude), hệthống xác định chính
xác đơn vịhành chính chứa điểm đó, đặc biệt tại các vùng ranh giới tiếp giáp.


- **BR5 — Làm giàu dữliệu.** Hệthống tựđộng bổsung tọa độ, ranh giới đa giác, tên điểm quan tâm
(Point of Interest — POI) từcác nguồn mở(OpenStreetMap, Google Maps) vào hồsơ địa chỉ.


27


_4.2._ _KIẾN TRÚC TỔNG THỂVNAI_


- **BR6 — Benchmark liên tục.** Hệthống cung cấp nền tảng so sánh hiệu năng giữa các mô hình AI
theo thời gian, hỗtrợra quyết định lựa chọn mô hình triển khai.

### **4.1.2 Yêu cầu phi chức năng**


Bốn nhóm yêu cầu phi chức năng (Non-Functional Requirements — NFR) định hình các ràng buộc kỹ
thuật của khung giải pháp. Thứnhất, vềhiệu năng, độtrễtrung bình cho một yêu cầu chuẩn hóa đơn lẻ
phải dưới 200ms, độtrễởphân vị95 (P95) dưới 500ms, và lưu lượng xửlý đạt ít nhất 20 địa chỉtrên
giây ởchếđộbatch. Thứhai, vềkhảnăng mởrộng, kiến trúc phải tuân theo mô hình microservices cho
phép mởrộng theo chiều ngang (horizontal scaling) khi tải tăng. Thứba, vềtính chính xác, mục tiêu
chỉsốF1 trên tập kiểm thử10.000 mẫu đa dạng đạt ít nhất 85%. Thứtư, vềtính sẵn sàng, hệthống
đồng bộhành chính hoạt động theo lịch định kỳ(cron) hoặc trigger sựkiện khi có thay đổi từnguồn
pháp lý.
Ngoài bốn nhóm trên, khung giải pháp ưu tiên ba ràng buộc kỹthuật chiến lược: triển khai _self-_
_hosted_ với toàn bộthành phần mã nguồn mởđểloại trừphụthuộc vào dịch vụthương mại bên thứba;
đảm bảo khảnăng truy vết nguồn gốc (provenance) cho mọi bản ghi địa chỉthông qua các cột audit; và
duy trì cơ chếtái lập (reproducibility) cho mọi thực nghiệm khoa học.

### **4.1.3 Phân tích luồng dữliệu**


Hệthống vận hành theo năm luồng dữliệu chính, tổng hợp tại Bảng 4.1. Năm luồng này liên kết với
nhau qua kho dữliệu trung tâm PostgreSQL nhưng được thiết kếđộc lập vềmặt khởi tạo và lịch chạy,
cho phép vận hành mỗi luồng riêng biệt mà không ảnh hưởng các luồng còn lại.


Bảng 4.1: Năm luồng dữliệu chính của khung giải pháp VNAI


**Luồng** **Tên** **Mô tả**


F1 Đồng bộhành chính Government API _→_ ETL _→_ PostgreSQL schema mat
F2 Chuẩn hóa địa chỉ Raw Address _→_ Queue prq _→_ AI Pipeline _→_ Structured Output
F3 Xác định không gian Coordinates _→_ PostGIS `ST_Contains` _→_ Admin Unit
F4 Làm giàu dữliệu Standardized Address _→_ OSM/Google _→_ Enriched Address
F5 Benchmarking Test Set _→_ AI Models _→_ Metrics _→_ schema ath

## **4.2 Kiến trúc tổng thểVNAI**

### **4.2.1 Triết lý thiết kế**


Bốn nguyên tắc thiết kếcốt lõi định hướng toàn bộkiến trúc VNAI. _Tách biệt mối quan tâm (Separation_
_of Concerns)_ - bốn module nghiệp vụ(thu thập dữliệu, chuẩn hóa AI, xác thực không gian, làm giàu
dữliệu) được hiện thực thành các thành phần độc lập, giao tiếp qua hợp đồng dữliệu (data contract)
rõ ràng thông qua các schema PostgreSQL chuyên biệt. _Kho tri thức làm trung tâm (Knowledge Base_
_First)_ - cơ sởdữliệu hành chính chuẩn trong schema mat được xem là Nguồn sựthật duy nhất (Single
Source of Truth); mọi mô hình AI tra cứu Knowledge Base thay vì sinh ( _hallucinate_ ) địa danh, qua đó
loại trừrủi ro tạo ra các định danh không tồn tại.


28


_4.2._ _KIẾN TRÚC TỔNG THỂVNAI_


_Nhận thức thời gian (Temporal Awareness)_  - mọi thực thểhành chính đều mang thông tin thời
gian theo mô hình Slowly Changing Dimension (SCD) Type 2, cho phép truy vết các phiên bản hành
chính cũ và mới song song. _Truy xuất lai (Hybrid Retrieval)_ - hệthống kết hợp tìm kiếm từvựng
(Typesense BM25) với tìm kiếm ngữnghĩa (mGTE/Siamese embedding) và Late Interaction đểcân
bằng giữa tốc độvà độchính xác.

### **4.2.2 Công nghệ(Technology Stack)**


Khung giải pháp được hiện thực trên Python 3.11+, với các thành phần phần mềm được tổchức thành
sáu lớp như tóm lược tại Bảng 4.2. Việc lựa chọn các thành phần này dựa trên ba tiêu chí: mã nguồn
mởđểphù hợp chiến lược tựchủhạtầng; hỗtrợtốt cho tiếng Việt; và khảnăng tích hợp với hệsinh
thái học sâu PyTorch + Hugging Face.


Bảng 4.2: Chồng công nghệphân lớp của khung giải pháp VNAI


**Lớp** **Thành phần**


Lõi và truy cập dữ SQLAlchemy 2+, psycopg2-binary, python-dotenv, click, tqdm, PyYAML, psutil
liệu

Dịch vụweb FastAPI [40], Uvicorn, Gunicorn, httpx, PyJWT, passlib (bcrypt)
Học máy và NLP PyTorch 2.4.1+, Hugging Face Transformers [41], sentence-transformers, seqeval,
scikit-learn 1.3.2, bitsandbytes, accelerate
Tiếng Việt pyvi, vnaddress, VnCoreNLP (qua PhoBERT pipeline)
Địa lý overpy (Overpass), Folium [42], Shapely [43], pyproj, alphashape, PostGIS [44]
Hạtầng vận hành Redis (cache), python-logstash-async (ELK), Docker Compose

### **4.2.3 Kiến trúc phân lớp và cấu trúc mã nguồn**


Khung giải pháp tuân theo kiến trúc phân lớp gồm bốn lớp: Lớp Trình bày (Presentation), Lớp Nghiệp
vụ(Business / Service), Lớp AI (AI Hub) và Lớp Dữliệu (Data). Hình 4.1 thểhiện trực quan kiến trúc
này. Tầng API chỉđiều phối: nhận yêu cầu HTTP, gọi dịch vụnghiệp vụhoặc module suy luận, trả
vềDTO (Data Transfer Object) hoặc JSON. Logic nghiệp vụtái sửdụng dài hạn nằm trong dịch vụ
domain hoặc gói AI. Script vận hành, migration và thực nghiệm được tổchức riêng và gọi qua trình
thông dịch Python thay vì _import_ như thư viện nội bộcủa server, qua đó loại bỏphụthuộc giữa kịch
bản nghiên cứu và server production.


29


_4.2._ _KIẾN TRÚC TỔNG THỂVNAI_


Hình 4.1: Kiến trúc phân lớp bốn tầng của khung giải pháp VNAI.


Hình 4.2: Cấu trúc thư mục logic kho mã nguồn VNAI.


Bốn khối chức năng chính lần lượt là: gói `api` đăng ký tập route REST, gắn middleware CORS khi
cần và nạp mô hình AI trong luồng nền (background thread) đểgiảm độtrễkhởi động; gói `services`
chứa các dịch vụđồng bộNSO với logic SCD Type 2, thu thập OSM, làm giàu dữliệu, xác thực
người dùng và đồng bộground truth từTypesense; gói `ai` chứa các lớp mô hình `AddressNER`,
`SiameseMGTE`, `LLMQwen3`, script huấn luyện, pipeline production kết hợp retrieval–NER–LLM–
ACS, cùng EpochDetector và PreLabeler; gói `geometry` hiện thực ba chiến lược hiệu chỉnh polygon
(Mục 4.6.4).


30


_4.3._ _THIẾT KẾCƠ SỞDỮLIỆU ĐA SCHEMA_

## **4.3 Thiết kếcơ sởdữliệu đa schema**

### **4.3.1 Quy ước chung và mô hình SCD Type 2**


Cơ sởdữliệu được phân tách thành bốn schema logic chuyên biệt: mat (Master Administrative Table)
cho dữliệu đơn vịhành chính và polygon ranh giới; osm cho thực thểOpenStreetMap đã xửlý; ath
(Analytics & Training Hub) cho huấn luyện, benchmark, nhật ký đồng bộ; và prq (Processing Queue)
cho hàng đợi xửlý địa chỉvà ground truth. Việc tách schema giúp phân quyền vận hành theo miền dữ
liệu, sao lưu chọn lọc và giảm rủi ro thay đổi lẫn nhau giữa dữliệu nghiệp vụvà artifact thực nghiệm.
Hình 4.3 trình bày lược đồER (Entity-Relationship) đầy đủcho bốn schema.


Hình 4.3: Lược đồER đầy đủcủa bốn schema cơ sởdữliệu VNAI.


Mọi bảng master tuân thủtập quy ước cột thống nhất nhằm hiện thực mô hình SCD Type 2 [8].
Cụthể, mỗi bảng có một khóa tựsinh ( `row_id` ) đóng vai trò khóa chính vật lý, một mã định danh
nghiệp vụ( `province_id`, `district_id`, `ward_id` ) mang ý nghĩa trong miền nghiệp vụ, cột
`admin_version` phân biệt phiên bản hành chính (1: tiền cải cách, 2: hậu cải cách 01/07/2025),
cột `old_id` lưu định danh legacy đểjoin ngược hệthống cũ, cặp `valid_from` / `valid_to` cùng
`predecessor_id` và `version_id` hỗtrợtruy vết lịch sử, cờ `is_active` chỉbản ghi đại diện
hiện tại cho API, và `is_deleted` đánh dấu xóa mềm.


31


_4.3._ _THIẾT KẾCƠ SỞDỮLIỆU ĐA SCHEMA_

### **4.3.2 Schema mat — Đơn vịhành chính và ranh giới**


Schema mat chứa sáu bảng cốt lõi tổchức theo phân cấp ba tầng tỉnh–huyện–xã. Bảng 4.3 tóm lược
chức năng các bảng. Trong đó, bảng `mat.area_polygon` đóng vai trò đặc biệt: lưu ranh giới đơn
vịhành chính dưới dạng GeoJSON, có chỉmục trên cặp ( `unit_level`, `unit_id` ), là đầu vào cho
mọi truy vấn PostGIS như `ST_Contains`, `ST_Distance` .


Bảng 4.3: Các bảng cốt lõi trong schema mat


**Bảng** **Vai trò**


`mat.province` Quản lý đơn vịcấp tỉnh kèm SCD, các cột bao hộp tọa độcực, khối GSO mởrộng
(population, area_km2, decision_number, decision_date)
`mat.district` Quản lý đơn vịcấp huyện kèm SCD; sau cải cách 2025 các bản ghi cấp huyện được
đánh `valid_to` nhưng vẫn lưu cho truy vấn lịch sử
`mat.ward` Quản lý đơn vịcấp xã/phường kèm SCD và mã GSO mởrộng
`mat.ward_mapping` Ánh xạchuyển đổi cấp xã: cặp `ward_id_old/new`, khoảng hiệu lực,

```
           relationship_type
```

`mat.unit_edge` Đồthịcó hướng quan hệđơn vị: `from_unit_id`, `to_unit_id`,
`relationship_type` _∈_ {MERGES_INTO, SPLIT_FROM, RENAMES_TO,
BOUNDARY_ADJUSTED}
`mat.area_polygon` Ranh giới geojson cho cảba cấp, kèm nguồn ( `source` _∈_ {OSM, GSO,
MANUAL}) và `admin_version`


Đặc biệt, bảng `mat.unit_edge` hiện thực hóa khái niệm _đồthịbiến động đơn vịhành chính_ :
khi một xã sáp nhập vào xã khác, hệthống tạo cạnh `MERGES_INTO` ; khi một huyện được tách, các
cạnh `SPLIT_FROM` được tạo từhuyện gốc sang các đơn vịmới. Cấu trúc đồthịnày không chỉphục
vụtruy vết lịch sửmà còn được sửdụng trực tiếp trong thuật toán Edge Injection ởMục 4.6.4.

### **4.3.3 Schema osm — Dữliệu OpenStreetMap**


Schema osm chứa bốn bảng: `streets`, `buildings`, `pois` với cấu trúc tương tự( `id`, `name`, `type`,
`province_id`, `province_name`, `created_at` ), và bảng `raw_entities` lưu nguyên trạng
dữliệu OSM dưới dạng JSON với cột `osm_type` _∈_ {node, way, relation} và `tags` JSON chứa toàn
bộcặp khóa–giá trịOSM gốc. Cách lưu trữnày cho phép hệthống vừa truy vấn nhanh trên các bảng
đã chuẩn hóa, vừa giữnguyên dữliệu thô đểtruy hồi khi cần làm giàu lại theo các trường mới.

### **4.3.4 Schema ath — Hub AI, benchmark và nhật ký**


Schema ath là trung tâm của các hoạt động học máy và đảm bảo tái lập thực nghiệm. Bảng 4.4 liệt kê
các bảng chính. Đáng chú ý, cặp `benchmark_dataset` (chứa các tập kiểm thửD1–D5 theo phân
loại nhiễu) và `benchmark_run_result` (lưu mọi dựđoán của từng mô hình trên từng mẫu, kèm
UUID nhóm run) hình thành nền tảng cho khung đánh giá khoa học chuẩn (Chương 5).


32


_4.3._ _THIẾT KẾCƠ SỞDỮLIỆU ĐA SCHEMA_


Bảng 4.4: Các bảng cốt lõi trong schema ath


**Bảng** **Vai trò**


`training_datasets` Tập huấn luyện NER với `ner_tags_json` (BIO), cờ `is_synthetic`,
mức nhiễu
`training_history` Lịch sửhuấn luyện: phiên bản, F1, loss, sốmẫu
`benchmark_model_baselines` Mô hình baseline với F1, throughput, chi phí/1M mẫu, `google_match`
`benchmark_dataset` Mẫu kiểm thử(D1–D5) kèm `noise_type`, `admin_version`, expected
IDs
`benchmark_run_result` Kết quảdựđoán: `run_id` (UUID), dựđoán ID, ACS, decision, epoch,
latency
`sync_log` Nhật ký đồng bộvới `sync_source` _∈_ {NSO_API, N8N_WORKFLOW,
MANUAL}
`typesense_ground_truth_sync_run` Run đồng bộground truth từTypesense
`email_verifications` Mã xác thực email cho luồng đăng ký

### **4.3.5 Schema prq — Hàng đợi xửlý và ground truth**


Schema prq đóng vai trò hai mặt: vừa là hàng đợi xửlý cho pipeline AI sản xuất, vừa là kho ground truth
phục vụhuấn luyện và đánh giá. Bảng `prq.address_cleansing_queue` là trung tâm: chứa địa
chỉthô ( `raw_address` ), trạng thái xửlý (PENDING, PROCESSING, DONE, FAILED), kết quảphân
tích từcảPhoBERT ( `phobert_parsed_components` JSON, `phobert_confidence_score` )
và mGTE ( `mgte_parsed_components`, `mgte_confidence_score` ), cờchọn mô hình
( `selected_ai_model` ), chuỗi chuẩn hóa cuối cùng ( `address_standardized` ), tọa độlàm
giàu (lat/lng), và các trường lineage tiền cải cách ( `old_province_id`, `old_district_id`,
`old_ward_id` ).
Bảng `prq.ground_truth` lưu cặp địa chỉchuẩn lưỡng thời: `address` (định danh hậu cải cách,
bắt buộc) và `old_address` (định danh tiền cải cách), kèm cặp ba cấp tỉnh–huyện–xã cho cảhai
phiên bản. Mỗi bản ghi có cờ `is_validated`, `data_quality_score`, và liên kết tới run đồng
bộTypesense thông qua `last_sync_run_id` . Đây là kho dữliệu nền tảng cho khung thực nghiệm
SUPA-Bench (Mục 4.9).

### **4.3.6 Bảng SUPA-Bench cho thực nghiệm**


Hai bảng `prq.supa_benchmark_run` (metadata mỗi lần chạy benchmark) và
`prq.supa_benchmark_specimen` (mẫu benchmark cụthể) được định nghĩa qua migration SQL
riêng, không map đầy đủtrong ORM chính nhằm giảm cặp ràng buộc giữa ứng dụng và bảng thực
nghiệm. Các trường quan trọng gồm `rng_seed` (hạt giống ngẫu nhiên), `noise_profile_id` (mã
profile nhiễu), `git_commit` (commit hash tại thời điểm extract), `ref_address_v2`
/ `ref_address_v1` (snapshot tham chiếu hậu/tiền cải cách), `noisy_raw_address` (chuỗi đã
nhiễu), `pred_standardized` (dựđoán của mô hình ngoài).
**Bất biến thực nghiệm (Experimental Invariant):** pipeline SUPA-Bench tuyệt đối không thực hiện
thao tác `INSERT` / `UPDATE` / `DELETE` trên `prq.ground_truth` ; mọi truy vấn chỉlà `SELECT` .
Bất biến này đảm bảo tính độc lập giữa pipeline thực nghiệm và kho dữliệu tham chiếu.


33


_4.4._ _MODULE 1: ĐỒNG BỘDANH MỤC HÀNH CHÍNH (GOV-SYNC)_

## **4.4 Module 1: Đồng bộdanh mục hành chính (Gov-Sync)**

### **4.4.1 Luồng đồng bộtừnguồn NSO**


Module Gov-Sync hiện thực luồng đồng bộtựđộng từAPI danh mục hành chính của Tổng cục Thống
kê (NSO). Client Python gọi tuần tựba endpoint: danh sách tỉnh, danh sách huyện theo tỉnh, danh
sách xã theo huyện; mỗi phản hồi được chuẩn hóa thông qua các hàm làm sạch tên (loại bỏký tựđặc
biệt, chuẩn hóa Unicode NFC) và dịch loại đơn vịsang tiếng Anh khi cần ( `type_name_en` ). Sau khi
nhận được dữliệu mới, hàm `upsert_scd` so checksum trên tập trường nghiệp vụ; khi phát hiện thay
đổi có ý nghĩa, bản ghi active hiện tại được đóng ( `valid_to` `=` `NOW()`, `is_active` `=` `FALSE` )
và bản ghi mới được chèn với mã đơn vịnghiệp vụbắt buộc trong payload.
REST API expose bốn endpoint cốt lõi cho module này:


   - `POST` `/api/sync/nso` kích hoạt đồng bộtoàn bộ;


   - `POST` `/api/sync/nso/province` đồng bộtheo một mã tỉnh;


   - `GET` `/api/sync/nso/logs` đọc log đồng bộ;


   - `DELETE` `/api/sync/nso/logs` xóa log.


   - Bộba endpoint `GET` `/api/nso/provinces`, `/districts`, `/wards` cung cấp chếđộchỉ
đọc dữliệu trực tiếp từNSO mà không ghi DB, phục vụkiểm tra trước khi đồng bộchính thức.

### **4.4.2 SCD Type 2 và đồthịquan hệunit_edge**


Mỗi thay đổi hành chính được ghi vào `ath.sync_log` với `run_id` nhóm, cho phép truy vết toàn bộ
lịch sửbiến động theo từng lần chạy. Đồng thời, đồthị `mat.unit_edge` bổsung cạnh có kiểu quan
hệvà ngày hiệu lực đểphục vụba mục đích nghiên cứu chiến lược: (i) phân tích cấu trúc tách/nhập
đơn vịhành chính theo thời gian; (ii) hỗtrợthuật toán Edge Injection trong hiệu chỉnh polygon; (iii)
cung cấp dữliệu cho EpochDetector trong việc phân loại địa chỉtiền/hậu cải cách.
API tra cứu lịch sửcó dạng `GET/api/admin-unit/{level}/{unit_id}/history?`
`at={timestamp}`, trảvềtrạng thái đơn vịtại một thời điểm cụthể. Truy vấn này được hiện thực
qua điều kiện SQL trên cặp `valid_from` _≤_ at _≤_ `valid_to` .

### **4.4.3 Vai trò orchestration n8n**


Trường `sync_source` trong `ath.sync_log` phân biệt ba nguồn kích hoạt: `NSO_API` (gọi trực
tiếp qua REST), `N8N_WORKFLOW` (kích hoạt qua nền tảng tựđộng hóa n8n [45]), `MANUAL` (thao tác
thủcông của quản trịviên). Hàm `upsert_scd` mặc định ghi nhận nguồn `N8N_WORKFLOW` nhằm
đồng nhất với kịch bản orchestration bên ngoài: trigger theo lịch (cron), gọi dịch vụChính phủhoặc
crawler, sau đó gọi lớp Python hoặc SQL đã chuẩn hóa của VNAI.
Việc tách rời pipeline orchestration sang n8n mang lại ba lợi ích: thứnhất, dễdàng thay đổi lịch
trình mà không cần redeploy server; thứhai, hỗtrợretry và exponential backoff khi API Chính phủ
timeout; thứba, cho phép tích hợp các nguồn dữliệu bổsung (Nghịquyết Chính phủ, Cổng Dịch vụ
công) vào cùng luồng đồng bộ. Hình 4.4 minh hoạluồng Gov-Sync hoàn chỉnh từtrigger cron đến cập
nhật cơ sởdữliệu.


34


_4.5._ _MODULE 2: PIPELINE AI CHUẨN HÓA ĐỊA CHỈ_


Hình 4.4: Luồng đồng bộGov-Sync sáu bước với nền tảng n8n.

### **4.4.4 Chuyển đổi địa chỉtheo kỷnguyên hành chính**


Endpoint `POST` `/api/migrate-address` là một thành phần phụtrợnghiên cứu cho phép gửi một
chuỗi địa chỉtựnhiên và nhận kết quảchuyển đổi. Pipeline xửlý gồm ba bước: (1) `EpochDetector`
phân loại chuỗi thành PRE_2025, POST_2025 hoặc AMBIGUOUS dựa trên các từkhóa đặc trưng
(sựxuất hiện của tên đơn vịcũ, từ"Quận" trong khu vực đã chuyển sang "Phường"); (2) nếu
phân loại là PRE_2025, áp dụng bảng `ward_mapping` đểtìm đơn vịhậu cải cách tương ứng;
(3) `ACSCalculator` tính điểm tin cậy ACS với `admin_version` phù hợp.

## **4.5 Module 2: Pipeline AI chuẩn hóa địa chỉ**

### **4.5.1 Lớp tiền xửlý và PreLabeler**


Lớp tiền xửlý thực hiện bốn nhóm thao tác trên chuỗi đầu vào trước khi đưa vào mô hình học sâu. Thứ
nhất, chuẩn hóa Unicode vềdạng NFC đểxửlý các trường hợp tổhợp dấu phụ(NFD) phổbiến trên dữ
liệu từiOS/macOS. Thứhai, chuẩn hóa từviết tắt theo từđiển 200+ entry phổbiến phân biệt ngữcảnh
Bắc/Nam (ví dụ: "Q." _→_ "Quận", "P." _→_ "Phường", "HN" _→_ "Hà Nội", "TpHCM" _→_ "Thành phốHồ
Chí Minh"). Thứba, loại bỏthông tin giao hàng (delivery note): các cụm như "gọi trước khi giao", "rẽ


35


_4.5._ _MODULE 2: PIPELINE AI CHUẨN HÓA ĐỊA CHỈ_


phải 150m", "gặp bảo vệ" được tách sang trường `delivery_instruction` riêng. Thứtư, chuẩn
hóa cấu trúc sốnhà/ngõ/ngách: chuỗi "90/12/5" được phân rã thành {street: 90, alley: 12, house: 5}.
**PreLabeler** là engine rule-based kết hợp luật heuristic và từvựng tiền tốhành chính đểsinh nhãn
hoặc cấu trúc trung gian. Engine này phục vụba mục đích: (i) gán nhãn (annotation) tựđộng cho dữ
liệu huấn luyện ban đầu đểgiảm chi phí lao động thủcông; (ii) regression testing cho các pattern địa
chỉđã biết; (iii) fallback khi tải mô hình deep learning thất bại — endpoint phân tích địa chỉtựđộng
chuyển sang PreLabeler đểtrảvềphản hồi tối thiểu thay vì lỗi 500. Module `address_cleaner` bổ
trợlàm sạch chuỗi đầu vào với các trường hợp cận lề(edge case) phát sinh từthực tiễn vận hành.

### **4.5.2 Huấn luyện PhoBERT NER**


Script huấn luyện NER thực hiện sáu bước theo trình tự. Bước 1: đọc dữliệu export từcông cụgán
nhãn Label Studio [46] hoặc tập Hugging Face công khai. Bước 2: ánh xạnhãn BIO từđịnh dạng
chuẩn của Label Studio sang lược đồnhãn dựán — bảy loại thực thể{STR (street), WDS (ward), DST
(district), PRO (province), HNB (house number), ALY (alley), POI} với hai nhãn B-/I- cho mỗi loại và
một nhãn O, tổng cộng 15 nhãn. Bước 3: tokenize bằng tokenizer PhoBERT (FastBPE) với chiến lược
_label propagation_ cho subword: nhãn của từgốc được nhân rộng cho mọi subword con. Bước 4: huấn
luyện `AutoModelForTokenClassification` của Hugging Face Transformers với Trainer; siêu
tham sốmặc định gồm learning rate 2e-5, batch size 32, 10 epoch, early stopping theo F1 trên tập
dev. Bước 5: đánh giá bằng `seqeval` với ba chỉsốprecision, recall, F1 theo chuỗi (sequence-level).
Bước 6: ghi lịch sửhuấn luyện vào bảng `ath.training_history` và lưu checkpoint vào thư mục
`models/` .
Khung huấn luyện hỗtrợtăng cường dữliệu (data augmentation) bằng bốn kỹthuật: thêm biến thể
viết tắt theo từđiển 200+ entry; biến đổi không dấu (loại bỏngẫu nhiên dấu thanh và phụâm trên 20%
mẫu); hoán đổi thứtựthành phần (ví dụđảo "Phường X, Quận Y" thành "Quận Y, Phường X"); và
thêm nhiễu từvựng nhẹ(đánh máy sai, lặp ký tự).

### **4.5.3 Retrieval đa tầng với Siamese mGTE**


Lớp `SiameseMGTE` hiện thực kiến trúc Bi-encoder trên nền checkpoint `Alibaba-NLP/gte-`
`multilingual-base` [6]. Quy trình ba bước: thứnhất, mã hóa toàn bộcorpus địa chỉchuẩn (gộp
từ `mat.ward`, `mat.district`, `mat.province` ) thành chỉmục vector kèm metadata (mã GSO,
tọa độcentroid, admin_version) và lưu thành file FAISS. Thứhai, tại thời điểm truy vấn, mã hóa chuỗi
đầu vào (đã chuẩn hóa qua tiền xửlý) thành vector và truy vấn top-k láng giềng gần nhất theo cosine
similarity. Thứba, lọc kết quảtheo `admin_version` mong muốn và áp dụng kiểm tra phân cấp
(Phường _∈_ Quận _∈_ Tỉnh) đểloại bỏcác tổhợp không hợp lệ.
Khi corpus có quy mô lớn (hàng trăm nghìn đơn vị), hệthống chuyển sang IVF (Inverted File
Index) với 1024 cluster và `nprobe` `=` `16` đểduy trì độtrễdưới 50ms ngay cảkhi truy vấn liên tục.
Trên API nghiên cứu parser, cấu hình YAML cho phép trỏtới checkpoint Siamese đã huấn luyện cục
bộthay vì checkpoint mặc định; điều này phục vụkịch bản fine-tune trên domain địa chỉViệt Nam
như mô tảởMục 3.5.

### **4.5.4 Tinh chỉnh cấu trúc bằng LLM Qwen**


Lớp `LLMQwen3` bọc tokenizer và mô hình causal LM họQwen [47], được kích hoạt khi điểm tin cậy
ACS sau giai đoạn retrieval và NER thấp hơn ngưỡng (mặc định 0.7). Cấu hình thực nghiệm hiện tại


36


_4.5._ _MODULE 2: PIPELINE AI CHUẨN HÓA ĐỊA CHỈ_


sửdụng checkpoint `Qwen/Qwen2.5-1.5B-Instruct` với lượng tửhóa 4-bit qua BitsAndBytes

[48], temperature 0 cho giải mã tham lam (Greedy Decoding) ổn định. Lựa chọn mô hình 1.5B (thay vì
các biến thểlớn hơn 7B/14B) phản ánh sựcân bằng thực tiễn giữa độchính xác và yêu cầu hạtầng:
1.5B có thểchạy trên một GPU tiêu dùng (8GB VRAM) sau quantization, đảm bảo tính khảthi triển
khai cho doanh nghiệp Việt Nam quy mô vừa.
Prompt được thiết kếtheo nguyên tắc _Structured Prompting_ với hai thành phần: (i) phần hệthống
mô tảvai trò “trợlý chuẩn hóa địa chỉViệt Nam” và liệt kê các quy tắc nghiệp vụ(chuẩn 3 cấp
Tỉnh–Huyện–Xã, định dạng sốnhà); (ii) phần người dùng cung cấp chuỗi đầu vào kèm danh sách top-k
ứng viên từgiai đoạn retrieval (Mục 4.5.3). Đầu ra yêu cầu định dạng JSON với năm trường: `street`,
`ward`, `district`, `province`, `full_address` . Áp dụng kỹthuật Constrained Decoding (hoặc
parsing nghiêm ngặt) đảm bảo đầu ra luôn hợp lệvềcú pháp JSON.

### **4.5.5 Pipeline production HYBRID_V1**


Pipeline production tích hợp tất cảthành phần trên thành luồng xửlý tám bước, được kích hoạt
trên các bản ghi của `prq.address_cleansing_queue` ởtrạng thái PENDING hoặc chưa có
`address_standardized` . Bảng 4.5 mô tảchi tiết tám bước.


Bảng 4.5: Tám bước của pipeline production HYBRID_V1


**#** **Bước** **Mô tả**


1 Trích thực thể `AddressNER` (PhoBERT+BiLSTM-CRF) bóc tách sốnhà, đường, ngõ,
hành chính
2 Chuẩn hóa tiền tố Áp dụng map viết tắt cho tên đường (nếu có)
3 Dựng ngữcảnh Ghép sốnhà, đường, ngõ, các trường hành chính có sẵn trên bản ghi
4 Retrieve top-k `SiameseMGTE` trảvềk ứng viên kèm metadata (tọa độ, GSO ID)
5 LLM refinement `LLMQwen3` sinh JSON chuẩn hóa từdanh sách ứng viên
6 Detect epoch `EpochDetector` phân loại PRE_2025 / POST_2025 / AMBIGUOUS
7 Tính ACS Điểm ngữnghĩa _S_ sem = max(LLM_score _,_ Retrieval_score)
8 Ghi kết quả Cập nhật `address_standardized`, ACS,
`processing_method=’HYBRID_V1’` ; back-fill lat/lng từmetadata
top-1 nếu thiếu


Việc lấy max giữa điểm LLM và điểm retrieval tại bước 7 phản ánh nguyên tắc _lạc quan thận trọng_
_(cautious optimism)_ : nếu một trong hai mô hình đưa ra điểm cao đáng tin cậy thì hệthống tin theo,
nhưng cờ `selected_ai_model` ghi lại nguồn quyết định đểhỗtrợphân tích lỗi và truy vết vềsau.
Hình 4.5 thểhiện trực quan toàn bộpipeline tám bước.


37


_4.5._ _MODULE 2: PIPELINE AI CHUẨN HÓA ĐỊA CHỈ_


Hình 4.5: Pipeline production HYBRID_V1 tám bước.

### **4.5.6 So sánh đa mô hình trên API nghiên cứu**


Endpoint `POST` `/api/parser/analyze` cho phép client gửi một chuỗi địa chỉvà nhận vềkết
quảphân tích từbốn mô hình chạy song song: `AddressNER`, `PhoBERTSiamese` (backbone
`vinai/phobert-base` ), `SiameseMGTE`, và `LLMQwen3` . Sau đó, nếu import thành công, ACS


38


_4.6._ _MODULE 3: GEOSPATIAL VÀ HIỆU CHỈNH POLYGON_


và epoch được tính trên cơ sởđiểm sốtốt nhất trong các đầu ra có trường score. Endpoint `GET`
`/api/parser/status` và `POST` `/api/parser/reload` hỗtrợvận hành theo dõi lỗi nạp
GPU/CPU và nạp lại checkpoint mà không cần restart toàn bộserver.

## **4.6 Module 3: Geospatial và hiệu chỉnh polygon**

### **4.6.1 Thu thập OpenStreetMap**


CLI và REST API hỗtrợkích hoạt job thu thập OSM qua client `overpy` gọi Overpass API [49] công
khai. Job nhận hai tham số: phạm vi địa lý (giới hạn theo `province_id` ) và mục tiêu tổng sốthực
thể. Trạng thái job được giữtrong biến tiến trình toàn cục có khóa mutex đểđảm bảo không có hai
job chạy đồng thời trên cùng phạm vi. Sau khi tải về, dữliệu thô được phân tích cú pháp và phân loại
vào ba bảng `osm.streets`, `osm.buildings`, `osm.pois` dựa trên các tag OSM gốc; bản ghi thô
được lưu vào `osm.raw_entities` . Endpoint `GET` `/api/osm/summary` và `/preview` phục
vụdashboard quan sát tiến trình thu thập.

### **4.6.2 Lưu trữpolygon và trực quan hóa ranh giới**


Bảng `mat.area_polygon` lưu ranh giới đơn vịhành chính dưới dạng GeoJSON. API `GET/api/`
`boundary/map` nhận tham số `level` và `unit_id`, tạo bản đồFolium [42] hiển thịpolygon trên
nền OpenStreetMap, trảvềđường dẫn file HTML có thểnhúng vào dashboard hoặc gửi tới người dùng
cuối. Trường hợp polygon không tồn tại (đơn vịhành chính mới được tạo mà chưa có dữliệu OSM), hệ
thống trảvềbản đồrỗng với cảnh báo thay vì lỗi cứng, đảm bảo trải nghiệm người dùng nhất quán.
Đểhỗtrợphân tích trực quan, công cụ `tools/boundary_visualization` cho phép xuất
bản đồHTML đa lớp gom polygon theo nhiều cấp hành chính, dùng cho debug và viết case study.

### **4.6.3 API spatial: Point-in-Polygon và Mismatch Report**


Endpoint `POST` `/api/spatial/subdivide` nhận danh sách điểm (lat, lng) cùng `level` _∈_
{province, district, ward} và trảvềphân nhóm đơn vịhành chính tương ứng. Logic xửlý hai tầng: nếu
PostGIS extension đã được cài đặt, hệthống thử `ST_Contains` giữa điểm và geometry chuyển từ
GeoJSON; nếu không có match (điểm nằm sát ngoài biên do sai sốGPS), fallback sang `ST_Distance`
tới centroid đểchọn đơn vịgần nhất. Phản hồi gồm bốn nhóm thống kê: sốđiểm khớp polygon, số
điểm khớp theo nearest, sốđiểm không khớp, và cờ `postgis_available` .
Endpoint `GET` `/api/spatial/mismatch-report` thực hiện so khớp giữa
`prq.address_cleansing_queue` (chứa lat/lng đã làm giàu) và polygon cấp ward: tìm các bản
ghi có tọa độnằm trong polygon của ward khác với `ward_id` đã khai báo. Truy vấn có thểlọc theo
`province_id` và giới hạn sốlượng kết quả. Kết quảnày là đầu vào cốt lõi cho quy trình hiệu chỉnh
polygon mô tảởmục tiếp theo.

### **4.6.4 Edge Injection cho hiệu chỉnh GPS gần biên**


Hàm `edge_inject_lookup` hiện thực chiến lược thứba trong ba chiến lược hiệu chỉnh polygon
đã trình bày ởChương 3, Mục 3.6.5. Cụthể, khi một tọa độGPS được phát hiện nằm sát biên giữa
hai đơn vịhành chính kềnhau, hàm thực hiện bốn bước: thứnhất, truy vấn `mat.unit_edge` đểlấy


39


_4.7._ _MODULE 4: LÀM GIÀU DỮLIỆU ĐA NGUỒN_


danh sách các đơn vịláng giềng (qua các cạnh kiểu `BOUNDARY_ADJUSTED` ); thứhai, tính khoảng
cách Haversine từđiểm cần kiểm tra tới centroid của từng đơn vịláng giềng (hoặc qua polygon nếu
bảng không lưu centroid trực tiếp cho cấp đó); thứba, lọc các đơn vịcó khoảng cách dưới ngưỡng bán
kính (mặc định 200m, cấu hình được); thứtư, chọn đơn vịcó khoảng cách nhỏnhất và đềxuất gán
điểm cho đơn vịđó.
Mục đích của Edge Injection là giảm lỗi gán đơn vịkhi điểm GPS rơi sát ranh giới do sai sốGPS
(thường 5–15m trên thiết bịdi động) hoặc nhiễu địa lý. Kết quảcủa hàm này được tích hợp vào pipeline
HYBRID_V1 (Mục 4.5.5) như một bước hậu xửlý cho các bản ghi có `phobert_confidence_score`
cao nhưng đối soát không gian thất bại.
Module `geometry/buffer_union` và `geometry/concave_hull` hiện thực hai chiến
lược còn lại (Buffer-Union và Concave Hull/Alpha Shape) dựa trên thư viện Shapely [43] và alphashape,
cho phép mởrộng polygon hoặc tái dựng biên từđám mây điểm giao nhận thực tế.

## **4.7 Module 4: Làm giàu dữliệu đa nguồn**

### **4.7.1 Chiến lược thu thập đa nguồn và Waterfall Enrichment**


Module làm giàu tuân theo kiến trúc Waterfall Enrichment đã đềxuất trong dàn ý nghiên cứu: ba lớp
xếp tầng theo thứtựưu tiên chi phí thấp _→_ chi phí cao. Lớp 1 (Internal Cache Redis): chi phí 0, hit
rate kỳvọng 20–40% với các địa chỉphổbiến đã xửlý trước đó. Lớp 2 (OSM + VietMap): chi phí
thấp, độtrễthấp do server đặt tại Việt Nam, độphủước tính 40–50% các địa chỉ. Lớp 3 (Google Maps
Geocoding API): chỉkích hoạt khi confidence thấp, mục tiêu giới hạn dưới 10–20% tổng sốrequest để
kiểm soát chi phí. Hình 4.6 minh hoạkiến trúc thác nước và tỷlệphân bổgiữa các lớp.


40


_4.7._ _MODULE 4: LÀM GIÀU DỮLIỆU ĐA NGUỒN_


Hình 4.6: Kiến trúc Waterfall Enrichment ba lớp Cache–OSM/VietMap–Google.


Cụthể, bốn nguồn dữliệu chính trong module enrichment được tổng hợp tại Bảng 4.6.


Bảng 4.6: Bốn nguồn dữliệu trong module làm giàu


**Nguồn** **Loại dữliệu** **Vai trò trong VNAI**


NSO (Government) Danh mục hành chính Cập nhật mat, mã GSO, ranh giới hành chính
chính thức

OpenStreetMap Đường, tòa nhà, POI Làm giàu osm; bounding box theo đơn vị
Google Maps Tọa độchính xác, POI Fallback khi OSM thiếu dữliệu
thương mại

VietMap Migration address, Xửlý vùng nông thôn (đềxuất tích hợp tương lai)
POI Việt


41


_4.8._ _TẦNG API REST VÀ GIAO DIỆN NGƯỜI DÙNG_

### **4.7.2 Bộnhớđệm Redis và xóa cache có chọn lọc**


Lớp 1 của Waterfall Enrichment được hiện thực bằng Redis [50]. Cache có hai chếđộhoạt động. Chế
độ _lookup cache_ : lưu kết quảcác truy vấn enrichment theo khóa hash của địa chỉchuẩn hóa, TTL
7 ngày. Chếđộ _admin unit cache_ : lưu toàn bộdanh mục đơn vịhành chính active đểgiảm truy vấn
DB cho các endpoint `/provinces`, `/districts`, `/wards` ; cache này được tựđộng invalidate khi
sync NSO ghi nhận thay đổi.
Hai endpoint quản trịđược cung cấp: `GET` `/api/cache/health` kiểm tra sức khỏe kết nối
Redis; `DELETE` `/api/cache/admin` xóa cache đơn vịhành chính (yêu cầu xác thực, dùng sau
khi sync NSO thủcông).

### **4.7.3 Provenance và quản lý nguồn gốc dữliệu**


Mọi bản ghi địa chỉvà đơn vịhành chính trong VNAI đều mang thông tin provenance dưới dạng cột
`source`, `source_system` hoặc tương đương: `mat.area_polygon.source` _∈_ {OSM, GSO,
MANUAL}; `prq.ground_truth.source_system` _∈_ {TYPESENSE, GOOGLE, MANUAL}.
Cách thiết kếnày cho phép truy vết nguồn gốc cho mọi quyết định của hệthống, hỗtrợphân tích lỗi và
audit dữliệu trong trường hợp có khiếu nại.
Đặc biệt, mọi run đồng bộground truth từTypesense được ghi vào
`ath.typesense_ground_truth_sync_run` với các trường `started_at`, `finished_at`,
`records_scanned`, `records_upserted` . Liên kết khóa ngoại từ
`prq.ground_truth.last_sync_run_id` đến bảng run này tạo thành dấu vết kiểm tra (audit
trail) đầy đủ.

## **4.8 Tầng API REST và giao diện người dùng**

### **4.8.1 Kiến trúc client SPA**


Giao diện người dùng được hiện thực dưới dạng Single Page Application (SPA) nhẹvới HTML/CSS/JavaScript thuần (không sửdụng framework như React/Vue). Quyết định này phản ánh hai ưu tiên: thứ
nhất, giảm độphức tạp triển khai cho doanh nghiệp quy mô vừa (không cần build pipeline Node.js);
thứhai, đảm bảo khảnăng tích hợp dễdàng với các backoffice hiện hữu của doanh nghiệp.
Logic client gồm bốn lớp. Thứnhất, lớp xác thực: kiểm tra JSON Web Token (JWT) trong
`sessionStorage` ; nếu thiếu và không ởtrang đăng nhập thì chuyển hướng tựđộng. Thứhai,
lớp fetch: hàm `apiFetch` thửnhiều base URL API theo thứtự(localhost cho dev, origin hiện
tại cho production, cấu hình người dùng cho deployment đặc biệt). Thứba, lớp điều hướng: shell
điều hướng theo thuộc tính HTML `data-page`, mỗi trang con tương ứng một màn chức năng.
Thứtư, lớp giao diện: cho phép đổi theme ( `dark`, `light`, `oled-black` ) và chếđộchuyển động
( `prefers-reduced-motion` ).
Các chức năng được tổchức thành ba nhóm: nhóm vận hành ( _overview_, _parser_, _batch_, _explorer_,
_lookup_ ); nhóm nghiên cứu ( _training_, _experiments_, _evidence_, _label-registry_, _prelabeler-cases_, _label-_
_studio_ ); nhóm dữliệu ( _admin-units_, _nso-sync_, _osm-enrichment_, _boundary-visualization_, _documenta-_
_tion_ ).


42


_4.8._ _TẦNG API REST VÀ GIAO DIỆN NGƯỜI DÙNG_

### **4.8.2 Phân nhóm endpoint REST**


Toàn bộAPI được tổchức thành sáu nhóm endpoint theo tiền tốURL. Nhóm chính `/api/*` chứa
các endpoint cốt lõi; router phiên bản `/api/v1/*` mirror cùng tập endpoint nhằm hỗtrợphiên bản
hóa API trong tương lai. Bốn nhóm con thuộc các module chuyên biệt: `/api/spatial/*` cho
geospatial, `/api/boundary/*` cho ranh giới, `/api/repo-docs/*` cho đọc tài liệu kho mã (chỉ
trong thư mục `docs/`, loại trừnhánh private), và các endpoint xác thực không gắn tiền tốmodule.
Bảng 4.7 liệt kê các endpoint cốt lõi theo nhóm chức năng nghiệp vụ.


Bảng 4.7: Các endpoint REST cốt lõi theo nhóm chức năng


**Nhóm** **Endpoint (method và đường dẫn sau /api)**


Xác thực `POST` `/login`, `/register/send-code`, `/register`, `/logout`
Tra cứu HC `GET` `/provinces`, `/districts/{province_id}`,
`/wards/{district_id}`, `/unit-details/{level}/{unit_id}`,

```
        /lookup/mapping
```

Đồng bộNSO `POST` `/sync/nso`, `/sync/nso/province` ; `GET` `/sync/nso/logs` ; `GET`

```
        /nso/{provinces|districts|wards}
```

AI Parser `GET` `/parser/status`, `/parser/sample` ; `POST` `/parser/reload`,
`/parser/analyze` ; `POST` `/migrate-address`
Hàng đợi `GET` `/queue/summary`, `/explorer/queue` ; `POST` `/batch/trigger` ; `GET`

```
        /batch/job
```

Huấn luyện `GET` `/training/history`, `/training/samples` ; `POST`

```
        /training/history
```

Benchmark `GET` `/benchmark/realtime`, `/benchmark/baselines`,
`/benchmark/job` ; `POST` `/benchmark/trigger`
OSM `GET` `/osm/{summary|preview|job}` ; `POST` `/osm/trigger`
Spatial `POST` `/api/spatial/subdivide` ; `GET`

```
        /api/spatial/{mismatch-report|postgis-status}
```

Boundary `GET` `/api/boundary/map`
Lịch sửHC `GET` `/admin-unit/{level}/{unit_id}/history` ; `/sync-logs`,

```
        /sync-logs/summary/{run_id}
```

PreLabeler `GET` `/prelabeler-cases`, `/random-predict` ; `POST`
`/prelabeler-cases`, `/run`, `/export-label-studio`
Cache `GET` `/cache/health` ; `DELETE` `/cache/admin`

### **4.8.3 Xác thực JWT và bảo mật**


Hệthống sửdụng JSON Web Token (JWT) cho xác thực phiên người dùng. Luồng đăng ký yêu
cầu xác thực email hai bước: `POST` `/register/send-code` gửi mã 6 chữsốtới email, lưu vào
`ath.email_verifications` với TTL 15 phút; `POST` `/register` hoàn tất với mã đã nhận. Mật
khẩu được hash bằng bcrypt qua thư viện `passlib` . Token JWT có thời hạn cấu hình được (mặc định
60 phút) và được kiểm tra trên các endpoint nghiệp vụthông qua dependency `get_current_user`
của FastAPI. Một sốendpoint trigger (batch, OSM, cache delete) yêu cầu xác thực đểngăn việc kích
hoạt trái phép từbên ngoài.


43


_4.9._ _KHUNG THỰC NGHIỆM SUPA-BENCH_

## **4.9 Khung thực nghiệm SUPA-Bench**

### **4.9.1 Định nghĩa và mục tiêu**


SUPA-Bench ( _Synthetic User-style Perturbation Address benchmark_ ) là khung đánh giá chuẩn hóa địa
chỉđược thiết kếchuyên biệt cho bối cảnh dữliệu lưỡng thời của Việt Nam. Khác với các benchmark
NER truyền thống vốn đo lường độchính xác trên dữliệu sạch đã gán nhãn, SUPA-Bench mô phỏng
cách người dùng thực tếgõ địa chỉvới nhiễu (perturbation) theo các pattern phổbiến, đồng thời cho
phép đánh giá Exact Match (EM) song song với cảhai phiên bản tham chiếu (hậu cải cách v2 và tiền
cải cách v1).
Mục tiêu cốt lõi của SUPA-Bench là cung cấp một khung tái lập (reproducible) cho mọi thực
nghiệm chuẩn hóa địa chỉtrong khung VNAI, đảm bảo các báo cáo khoa học có thểso sánh được giữa
các phiên bản mô hình, các checkpoint khác nhau, và các nghiên cứu kếthừa trong tương lai. Bất biến
nghiên cứu cốt lõi (đã nêu tại Mục 4.3.6) là pipeline SUPA-Bench chỉđọc `prq.ground_truth` mà
không thực hiện bất kỳthao tác ghi nào, đảm bảo tính độc lập giữa nguồn tham chiếu và quy trình
đánh giá.

### **4.9.2 Quy trình SUPA-Bench năm bước**


Bảng 4.8 mô tảnăm bước của quy trình SUPA-Bench, từchuẩn bịcơ sởdữliệu đến xuất báo cáo.
Hình 4.7 thểhiện trực quan luồng các lệnh CLI cùng các artifact đầu ra.


44


_4.9._ _KHUNG THỰC NGHIỆM SUPA-BENCH_


Hình 4.7: Workflow SUPA-Bench.


Bảng 4.8: Năm bước của quy trình SUPA-Bench


**#** **Lệnh con CLI** **Mô tả**


0 DDL chuẩn bị Tạo `prq.supa_benchmark_run` và `supa_benchmark_specimen`
qua migration SQL
1 `extract` Chọn cohort từground truth, sinh nhiễu deterministic theo seed, ghi specimen
2 `export-` Xuất CSV UTF-8 với cột `noisy_raw_address`, `ref_address_v1/v2`,
`specimens` cột trống `pred_standardized`
3 `import-preds` Đọc lại CSV sau khi pipeline ngoài chạy dựđoán; bắt buộc `–source-note`
4 `eval` Tổng hợp Exact Match v1% và v2%; chuẩn hóa NFC + gom whitespace trước so
khớp
5 `export-tex` Sinh `providecommand` cho RunId, cỡmẫu, EM%, seed, commit


**Profile nhiễu SUP-1.0.0.** Hàm sinh nhiễu deterministic theo `random.Random(seed)` áp bốn
loại perturbation phổbiến: (i) thêm tiền tốngẫu nhiên kiểu “Gần ”, “Đối diện ”, “Bên cạnh ” (mô
phỏng cách người dùng mô tảvịtrí tương đối); (ii) thêm hậu tốghi chú kiểu “(gặp bảo vệ)”, “- gọi
trước” (mô phỏng instruction giao hàng); (iii) thay “, ” bằng biến thểcó khoảng trắng thừa hoặc thiếu
( `",` `"`, `","` ); (iv) với xác suất nhỏ, gấp đôi khoảng trắng nội bộ. Tính chất deterministic của seed đảm
bảo mọi lần chạy với cùng seed sinh cùng tập specimen, là điều kiện cần cho khảnăng tái lập.


45


_4.10._ _TÓM TẮT CHƯƠNG_

### **4.9.3 Lệnh gộp workflow**


Lệnh `workflow` thực hiện chuỗi tựđộng: `extract` (trừkhi `–skip-extract` ) _→_
`export-specimens` _→_ `import-preds` (nếu có CSV dựđoán) _→_ `eval` _→_ `export-tex` .
Tham số `–n` mặc định là 10.000 mẫu; khi chỉcần cohort nhỏcho thửnghiệm cần truyền `–n` tường
minh. Cờ `–preds-demo-ref-v2` tạo file dựđoán _oracle_ bằng cách sao chép `ref_address_v2`
sang `pred_standardized`, chỉphục vụsmoke test đường ống mà không được dùng làm bằng
chứng mô hình; cờ `–source-note` bắt buộc khi có `–preds` thực tế.
Đầu ra `export-tex` sinh các macro `providecommand` cho RunId, cỡmẫu, tỉlệEM v1%/v2%,
seed, noise profile, commit; phần trăm được escape cho TeX ( `%` _→_ `\%` ); giá trịthiếu hiển thịdạng
“—”. Điều này cho phép chương Thực nghiệm (Chương 5) trực tiếp `\input` file macro mà không cần
copy/paste thủcông, qua đó đảm bảo sốliệu báo cáo đồng nhất với dữliệu thực sựđã đo.

### **4.9.4 Reproducibility và truy vết**


SUPA-Bench đóng gói bốn yếu tốcho mỗi lần chạy: (i) `rng_seed` ghi vào
`prq.supa_benchmark_run`, đảm bảo cohort tái sinh được; (ii) `git_commit` bắt được tại thời
điểm extract qua lệnh `git` `rev-parse` `HEAD` nếu khảdụng; (iii) `notes` cho metadata bổsung
(mô tảmục đích run); (iv) bắt buộc `–source-note` khi import dựđoán, ghi rõ checkpoint, GPU,
commit của pipeline đã chạy dựđoán. Bốn yếu tốnày cùng với dấu thời gian UTC ( `started_at`,
`finished_at` ) tạo nên dấu vết kiểm tra đầy đủcho mọi báo cáo khoa học dựa trên VNAI.

## **4.10 Tóm tắt chương**


Chương này đã trình bày khung giải pháp VNAI ởmức chi tiết thiết kế. Bắt đầu từsáu yêu cầu nghiệp
vụvà bốn nhóm yêu cầu phi chức năng (Mục 4.1), kiến trúc tổng thểđược tổchức thành bốn tầng với
chồng công nghệmã nguồn mở(Mục 4.2). Cơ sởdữliệu được phân tách thành bốn schema chuyên biệt
(mat, osm, ath, prq) với mô hình SCD Type 2 thống nhất (Mục 4.3).
Bốn module nghiệp vụhiện thực các bài toán cốt lõi: Module Gov-Sync (Mục 4.4) tựđộng hóa
đồng bộdanh mục hành chính từNSO và quản lý đồthịbiến động qua `mat.unit_edge` ; Module AI
Pipeline (Mục 4.5) tích hợp PhoBERT NER, mGTE retrieval và LLM Qwen vào pipeline HYBRID_V1
tám bước; Module Geospatial (Mục 4.6) cung cấp Point-in-Polygon, Mismatch Report và Edge Injection
cho hiệu chỉnh GPS gần biên; Module Enrichment (Mục 4.7) tuân theo kiến trúc Waterfall ba lớp
Cache–OSM/VietMap–Google nhằm tối ưu chi phí.
Tầng API REST (Mục 4.8) cung cấp bềmặt tích hợp thống nhất với hơn 60 endpoint phân nhóm
theo chức năng. Cuối cùng, khung thực nghiệm SUPA-Bench (Mục 4.9) thiết lập quy trình năm bước
có thểtái lập, là nền tảng cho mọi báo cáo định lượng ởChương 5.
Các thiết kếtrên đảm bảo ba đặc tính cốt lõi: _tính nhất quán dữliệu_ qua mô hình SCD và provenance
cột; _tính tái lập khoa học_ qua SUPA-Bench với seed, commit, source-note đóng gói cùng metric; và
_tính chủđộng hạtầng_ qua chuỗi công nghệmã nguồn mởself-hosted. Chương 5 sẽvận dụng khung
này đểthực hiện các kịch bản kiểm thửtrên năm tập dữliệu (D1–D5) và phân tích định lượng hiệu
năng của ba mô hình AI cùng tác động nghiệp vụtổng thể.


46


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


_5.4._ _KHUNG THỰC NGHIỆM SUPA-BENCH_


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


**Diễn giải.** Sốliệu trên _chỉchứng minh chuỗi vận hành_ của thực nghiệm phân tầng đa lần chạy:
cơ chếlấy mẫu theo quota D1–D4 hoạt động đúng, lệnh `replicate-stratified` sinh được năm
cohort độc lập, lệnh `aggregate-runs` `–persist-ath` ghi đúng vào
`ath.supa_stratified_eval_summary` . _Không_ thểkết luận pipeline AI đạt EM@v2 = 100 %
hay F1 thành phần = 100 % trên thực tế; những sốliệu trên là kết quảoracle, có giá trịvềmặt vận
hành chuỗi đánh giá chứkhông phải vềmặt năng lực mô hình. **Diễn giải.** Sốliệu trên _chỉchứng minh_
_chuỗi vận hành_ của thực nghiệm phân tầng đa lần chạy: cơ chếlấy mẫu theo quota D1–D4 hoạt động
đúng, lệnh `replicate-stratified` sinh được năm cohort độc lập, lệnh `aggregate-runs`
`–persist-ath` ghi đúng vào
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


53


_5.5._ _ĐÁNH GIÁ TRUY XUẤT NGỮNGHĨA_


Bảng 5.7: Kết quảthống kê K = 5 với cohort phân tầng _n_ = 2 _._ 000 (kịch bản oracle)


**Chỉsố** **Mean** **Std** **Min** **Max** **Ghi chú**


EM@v2 (%) 100,00 0,00 100,00 100,00 Oracle: `pred` = ref v2
EM@v1 (%) 16,14 0,44 15,55 16,65 `pred` v2 so khớp tuyệt đối chuỗi v1
F1 Đường (chuỗi, %) 100,00 0,00 100,00 100,00 Cùng điều kiện oracle
F1 Phường (%) 100,00 0,00 100,00 100,00 F1 Quận (%) 100,00 0,00 100,00 100,00 F1 Tỉnh/TP (%) 100,00 0,00 100,00 100,00 

15 _,_ 5 % đến 16 _,_ 7 % mà không có cơ chếphân biệt. Hình 5.3 thểhiện trực quan biên độdao động này.


Hình 5.3: Dao động EM@v1 trên năm lần chạy K = 5 độc lập với cohort phân tầng.

## **5.5 Đánh giá Truy xuất Ngữnghĩa**


**Trạng thái artifact.** Các chỉsốS-RET (R@k, MRR, top-1 string match) chưa có giá trịmặc định trong
kho mã — chỉxuất hiện sau khi chạy thực sựscript đánh giá. Hệthống đã chuẩn bịđầy đủhạtầng:
tập đo là cặp `(old_address,` `address)` từ `prq.ground_truth`, _corpus_ là tập `address`
đã khửtrùng lặp, truy vấn qua phương thức `SiameseMGTE.retrieve_top_k` với checkpoint
`Alibaba-NLP/gte-multilingual-base` .
**Quy trình thực hiện.** Script `scripts/experiments/eval_retrieval_mgte.py` (hoặc
tương đương qua `python` `-m` `app.ai.evaluate_retriever` ) hỗtrợba tham sốchính: `–k-list`
(ví dụ _{_ 1 _,_ 5 _,_ 10 _,_ 20 _}_ ), `–out-json` (đường dẫn artifact), và `–persist-db` (ghi một dòng vào bảng
`ath.retrieval_eval_run` ).
Điều kiện tiên quyết là migration `20260512_retrieval_eval_and_supa_metrics.sql`


54


_5.6._ _KỊCH BẢN ĐÁNH GIÁ END-TO-END TRÊN ĐỊA CHỈTHỰC TẾ_


đã được áp lên cơ sởdữliệu. Giao diện web tại mục _Lịch_ _sửthực_ _nghiệm_ đọc qua endpoint `GET`
`/api/experiments/retrieval-runs` đểliệt kê các lần chạy đã _persist_ .
**Phương pháp luận bổsung.** Khi so sánh hai _snapshot_ mô hình, cần giữcốđịnh bốn tham số:
`model_name`, giới hạn corpus `limit`, `top_k` và danh sách `k_list` ; đồng thời ghi `git_commit`
vào cảJSON và DB. Định nghĩa `recall@k` là trùng khớp chuỗi đầy đủvới tham chiếu vàng trong
top- _k_ ứng viên — một định nghĩa nghiêm ngặt phù hợp bài toán chuẩn hoá.

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


55


_5.8._ _TÁC ĐỘNG NGHIỆP VỤVÀ PHÂN TÍCH RỦI RO_

## **5.8 Tác động Nghiệp vụvà Phân tích Rủi ro**

### **5.8.1 Tác động tích cực trên căn cứđịnh lượng**


Trên cơ sởcác phép đo audit và NER đã trình bày, đềtài rút ra ba kết luận vềtác động nghiệp vụtích
cực.
_Thứnhất_, quy mô 437862 bản ghi trong hàng đợi tại một thời điểm đo cho thấy nhu cầu tựđộng
hoá là có thật và cấp thiết — nếu xửlý thủcông, công sức kiểm tra một bản ghi chỉmột phút cũng
vượt 7 _._ 000 giờ-người, một quy mô không khảthi.
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


56


_5.9._ _TỔNG KẾT CHƯƠNG_


quy kết sai lệch vềmô hình. _Thứba_, thực nghiệm phân tầng K = 5 với bảng tổng hợp _persist_ trong ath
thiết lập một chuẩn báo cáo có _provenance_ đầy đủ, sẵn sàng cho mọi vòng thực nghiệm trong tương lai.
Chương 6 đối chiếu các kết quảnày với mục tiêu nghiên cứu ban đầu, tổng hợp đóng góp khoa học,
ghi nhận các hạn chếvà đềxuất hướng phát triển ưu tiên đóng vòng làm giàu không gian tựđộng.


57


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


58


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


59


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


60


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


61


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


62


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


63


# **Tài liệu tham khảo**


[1] G. Chow, T. D. Heaver, and L. E. Henriksson, “Logistics performance: definition and
measurement,” _International Journal of Physical Distribution & Logistics Management_, vol. 24,
no. 1, pp. 17–28, 1994.


[2] Quốc hội, “Nghịquyết số202/2025/qh15 vềviệc sắp xếp đơn vịhành chính cấp tỉnh,” 2025,
[accessed: 2025. [Online]. Available: https://thuvienphapluat.vn/](https://thuvienphapluat.vn/)


[3] Tổng cục Thống kê Việt Nam, “Danh mục các đơn vịhành chính việt nam,” 2025, truy cập năm
[2025. [Online]. Available: https://danhmuchanhchinh.nso.gov.vn/](https://danhmuchanhchinh.nso.gov.vn/)


[4] [n8n GmbH, “n8n documentation – workflow automation,” https://docs.n8n.io/, 2024, accessed:](https://docs.n8n.io/)
2024.


[5] D. Q. Nguyen and A. T. Nguyen, “PhoBERT: Pre-trained language models for vietnamese,” in
_Findings of the Association for Computational Linguistics: EMNLP 2020_ . Association for
Computational Linguistics, 2020, pp. 1037–1042.


[6] X. Zhang, Z. Ma _et al._, “mgte: Generalized long-context text representation and reranking
models for multilingual text retrieval,” _arXiv preprint arXiv:2407.19669_, 2024.


[7] J. Santos, A. Rodrigues, and B. Martins, “Geo-semantic learning for address matching,” in
_Proceedings of the 26th ACM SIGSPATIAL International Conference on Advances in Geographic_
_Information Systems_ . ACM, 2018, pp. 299–308.


[8] R. Kimball and M. Ross, _The Data Warehouse Toolkit: The Definitive Guide to Dimensional_
_Modeling_, 3rd ed. Wiley, 2013.


[9] M. Bilmener and M. Toka, “Ontology-based address standardization and geocoding for smart
cities,” _Survey Review_, vol. 54, no. 386, pp. 398–408, 2022.


[10] E. K. Zavadskas, J. Antucheviciene, and P. Chatterjee, “Multiple-criteria decision-making
(MCDM) techniques for business processes information management,” _Information_, vol. 10,
no. 1, p. 4, 2019.


[11] C. D. Manning, P. Raghavan, and H. Sch¨utze, _Introduction to Information Retrieval_ .
Cambridge, UK: Cambridge University Press, 2008. [Online]. Available:
[https://nlp.stanford.edu/IR-book/](https://nlp.stanford.edu/IR-book/)


[12] H.-N. Cao and V.-T. Tran, “Deep neural network based learning to rank for address
standardization,” in _2021 RIVF International Conference on Computing and Communication_
_Technologies (RIVF)_ . IEEE, 2021, pp. 1–6.


64


_TÀI LIỆU THAM KHẢO_


[13] Ủy ban Thường vụQuốc hội, “Nghịquyết số35/2023/ubtvqh15 vềviệc sắp xếp đơn vịhành
chính cấp huyện, cấp xã giai đoạn 2023–2030,” 2023, accessed: 2023. [Online]. Available:
[https://vanban.chinhphu.vn/](https://vanban.chinhphu.vn/)


[14] Google Developers, “Google maps platform documentation - geocoding api,”
[https://developers.google.com/maps/documentation/geocoding/overview, 2025, truy cập ngày:](https://developers.google.com/maps/documentation/geocoding/overview)
20-12-2025.


[15] [Typesense, “Typesense guide and api reference,” https://typesense.org/docs/, 2024, accessed:](https://typesense.org/docs/)
2024.


[16] D. Marcoux _et al._, “Deepparse: A deep learning multinational address parser,” _arXiv preprint_
_arXiv:2006.16152_, 2020.


[17] Z. Li _et al._, “Geoagent: Bridging llms with geospatial tools for intelligent location services,”
_arXiv preprint arXiv:2407.06451_ [, 2024. [Online]. Available: https://arxiv.org/abs/2407.06451](https://arxiv.org/abs/2407.06451)


[18] Đặng Đức Tùng, “Ứng dụng mô hình crf và bi-lstm trong trích xuất thông tin địa chỉ,” Master’s
thesis, Đại học Bách Khoa Hà Nội, 2019.


[19] V. C. Kiên and cộng sự, “Nghiên cứu giải pháp công nghệvà ứng dụng mã địa chỉbưu chính kết
hợp bản đồsốphục vụphát triển kinh tế–xã hội,” BộThông tin và Truyền thông, Tech. Rep.,
2021, tiêu chuẩn ISO 19160; quy mô 23.4 triệu địa chỉ. [Online]. Available:
[https://www.vista.gov.vn/vi/news/ket-qua-nghien-cuu-trien-khai/](https://www.vista.gov.vn/vi/news/ket-qua-nghien-cuu-trien-khai/nghien-cuu-giai-phap-cong-nghe-va-ung-dung-ma-dia-chi-buu-chinh-ket-hop-ban-do-so-phuc-vu-phat-trien-kinh-te-xa-hoi-10489.html)
[nghien-cuu-giai-phap-cong-nghe-va-ung-dung-ma-dia-chi-buu-chinh-ket-hop-ban-do-so-phuc-vu-phat-trien](https://www.vista.gov.vn/vi/news/ket-qua-nghien-cuu-trien-khai/nghien-cuu-giai-phap-cong-nghe-va-ung-dung-ma-dia-chi-buu-chinh-ket-hop-ban-do-so-phuc-vu-phat-trien-kinh-te-xa-hoi-10489.html)
[html](https://www.vista.gov.vn/vi/news/ket-qua-nghien-cuu-trien-khai/nghien-cuu-giai-phap-cong-nghe-va-ung-dung-ma-dia-chi-buu-chinh-ket-hop-ban-do-so-phuc-vu-phat-trien-kinh-te-xa-hoi-10489.html)


[20] VLSP Campaign, “Vietnamese semantic parsing task (visemparse) overview,” in _Proceedings of_
_the 11th International Workshop on Vietnamese Language and Speech Processing (VLSP 2025)_ .
VLSP, 2025.


[21] S. Hochreiter and J. Schmidhuber, “Long short-term memory,” _Neural Computation_, vol. 9,
no. 8, pp. 1735–1780, 1997.


[22] A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and
I. Polosukhin, “Attention is all you need,” in _Advances in Neural Information Processing Systems_
_(NeurIPS)_, 2017, pp. 5998–6008.


[23] J. Devlin, M. W. Chang, K. Lee, and K. Toutanova, “BERT: Pre-training of deep bidirectional
transformers for language understanding,” in _Proceedings of the 2019 Conference of the North_
_American Chapter of the Association for Computational Linguistics: Human Language_
_Technologies (NAACL-HLT)_ . Association for Computational Linguistics, 2019, pp. 4171–4186.


[24] Y. Liu, M. Ott, N. Goyal, J. Du, M. Joshi, D. Chen, O. Levy, M. Lewis, L. Zettlemoyer, and
V. Stoyanov, “RoBERTa: A robustly optimized BERT pretraining approach,” _arXiv preprint_
_arXiv:1907.11692_, 2019.


[25] T. Vu, D. Q. Nguyen, D. Q. Nguyen, M. Dras, and M. Johnson, “VnCoreNLP: A Vietnamese
natural language processing toolkit,” in _Proceedings of the 2018 Conference of the North_
_American Chapter of the Association for Computational Linguistics: Demonstrations_, 2018, pp.
56–60.


65


_TÀI LIỆU THAM KHẢO_


[26] N. Reimers and I. Gurevych, “Sentence-BERT: Sentence embeddings using Siamese
BERT-networks,” in _Proceedings of the 2019 Conference on Empirical Methods in Natural_
_Language Processing (EMNLP-IJCNLP)_ . Association for Computational Linguistics, 2019, pp.
3982–3992.


[27] V. Karpukhin, B. O˘guz, S. Min, P. Lewis, L. Wu, S. Edunov, D. Chen, and W.-t. Yih, “Dense
passage retrieval for open-domain question answering,” in _Proceedings of the 2020 Conference_
_on Empirical Methods in Natural Language Processing (EMNLP)_, 2020, pp. 6769–6781.


[28] O. Khattab and M. Zaharia, “ColBERT: Efficient and effective passage search via contextualized
late interaction over BERT,” in _Proceedings of the 43rd International ACM SIGIR Conference on_
_Research and Development in Information Retrieval (SIGIR)_, 2020, pp. 39–48.


[29] J. Johnson, M. Douze, and H. Jégou, “Billion-scale similarity search with GPUs,” _arXiv preprint_
_arXiv:1702.08734_, 2017.


[30] Y. A. Malkov and D. A. Yashunin, “Efficient and robust approximate nearest neighbor search
using hierarchical navigable small world graphs,” _IEEE Transactions on Pattern Analysis and_
_Machine Intelligence_, vol. 42, no. 4, pp. 824–836, 2020.


[31] J. Bromley, I. Guyon, Y. LeCun, E. S¨ackinger, and R. Shah, “Signature verification using a
Siamese time delay neural network,” in _Advances in Neural Information Processing Systems_
_(NIPS)_, 1993, pp. 737–744.


[32] R. Hadsell, S. Chopra, and Y. LeCun, “Dimensionality reduction by learning an invariant
mapping,” in _Proceedings of the IEEE Computer Society Conference on Computer Vision and_
_Pattern Recognition (CVPR)_, 2006, pp. 1735–1742.


[33] F. Schroff, D. Kalenichenko, and J. Philbin, “FaceNet: A unified embedding for face recognition
and clustering,” in _Proceedings of the IEEE Conference on Computer Vision and Pattern_
_Recognition (CVPR)_, 2015, pp. 815–823.


[34] Open Geospatial Consortium, _OpenGIS Implementation Standard for Geographic Information —_
_Simple Feature Access_, Open Geospatial Consortium, 2011, version 1.2.1, OGC 06-103r4.


[35] M. I. Shamos and D. Hoey, “Geometric intersection problems,” _17th Annual Symposium on_
_Foundations of Computer Science (FOCS)_, pp. 208–215, 1976.


[36] H. Edelsbrunner, D. Kirkpatrick, and R. Seidel, “On the shape of a set of points in the plane,”
_IEEE Transactions on Information Theory_, vol. 29, no. 4, pp. 551–559, 1983.


[37] C. L. Hwang and K. Yoon, _Multiple Attribute Decision Making: Methods and Applications_ .
Springer-Verlag, 1981.


[38] T. L. Saaty, _The Analytic Hierarchy Process_ . McGraw-Hill, 1980.


[39] C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, “On calibration of modern neural networks,” in
_Proceedings of the 34th International Conference on Machine Learning (ICML)_, 2017, pp.
1321–1330.


66


_TÀI LIỆU THAM KHẢO_


[40] S. Ramírez, _FastAPI: Modern, fast (high-performance) web framework for building APIs with_
_Python_, Sebastián Ramírez, 2024, truy cập ngày 10-05-2026. [Online]. Available:
[https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)


[41] T. Wolf, L. Debut, V. Sanh, J. Chaumond, C. Delangue, A. Moi, P. Cistac, T. Rault, R. Louf,
M. Funtowicz, J. Davison, S. Shleifer, P. von Platen, C. Ma, Y. Jernite, J. Plu, C. Xu, T. Le Scao,
S. Gugger, M. Drame, Q. Lhoest, and A. M. Rush, “Transformers: State-of-the-art natural
language processing,” in _Proceedings of the 2020 Conference on Empirical Methods in Natural_
_Language Processing: System Demonstrations (EMNLP)_ . Association for Computational
Linguistics, 2020, pp. 38–45.


[42] R. Story and Folium Contributors, _Folium: Python Data, Leaflet.js Maps_, Folium Project, 2024,
[truy cập ngày 10-05-2026. [Online]. Available: https://python-visualization.github.io/folium/](https://python-visualization.github.io/folium/)


[43] S. Gillies and Shapely Contributors, _Shapely: Manipulation and Analysis of Geometric Objects_,
Shapely Project, 2024, truy cập ngày 10-05-2026. [Online]. Available:
[https://shapely.readthedocs.io/](https://shapely.readthedocs.io/)


[44] PostGIS Project Steering Committee, _PostGIS 3 Spatial and Geographic Objects for PostgreSQL_,
[OSGeo, 2024, truy cập ngày 10-05-2026. [Online]. Available: https://postgis.net/documentation/](https://postgis.net/documentation/)


[45] n8n GmbH, _n8n Documentation — Workflow Automation_, n8n GmbH, 2024, truy cập ngày
[10-05-2026. [Online]. Available: https://docs.n8n.io/](https://docs.n8n.io/)


[46] HumanSignal, Inc., _Label Studio: Open Source Data Labeling Platform_, HumanSignal, Inc.,
[2024, truy cập ngày 10-05-2026. [Online]. Available: https://labelstud.io/](https://labelstud.io/)


[47] Qwen Team, “Qwen2.5 technical report,” arXiv preprint arXiv:2412.15115, 2024, checkpoint
[reference: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct.](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)


[48] T. Dettmers, M. Lewis, Y. Belkada, and L. Zettlemoyer, “LLM.int8(): 8-bit matrix multiplication
for transformers at scale,” _Advances in Neural Information Processing Systems (NeurIPS)_, 2022.


[49] OpenStreetMap Foundation, _Overpass API — Database for OpenStreetMap_, OpenStreetMap
[Foundation, 2024, truy cập ngày 10-05-2026. [Online]. Available: https://overpass-api.de/](https://overpass-api.de/)


[50] Redis Ltd., _Redis: An open source, in-memory data store_, Redis Ltd., 2024, truy cập ngày
[10-05-2026. [Online]. Available: https://redis.io/docs/](https://redis.io/docs/)


67


