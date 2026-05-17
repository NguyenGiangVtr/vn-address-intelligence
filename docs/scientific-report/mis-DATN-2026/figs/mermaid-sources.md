# Mã nguồn Mermaid cho tất cả hình trong luận văn VNAI

> **Cách sử dụng**: Mỗi block code dưới đây là một hình độc lập. Mở https://mermaid.live (online, miễn phí) → paste vào panel trái → chụp ảnh panel phải → save vào folder `figs/` với tên gợi ý ở mỗi mục.
>
> **Lưu ý nâng cao**:
> - Đổi theme nền tối/sáng qua menu *Theme* trên mermaid.live nếu muốn match style luận văn.
> - Một số biểu đồ hình học (Ray Casting, Polygon Strategies) Mermaid không vẽ thuần hình; tôi cung cấp **flowchart minh hoạ thuật toán** (logic). Phần *hình học* nên vẽ thủ công bằng draw.io / excalidraw / TikZ cho đẹp hơn — note kèm dưới mỗi block.

---

## CHƯƠNG 3 — CƠ SỞ LÝ THUYẾT

### Hình 3.1 — `fig:transformer-arch` → lưu `figs/fig-transformer-arch.png`

```mermaid
flowchart TB
    SRC["Source: 'Hà Nội Việt Nam'"] --> EMB1[Input Embedding + PE]

    subgraph ENCODER["Encoder × 6 lớp"]
        EMB1 --> MSA[Multi-Head Self-Attention]
        MSA --> ADD1[Add & LayerNorm]
        EMB1 -.->|Residual| ADD1
        ADD1 --> FFN1[Feed-Forward Network]
        FFN1 --> ADD2[Add & LayerNorm]
        ADD1 -.->|Residual| ADD2
    end

    TGT["Target Sequence"] --> EMB2[Output Embedding + PE]

    subgraph DECODER["Decoder × 6 lớp"]
        EMB2 --> MMSA[Masked Multi-Head Self-Attention]
        MMSA --> ADD3[Add & LayerNorm]
        ADD3 --> CROSS[Encoder-Decoder Cross-Attention]
        CROSS --> ADD4[Add & LayerNorm]
        ADD4 --> FFN2[Feed-Forward Network]
        FFN2 --> ADD5[Add & LayerNorm]
    end

    ADD2 -->|Encoded Context| CROSS
    ADD5 --> LIN[Linear + Softmax]
    LIN --> OUT[Output Probabilities]

    style ENCODER fill:#e3f2fd
    style DECODER fill:#fff3e0
    style MSA fill:#bbdefb
    style MMSA fill:#ffe0b2
    style CROSS fill:#ffcc80
```

---

### Hình 3.2 — `fig:phobert-ner` → lưu `figs/fig-phobert-ner.png`

```mermaid
flowchart TB
    RAW["Chuỗi đầu vào (hậu cải cách 2025)<br/>'268 Lý Thường Kiệt, Phường Diên Hồng, TP. HCM'"]
    RAW --> SEG["VnCoreNLP<br/>Word Segmentation"]
    SEG --> BPE["FastBPE<br/>Subword Encoding"]
    BPE --> PHO["PhoBERT-base<br/>12 lớp encoder, d=768"]
    PHO --> H["Vector ngữ cảnh<br/>h₁, h₂, …, hₙ ∈ ℝ⁷⁶⁸"]
    H --> BILSTM["BiLSTM<br/>forward + backward"]
    BILSTM --> HT["h̃ᵢ = [→hᵢ ; ←hᵢ]"]
    HT --> CRF["CRF Layer<br/>Ma trận chuyển trạng thái A"]
    CRF --> VIT["Viterbi Decoding<br/>arg max P(y|x)"]
    VIT --> TAGS["Chuỗi nhãn BIO:<br/>B-HOUSENUM | B-STREET | I-STREET | O |<br/>B-WARD | B-PROVINCE<br/>(B-/I-DISTRICT giữ trong tập nhãn<br/>cho địa chỉ tiền cải cách)"]

    style PHO fill:#bbdefb
    style BILSTM fill:#ffe0b2
    style CRF fill:#ce93d8
    style TAGS fill:#a5d6a7
```

---

### Hình 3.3 — `fig:retrieval-arch` → lưu `figs/fig-retrieval-arch.png`

```mermaid
flowchart TB
    subgraph BI["(a) Bi-encoder"]
        direction TB
        BQ["Query q"] --> BEQ["Encoder Eq"]
        BD["Doc d"] --> BED["Encoder Ed"]
        BEQ --> BVQ["⃗q (1 vector)"]
        BED --> BVD["⃗d (1 vector)"]
        BVQ --> BCOS["cos(⃗q, ⃗d)"]
        BVD --> BCOS
        BCOS --> BSCORE["Score<br/>⚡ Tiền tính toán corpus"]
    end

    subgraph LATE["(b) Late Interaction"]
        direction TB
        LQ["Query tokens q₁…qₘ"] --> LEQ["Encoder"]
        LD["Doc tokens d₁…dₙ"] --> LED["Encoder"]
        LEQ --> LVQ["m vectors"]
        LED --> LVD["n vectors"]
        LVQ --> LSIM["Σᵢ maxⱼ cos(⃗qᵢ, ⃗dⱼ)"]
        LVD --> LSIM
        LSIM --> LSCORE["Score<br/>🎯 Giữ chi tiết hạt mịn"]
    end

    subgraph CROSS["(c) Cross-encoder"]
        direction TB
        CQD["[CLS] q [SEP] d [SEP]"] --> CENC["Single Encoder<br/>Full Attention"]
        CENC --> CCLS["Vector [CLS]"]
        CCLS --> CHEAD["Classification Head"]
        CHEAD --> CSCORE["Score<br/>🏆 Chính xác nhất<br/>❌ Không tiền tính toán"]
    end

    style BI fill:#e3f2fd
    style LATE fill:#fff9c4
    style CROSS fill:#ffebee
```

---

### Hình 3.4 — `fig:siamese-triplet` → lưu `figs/fig-siamese-triplet.png`

```mermaid
flowchart TB
    subgraph NET["Mạng Siamese 3 nhánh (shared weights)"]
        A["Anchor a"] --> EA["Encoder"]
        P["Positive p"] --> EP["Encoder"]
        N["Negative n"] --> EN["Encoder"]
        EA --> VA["⃗a"]
        EP --> VP["⃗p"]
        EN --> VN["⃗n"]
        VA --> L["Triplet Loss<br/>L = max(0, ‖⃗a−⃗p‖² − ‖⃗a−⃗n‖² + α)"]
        VP --> L
        VN --> L
    end

    subgraph BEF["Trước huấn luyện (embedding 2D)"]
        BA(("a"))
        BP(("p"))
        BN(("n"))
    end

    subgraph AFT["Sau huấn luyện"]
        FA(("a"))
        FP(("p"))
        FN(("n"))
        FA ==>|pull together| FP
        FA ==>|push apart ≥ α| FN
    end

    L -.->|gradient update| BEF
    BEF -.->|học| AFT

    style NET fill:#e3f2fd
    style L fill:#fff3e0
    style FP fill:#c8e6c9
    style FN fill:#ffcdd2
```

---

### Hình 3.5 — `fig:ray-casting` → lưu `figs/fig-ray-casting.png`

> **Khuyến nghị**: Mermaid khó vẽ thuần hình học. Block dưới là flowchart **giải thích thuật toán** Ray Casting. Phần *hình* (điểm trong/ngoài polygon) nên vẽ bằng **draw.io** hoặc **TikZ** cho đẹp hơn.

```mermaid
flowchart TB
    START["Điểm P(x, y)<br/>Polygon = [v₁, v₂, …, vₙ]"] --> RAY["Vẽ tia ngang từ P<br/>sang phải vô hạn"]
    RAY --> COUNT["Đếm số lần tia cắt cạnh polygon"]
    COUNT --> CHECK{"Số lần cắt"}
    CHECK -->|Lẻ| INSIDE["✓ P nằm TRONG polygon"]
    CHECK -->|Chẵn| OUTSIDE["✗ P nằm NGOÀI polygon"]

    OPTI["Tối ưu PostGIS:<br/>R-tree (GiST) loại polygon<br/>không thể chứa P<br/>trước khi áp Ray Casting"] -.-> RAY

    style INSIDE fill:#c8e6c9
    style OUTSIDE fill:#ffcdd2
    style OPTI fill:#fff9c4
```

---

### Hình 3.6 — `fig:polygon-strategies` → lưu `figs/fig-polygon-strategies.png`

> **Khuyến nghị tương tự**: phần geometric (polygon thật) nên vẽ trong draw.io. Block dưới là **flowchart logic 3 chiến lược**.

```mermaid
flowchart LR
    subgraph BU["(a) Buffer-Union"]
        direction TB
        BP["Polygon P"] --> BB["B(p, r):<br/>buffer bán kính r"]
        BB --> BU2["P' = P ∪ B(p, r)"]
        BU2 --> BUR["✓ Sai số nhỏ<br/>⚠ Có thể xâm phạm láng giềng"]
    end

    subgraph CH["(b) Concave Hull / Alpha Shape"]
        direction TB
        CPTS["Đám mây điểm<br/>𝒫 = {p₁, …, pₖ}"] --> CA["Alpha Shape<br/>tham số α"]
        CA --> CHU["P' bám sát 𝒫"]
        CHU --> CHR["✓ Dữ liệu phong phú<br/>⚠ Cần mật độ điểm cao"]
    end

    subgraph EI["(c) Edge Injection"]
        direction TB
        EP["Polygon P, cạnh (vᵢ, vᵢ₊₁)"] --> EF["Tìm cạnh gần nhất<br/>điểm p ngoại vi"]
        EF --> EIN["Chèn p:<br/>(vᵢ, p, vᵢ₊₁)"]
        EIN --> EIR["✓ Ít xâm lấn nhất<br/>⚠ Có thể tạo răng cưa"]
    end

    style BU fill:#e3f2fd
    style CH fill:#fff9c4
    style EI fill:#f3e5f5
```

---

### Hình 3.7 — `fig:acs-decision` → lưu `figs/fig-acs-decision.png`

```mermaid
flowchart TB
    INPUT["Truy vấn q + ứng viên aᵢ"]

    INPUT --> ST["S_text<br/>Typesense BM25"]
    INPUT --> SS["S_sem<br/>Cosine mGTE"]
    INPUT --> VH["V_hier<br/>Phân cấp trong mat"]
    INPUT --> VT["V_temporal<br/>Trọng số thời gian SCD"]

    ST --> MIX["Weighted Sum Model:<br/>α·S_text + β·S_sem<br/>+ γ·V_hier + δ·V_temporal<br/>α+β+γ+δ = 1"]
    SS --> MIX
    VH --> MIX
    VT --> MIX

    MIX --> ACS["ACS(aᵢ | q)"]

    ACS --> C1{"ACS ≥ 0.85?"}
    C1 -->|Có| C2{"V_temporal = 1?"}
    C1 -->|Không| C3{"ACS ≥ 0.50?"}

    C2 -->|Có| ACCEPT["🟢 Auto-Accept<br/>'Địa chỉ chính xác hoàn toàn'"]
    C2 -->|Không| CONVERT["🔵 Auto-Convert<br/>'Đã cập nhật đơn vị hành chính mới 2025'"]

    C3 -->|Có| SUGGEST["🟡 Suggest<br/>'Có phải bạn muốn tìm…?'"]
    C3 -->|Không| REJECT["🔴 Reject / Human Review<br/>'Không tìm thấy địa chỉ hợp lệ'"]

    style ACCEPT fill:#c8e6c9
    style CONVERT fill:#bbdefb
    style SUGGEST fill:#fff9c4
    style REJECT fill:#ffcdd2
```

---

## CHƯƠNG 4 — THIẾT KẾ KHUNG GIẢI PHÁP

### Hình 4.1 — `fig:layered-arch` → lưu `figs/fig-layered-arch.png`

```mermaid
flowchart TB
    subgraph L1["🖥 Lớp 1: Presentation"]
        L1A["Web UI tĩnh HTML/CSS/JS"]
        L1B["REST API Client"]
    end

    subgraph L2["🔌 Lớp 2: API (FastAPI)"]
        L2A["/api/* routers"]
        L2B["/api/spatial/*"]
        L2C["/api/boundary/*"]
        L2D["Middleware: CORS + JWT"]
    end

    subgraph L3["⚙️ Lớp 3: Business / Service"]
        L3A["Gov-Sync Service"]
        L3B["OSM Collector"]
        L3C["Ground Truth Sync"]
        L3D["Enrichment Service"]
        L3E["Auth Service"]
    end

    subgraph L4["🤖 Lớp 4: AI Hub"]
        L4A["PreLabeler"]
        L4B["AddressNER<br/>PhoBERT + BiLSTM-CRF"]
        L4C["SiameseMGTE<br/>(retrieval)"]
        L4D["LLMQwen3<br/>(refinement)"]
        L4E["EpochDetector"]
        L4F["ACSCalculator"]
    end

    subgraph L5["💾 Lớp 5: Data"]
        L5A[("PostgreSQL<br/>4 schemas:<br/>mat, osm, ath, prq")]
        L5B[("Redis Cache")]
        L5C[("FAISS Vector Index")]
    end

    L1 --> L2
    L2 --> L3
    L3 --> L4
    L3 --> L5
    L4 --> L5

    style L1 fill:#e3f2fd
    style L2 fill:#bbdefb
    style L3 fill:#90caf9
    style L4 fill:#64b5f6,color:#fff
    style L5 fill:#1976d2,color:#fff
```

---

### Hình 4.2 — `fig:repo-structure` → lưu `figs/fig-repo-structure.png`

```mermaid
flowchart LR
    REPO["📦 repo/<br/>Kho mã nguồn"]

    REPO --> APP["📁 app/"]
    REPO --> UI["📁 ui/<br/>HTML/CSS/JS"]
    REPO --> SCRIPTS["📁 scripts/<br/>Vận hành + thực nghiệm"]
    REPO --> DATA["📁 data/<br/>Seed + export"]
    REPO --> MODELS["📁 models/<br/>Checkpoint"]
    REPO --> DOCS["📁 docs/"]
    REPO --> REPORTS["📁 reports/<br/>Artifact"]

    APP --> API["api/<br/>FastAPI + routers"]
    APP --> CORE["core/<br/>Config, ORM, cache"]
    APP --> SERVICES["services/<br/>NSO, OSM, Auth"]
    APP --> AI["ai/<br/>NER, mGTE, Qwen,<br/>PreLabeler"]
    APP --> GEO["geometry/<br/>edge_inject,<br/>buffer_union,<br/>concave_hull"]
    APP --> DOMAIN["domain/<br/>Hằng số + SQL"]
    APP --> TOOLS["tools/<br/>Boundary viz"]

    style REPO fill:#fff9c4
    style APP fill:#e3f2fd
    style AI fill:#c8e6c9
    style GEO fill:#ffcc80
```

---

### Hình 4.3 — `fig:erd-schema` → lưu `figs/fig-erd-schema.png`

```mermaid
erDiagram
    PROVINCE ||--o{ DISTRICT : "1 - N"
    DISTRICT ||--o{ WARD : "1 - N"
    WARD ||--o{ WARD_MAPPING : "có ánh xạ"
    PROVINCE ||--o{ AREA_POLYGON : "có ranh giới"
    DISTRICT ||--o{ AREA_POLYGON : "có ranh giới"
    WARD ||--o{ AREA_POLYGON : "có ranh giới"
    PROVINCE ||--o{ UNIT_EDGE : "đầu/đích"
    DISTRICT ||--o{ UNIT_EDGE : "đầu/đích"
    WARD ||--o{ UNIT_EDGE : "đầu/đích"

    ADDRESS_QUEUE }o--|| WARD : "lineage (queue.ward_id → mat.ward)"
    GROUND_TRUTH }o--|| WARD : "lineage hậu cải cách"
    SUPA_RUN ||--o{ SUPA_SPECIMEN : "1 run - N specimen"
    GROUND_TRUTH ||--o{ SUPA_SPECIMEN : "được lấy mẫu"

    PROVINCE {
        bigint row_id PK
        int province_id
        string province_name
        int admin_version "1=pre, 2=post"
        int old_id FK
        date valid_from
        date valid_to
        bool is_active
    }

    DISTRICT {
        bigint row_id PK
        int district_id
        int province_id FK
        int admin_version
        int old_id
        date valid_from
        date valid_to
    }

    WARD {
        bigint row_id PK
        int ward_id
        int district_id FK
        int admin_version
        int old_id
        date valid_from
    }

    WARD_MAPPING {
        bigint id PK
        int ward_id_old
        int ward_id_new
        string relationship_type
    }

    UNIT_EDGE {
        bigint id PK
        int from_unit_id
        int to_unit_id
        string relationship_type "MERGES_INTO etc."
        date effective_date
    }

    AREA_POLYGON {
        bigint id PK
        string unit_level
        int unit_id
        json geojson
        string source "OSM/GSO/MANUAL"
    }

    ADDRESS_QUEUE {
        bigint id PK
        string raw_address
        string processing_status
        json phobert_parsed
        float phobert_confidence
        string address_standardized
        float latitude
        float longitude
    }

    GROUND_TRUTH {
        bigint id PK
        string address "post-2025"
        string old_address "pre-2025"
        int province_id
        int district_id
        int ward_id
    }

    SUPA_RUN {
        bigint id PK
        int n_requested
        int rng_seed
        string noise_profile_id
        string git_commit
    }

    SUPA_SPECIMEN {
        bigint id PK
        bigint run_id FK
        bigint ground_truth_id FK
        string noisy_raw_address
        string ref_address_v1
        string ref_address_v2
        string pred_standardized
    }
```

---

### Hình 4.4 — `fig:gov-sync-workflow` → lưu `figs/fig-gov-sync-workflow.png`

```mermaid
flowchart LR
    TRIG["⏰ Cron Trigger<br/>02:00 daily<br/>hoặc Webhook"] --> FETCH["🌐 HTTP Request<br/>NSO SOAP/REST"]
    FETCH --> PARSE["📋 JSON Parser<br/>+ Validator"]
    PARSE --> TRANS["🔧 Transform (JS)<br/>NFC normalize<br/>Checksum diff"]
    TRANS --> SCD["💾 PostgreSQL Upsert SCD<br/>valid_to=NOW(), is_active=FALSE<br/>→ chèn bản ghi mới"]
    SCD --> EDGE["📊 Insert mat.unit_edge<br/>MERGES_INTO / RENAMES_TO"]
    EDGE --> CACHE["🗑 Redis: invalidate<br/>cache đơn vị HC"]
    CACHE --> NOTIFY["📢 Slack/Email<br/>báo cáo thay đổi"]
    NOTIFY --> LOG[("📝 ath.sync_log<br/>sync_source=N8N_WORKFLOW<br/>run_id chung")]

    FETCH -.->|Timeout| RETRY["⚠️ Exponential Backoff Retry"]
    RETRY -.-> FETCH

    style TRIG fill:#fff3e0
    style SCD fill:#bbdefb
    style EDGE fill:#ce93d8
    style LOG fill:#a5d6a7
    style RETRY fill:#ffcdd2
```

---

### Hình 4.5 — `fig:hybrid-v1-pipeline` → lưu `figs/fig-hybrid-v1-pipeline.png`

```mermaid
flowchart TB
    IN[("prq.address_cleansing_queue<br/>status=PENDING")] --> S1["1️⃣ AddressNER<br/>PhoBERT + BiLSTM-CRF<br/>Bóc tách số nhà/đường/ngõ/phường/quận/tỉnh"]
    S1 --> S2["2️⃣ Chuẩn hoá tiền tố đường<br/>(map viết tắt)"]
    S2 --> S3["3️⃣ Dựng chuỗi ngữ cảnh<br/>số nhà + đường + ngõ + HC"]
    S3 --> S4["4️⃣ SiameseMGTE Retrieve<br/>Top-k ứng viên kèm metadata<br/>(GSO ID, toạ độ)"]
    S4 --> S5["5️⃣ LLMQwen3 Refinement<br/>Sinh JSON chuẩn hoá<br/>từ danh sách top-k"]
    S5 --> S6["6️⃣ EpochDetector<br/>PRE_2025 / POST_2025 / AMBIGUOUS"]
    S6 --> S7["7️⃣ ACSCalculator<br/>S_sem = max(LLM_score, Retrieval_score)<br/>ACS = α·S_text + β·S_sem + γ·V_hier + δ·V_temporal"]
    S7 --> S8["8️⃣ Update bản ghi<br/>address_standardized, ACS,<br/>processing_method='HYBRID_V1',<br/>back-fill lat/lng từ top-1"]
    S8 --> DONE[("status=DONE")]

    S1 -.->|Lỗi nạp mô hình| FB["🛟 Fallback:<br/>PreLabeler rule-based"]
    FB -.-> S8

    style S1 fill:#bbdefb
    style S4 fill:#fff59d
    style S5 fill:#ce93d8
    style S7 fill:#a5d6a7
    style FB fill:#ffe0b2
```

---

### Hình 4.6 — `fig:waterfall-enrichment` → lưu `figs/fig-waterfall-enrichment.png`

```mermaid
flowchart LR
    REQ["📨 Yêu cầu<br/>enrichment"] --> L1{"🥇 Lớp 1<br/>Redis Cache"}

    L1 -->|"Hit<br/>~20-40%"| O1["✓ Trả ngay<br/>$0 | &lt;5ms"]
    L1 -->|Miss| L2{"🥈 Lớp 2<br/>OSM + VietMap"}

    L2 -->|"Confidence cao<br/>~40-50%"| O2["✓ Trả + cache<br/>$ thấp | ~50ms"]
    L2 -->|Confidence thấp| L3{"🥉 Lớp 3<br/>Google Maps API"}

    L3 -->|"~10-20%"| O3["✓ Trả + cache<br/>$$$ cao | ~150ms"]

    O1 --> RES["🎯 Địa chỉ làm giàu"]
    O2 --> RES
    O3 --> RES

    style L1 fill:#c8e6c9
    style L2 fill:#fff9c4
    style L3 fill:#ffcdd2
    style O1 fill:#81c784
    style O2 fill:#ffeb3b
    style O3 fill:#e57373
```

---

### Hình 4.7 — `fig:supa-workflow` → lưu `figs/fig-supa-workflow.png`

```mermaid
flowchart TB
    GT[("🔒 prq.ground_truth<br/>CHỈ ĐỌC<br/>(Bất biến nghiên cứu)")]

    GT -->|"SELECT only"| S1["📦 Bước 1: extract<br/>--n, --seed, --noise-profile<br/>Sinh nhiễu deterministic"]
    S1 --> SR[("prq.supa_benchmark_run<br/>rng_seed + git_commit")]
    S1 --> SS[("prq.supa_benchmark_specimen<br/>noisy + ref_v1 + ref_v2")]

    SS --> S2["📤 Bước 2: export-specimens<br/>CSV UTF-8 với cột<br/>pred_standardized=blank"]
    S2 --> EXT["🤖 Bước 3: Pipeline ngoài<br/>Normalizer chạy trên CSV<br/>(checkpoint, GPU, commit)"]
    EXT --> S3["📥 Bước 4: import-preds<br/>--source-note bắt buộc<br/>Manifest JSON ghi commit + dòng"]
    S3 --> SS

    SS --> S4["📊 Bước 5: eval + export-tex<br/>Chuẩn hoá NFC + gom whitespace<br/>EM@v1, EM@v2<br/>Sinh \\providecommand{...}"]
    S4 --> METRICS["📈 reports/*.json metrics<br/>+ ath.supa_stratified_eval_summary"]

    GT -.->|"❌ KHÔNG<br/>INSERT/UPDATE/DELETE"| GT

    style GT fill:#ffcdd2
    style SR fill:#fff9c4
    style SS fill:#fff9c4
    style METRICS fill:#a5d6a7
```

---

## CHƯƠNG 5 — THỰC NGHIỆM

### Hình 5.1 — `fig:audit-distribution` → lưu `figs/fig-audit-distribution.png`

```mermaid
pie title "Audit Bridge: 437.862 bản ghi (G2 = 96.61%)"
    "Pass G2 (triple inner join)" : 96.61
    "Fail G2 (cần reconcile)" : 3.39
```

**Hoặc** dùng version 2-cổng:

```mermaid
pie title "Audit Bridge: 437.862 bản ghi (G3 = 96.79%)"
    "Pass G3 (denormalized aligned)" : 96.79
    "Fail G3 (14.044 dòng)" : 3.21
```

---

### Hình 5.2 — `fig:strata-distribution` → lưu `figs/fig-strata-distribution.png`

```mermaid
pie title "Cohort SUPA-Bench phân tầng strat-v1 (n=2.000/lần chạy)"
    "D1 - Đô thị (40%, 800 mẫu)" : 800
    "D2 - Nhiễu cao (20%, 400 mẫu)" : 400
    "D3 - Lưỡng thời (30%, 600 mẫu)" : 600
    "D4 - Ranh giới không gian (10%, 200 mẫu)" : 200
```

---

### Hình 5.3 — `fig:emv1-k5` → lưu `figs/fig-emv1-k5.png`

```mermaid
xychart-beta
    title "EM@v1 trên K = 5 lần chạy stratified (oracle)"
    x-axis ["run 56", "run 57", "run 58", "run 59", "run 60"]
    y-axis "EM@v1 (%)" 15 --> 17
    bar [16.65, 16.40, 16.10, 15.95, 15.55]
    line [16.14, 16.14, 16.14, 16.14, 16.14]
```

> **Lưu ý**: `xychart-beta` là tính năng experimental của Mermaid, cần phiên bản ≥ 10.6. Trên mermaid.live → menu *Settings* → chọn `mermaid@latest` để chạy. Các giá trị trên là minh hoạ (mean = 16.14, std ≈ 0.44, min = 15.55, max = 16.65).
>
> **Nếu xychart-beta lỗi**, fallback dùng bar chart đơn giản hoặc vẽ tay bằng Python matplotlib và lưu PNG.

---

## 📋 BẢNG TỔNG HỢP — TÊN FILE & VỊ TRÍ TRONG LUẬN VĂN

| # | Label LaTeX | File PNG | Chương | Mục dùng |
|---|---|---|---|---|
| 1 | `fig:transformer-arch` | `figs/fig-transformer-arch.png` | Ch3 | §3.2 Transformer |
| 2 | `fig:phobert-ner` | `figs/fig-phobert-ner.png` | Ch3 | §3.3 PhoBERT NER |
| 3 | `fig:retrieval-arch` | `figs/fig-retrieval-arch.png` | Ch3 | §3.4 mGTE retrieval |
| 4 | `fig:siamese-triplet` | `figs/fig-siamese-triplet.png` | Ch3 | §3.5 Siamese |
| 5 | `fig:ray-casting` | `figs/fig-ray-casting.png` | Ch3 | §3.6 PostGIS PIP |
| 6 | `fig:polygon-strategies` | `figs/fig-polygon-strategies.png` | Ch3 | §3.6 Polygon adj. |
| 7 | `fig:acs-decision` | `figs/fig-acs-decision.png` | Ch3 | §3.7 ACS |
| 8 | `fig:layered-arch` | `figs/fig-layered-arch.png` | Ch4 | §4.2 Kiến trúc |
| 9 | `fig:repo-structure` | `figs/fig-repo-structure.png` | Ch4 | §4.2 Mã nguồn |
| 10 | `fig:erd-schema` | `figs/fig-erd-schema.png` | Ch4 | §4.3 CSDL |
| 11 | `fig:gov-sync-workflow` | `figs/fig-gov-sync-workflow.png` | Ch4 | §4.4 Gov-Sync |
| 12 | `fig:hybrid-v1-pipeline` | `figs/fig-hybrid-v1-pipeline.png` | Ch4 | §4.5 AI Pipeline |
| 13 | `fig:waterfall-enrichment` | `figs/fig-waterfall-enrichment.png` | Ch4 | §4.7 Enrichment |
| 14 | `fig:supa-workflow` | `figs/fig-supa-workflow.png` | Ch4 | §4.9 SUPA-Bench |
| 15 | `fig:audit-distribution` | `figs/fig-audit-distribution.png` | Ch5 | §5.3 Audit |
| 16 | `fig:strata-distribution` | `figs/fig-strata-distribution.png` | Ch5 | §5.4 Phân tầng |
| 17 | `fig:emv1-k5` | `figs/fig-emv1-k5.png` | Ch5 | §5.4 K=5 results |

---

## 🛠 QUY TRÌNH ĐỀ XUẤT — TỪ MERMAID SANG PNG TRONG LUẬN VĂN

### Bước 1: Render Mermaid → PNG
1. Mở https://mermaid.live trong trình duyệt.
2. Copy code Mermaid (chỉ phần trong ```` ```mermaid ... ``` ````) → paste vào panel trái.
3. Menu trên cùng → *Actions* → *PNG* (hoặc SVG cho chất lượng cao hơn) → tải về.
4. Đổi tên file theo bảng ở trên (ví dụ `fig-phobert-ner.png`) → save vào `figs/`.

### Bước 2: Thay placeholder bằng include hình
Trong file `.tex` tương ứng, tìm khối:

```latex
\fbox{\begin{minipage}{0.92\linewidth}\centering\vspace{1.4cm}\textit{[Hình ...]}\vspace{1.4cm}\end{minipage}}
```

→ Thay bằng:

```latex
\includegraphics[width=0.9\linewidth]{figs/fig-phobert-ner.png}
```

Caption và label giữ nguyên — không cần đổi.

### Bước 3: Compile lại
`xelatex` hoặc `pdflatex` rồi `bibtex` → 2 lần `latex` để cập nhật DS hình. DS hình sẽ tự sinh từ `\listoffigures` đã bật trong TOC.

---

## 💡 TIPS TINH CHỈNH

- **Đổi màu nhanh**: chỉnh `fill:#XXXXXX` trong dòng `style` cuối mỗi block.
- **Theme tối**: trên mermaid.live → *Theme* → chọn `dark`. Lưu ý màu chữ.
- **Phông chữ Việt**: mermaid.live render UTF-8 tốt; không cần config.
- **Sửa text**: ký tự đặc biệt trong Mermaid (như `(`, `)`, `[`, `]`) phải nằm trong `"..."`.
- **Hình quá rộng**: chỉnh `direction LR` thành `TB` (hoặc ngược lại) để xoay layout.
- **Hình bị cắt**: thêm whitespace + `\<br/>` để xuống dòng tự nhiên.

---

**Sinh bởi**: VNAI thesis project, phiên bản đồng bộ với commit cuối cùng của `chapters/` folder.
