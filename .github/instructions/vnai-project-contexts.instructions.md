---
description: "Use when working on VN Address Intelligence tasks across project contexts: code reading, Python API/service implementation, AI pipeline changes, data enrichment, SQL safety, evaluation/report writing, and dashboard wiring for MIS goals."
applyTo: "**/*"
---

# VNAI Project Context Playbook

## 1. Mission Lock
- Mọi thay đổi phải phục vụ đúng bài toán: lam giau va chuan hoa dia chi Viet Nam trong boi canh bien dong hanh chinh 2025.
- Uu tien gia tri MIS: chi phi, throughput, kha nang van hanh batch lon, tinh ben vung khi thay doi don vi hanh chinh.
- Neu co nhieu phuong an, uu tien cach don gian nhat dat yeu cau va de kiem chung.

## 2. Ground Truth Architecture
- Bang trung tam nghiep vu: prq.address_cleansing_queue.
- Input chinh cua pipeline: raw_address, street_address.
- Output chinh cua pipeline: address_standardized va cac truong confidence, processing_method.
- Nhan NER chi duoc coi la nguon su that tai app/ai/constants.py.
- Ward mapping 2025 la thanh phan bat buoc khi xu ly tinh huong dia chi cu sang moi.

## 3. Context-Specific Execution Rules

### 3.1 Context: Read and Explain Code
- Di theo thu tu: entrypoint start.py -> app/main.py -> app/api/server.py -> app/core/database.py -> app/ai/production_pipeline.py.
- Luon mo ta data flow end-to-end, khong chi list file.
- Chi ra dependency quan trong giua service, ai model, database schema.
- Neu phat hien sai lech giua README va code, danh dau ro sai lech va uu tien hanh vi thuc te trong code.

### 3.2 Context: API and Service Changes
- Giu API layer mong, day logic xuong service layer.
- Khong hardcode credentials, endpoint secrets, host private.
- Uu tien logging co cau truc thay vi print.
- Giu backward compatibility cho endpoint dang duoc UI goi, neu buoc phai doi contract thi cap nhat UI cung luc.

### 3.3 Context: AI Pipeline and Model Orchestration
- Khong sua truc tiep mapping label o nhieu noi; neu doi label chi sua constants.py.
- Ton trong pipeline SQL preprocessing -> NER -> Siamese retrieval/ranking -> LLM normalization.
- Khong khoi tao lai model trong moi record neu co the tai 1 lan va tai su dung.
- Khi thay doi pipeline, neu anh huong output schema thi cap nhat docs va validation scripts lien quan.
- Tai lieu tong hop workflow trainning/experiment/inference la docs/ai-training-workflow-summary.md; khi thay doi logic app/ai bat buoc cap nhat tai lieu nay trong cung dot thay doi.

### 3.4 Context: Database, SQL, and Data Safety
- Luon dung parameterized query cho filter input tu nguoi dung.
- Neu doi schema trong app/core/database.py, bat buoc ra soat app/, scripts/, docs/ de sua query phu hop.
- Khong xoa hoac truncate du lieu that neu khong co yeu cau ro rang tu user.

### 3.5 Context: Dashboard and Frontend Wiring
- Moi tinh nang AI quan trong can co feedback tren UI: progress, log, error actionable.
- Giu dong bo NER labels giua UI va backend constants.
- Uu tien endpoint /api dang co, tranh tao endpoint moi neu co the tai su dung endpoint hien huu.
- Kiem tra responsive co ban desktop va mobile khi sua giao dien.
- Quy dinh chung bat buoc: tat ca dropdown list, notify, confirm phai dung chung mot format.
- Nguon template control mac dinh la trang Tra cuu Bien dong DVHC (lookup). Khi them moi control, chi duoc tai su dung helper/template tu nhom control nay.
- Khong tao kieu thong bao moi bang alert/confirm native neu da co bo showToast/showConfirm va control template trong ui/app.js.
- Tuyet doi khong thay doi design khi khong co yeu cau.
- Tuyet doi khong thay doi codebase của UI theme
- Trong tất cả các trang khi load data hãy tính toán canh chỉnh chiều cao các phần tử gridvew, job-log... để không bị tràn làm xuất hiện thanh ở page-content 
<!-- - **Quy tac scroll (toan bo page):** Uu tien scroll trong control (`.table-container`, `.batch-log`, `.ner-output`, `.tool-input-section`, `.content-grid` items) thay vi scroll full page. Chi dung full-page scroll khi noi dung toan man hinh bat buoc. Ap dung cho tat ca pages:
  - **Address Parser:** NER Output + Entities table scroll noi dung, Input tinh gon (44px min-height)
  - **Batch Processor:** Batch log scroll noi dung (max-height 400px), khong lock full page
  - **Training Hub:** Label registry table, experiment results table scroll noi dung
  - **Data Explorer:** Datatable scroll noi dung (max-height 500px)
  - **Lookup/Admin:** Grid items scroll independently, khong nested scroll
  - Primary scroll chi xay ra tren `#page-content`, control regions (grid, panel, table, log) tu handle overflow-y: auto -->

### 3.6 Context: Experiments, Evaluation, and Reporting
- Bao cao phai gan voi 4 KPI MIS: F1, throughput, chi phi, ti le khop voi ground truth.
- Uu tien du lieu that cua queue (505k) cho danh gia, tranh ket luan tu dummy samples.
- Neu dua ra ket qua benchmark, ghi ro sample size, phuong phap doi soat, va gioi han thuc nghiem.

### 3.7 Context: Supervisor and Thesis Documentation
- Van phong hoc thuat ngan gon, co so lieu, co logic tu van de -> giai phap -> ket qua -> han che -> huong mo rong.
- Tuan thu timeline deadline 25/05/2026 trong de xuat pham vi.
- Khong noi qua kha nang he thong neu chua co minh chung trong code/data/report.

## 4. Security and Compliance Guardrails
- Khong de lo thong tin nhay cam trong log, report, markdown, hoac screenshot.
- Khong commit .env, models artifact, evidence nhay cam.
- Khong sao chep huong dan dai dong tu ben ngoai vao repo neu khong can thiet; uu tien link tai lieu.

## 5. Definition of Done
- Dung yeu cau user, khong mo rong ngoai pham vi.
- Co verification toi thieu: lint/syntax/run path hoac kiem tra logic thay doi.
- Neu khong the run test hoac canh bao rui ro du lieu, phai noi ro trong ket qua.
- Neu thay doi anh huong docs hoac UI contract, cap nhat ngay trong cung dot thay doi.

## 6. Preferred Response Shape for This Project
- Neu user yeu cau review: uu tien liet ke findings theo muc do nghiem trong truoc, sau do moi tom tat.
- Neu user yeu cau implement: tra loi theo cau truc ket qua -> file da doi -> verification -> rui ro ton dong.
- Neu user yeu cau explain: su dung file references ro rang va mo ta data flow cu the.

## 7. UI Layout Standard: 3-Zone Parser Template
Tiến hành refactor lại theo todo.md
Mục tiêu: lấy trang Address Parser làm chuẩn
- block đầu tiên chứa 
    + hero-label: chứa title, mô tả
    + cụm textbox, button, action.. nằm gói gọn trong 1 input-wrap
    + status-bar
- block thứ 2 (có thể có hoặc không) chứa	
    + các thông số thống kê, các Chỉ số
- block chính: là nơi hiển thị gridvew, console log realtime: được thiết kế rộng rãi và page
    + Với gridview luôn áp dụng paging
    + với log console realtime: luôn áp dụng scroll khi realtime log
- Tất cả đảm bảo responsive, tối ưu trải nghiệm trên mobile, trên mobile hãy bỏ luôn với gridvew - thay thế bằng 1 UI phù hợp trải nghiệm hơn
- luôn áp dụng class mt-12 giữa các block
- Loại bỏ hết kiểu thiết kê content-grid / 2 card như hiện tại