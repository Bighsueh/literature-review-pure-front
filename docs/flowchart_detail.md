# 論文分析系統整體運作流程圖

## 系統概述
本系統是一個基於PostgreSQL資料庫的學術論文分析平台，整合Grobid進行文檔分區處理，支援多檔案橫向比較與深度分析。系統分為兩個主要工作流：**資料準備階段**和**使用者發問階段**。

## 整體系統流程圖

```mermaid
graph TD
    %% 使用者介面層
    A[使用者上傳PDF檔案] --> B{檢查檔案雜湊}
    
    %% 檔案處理分支
    B -->|檔案已存在| C[從資料庫載入已存在資料]
    B -->|檔案不存在| D[儲存檔案資訊到PostgreSQL]
    
    %% 資料準備階段
    D --> E[暫存PDF檔案到temp目錄]
    E --> F[加入FastAPI處理佇列]
    F --> G[Grobid TEI XML處理]
    G --> H[解析TEI並提取章節資訊]
    H --> I[儲存論文分區到paper_sections表]
    I --> J[Split Sentences服務切分句子]
    J --> K[批次OD/CD句子分析]
    K --> L[儲存句子資料到sentences表]
    L --> M[自動清理暫存PDF檔案]
    M --> N[標記處理完成並加入選取清單]
    
    %% 使用者查詢階段
    C --> O[使用者發送查詢]
    N --> O
    O --> P[取得勾選檔案清單]
    P --> Q[獲取各檔案section摘要]
    Q --> R[N8N關鍵詞提取API]
    R --> S[N8N智能section選擇API]
    S --> T[根據LLM選擇提取相關內容]
    T --> U{內容提取策略}
    
    %% 內容提取分支
    U -->|definitions| V[提取OD/CD定義句子]
    U -->|full_section| W[提取完整章節內容]
    U -->|key_sentences| X[基於關鍵詞搜尋句子]
    
    %% 統一分析階段
    V --> Y[N8N統一內容分析API]
    W --> Y
    X --> Y
    Y --> Z[生成整合回應與引用]
    Z --> AA[前端顯示結果與來源引用]
    
    %% 錯誤處理分支
    G --> BB{處理失敗?}
    J --> CC{切分失敗?}
    K --> DD{分析失敗?}
    R --> EE{API調用失敗?}
    S --> FF{選擇失敗?}
    Y --> GG{分析失敗?}
    
    BB -->|是| HH[記錄錯誤並提供重試]
    CC -->|是| HH
    DD -->|是| HH
    EE -->|是| HH
    FF -->|是| HH
    GG -->|是| HH
    
    HH --> II[顯示錯誤訊息與重試按鈕]
    II --> JJ{使用者選擇重試?}
    JJ -->|是| G
    JJ -->|否| KK[結束處理]
    
    %% 多Client同步
    N --> LL[更新其他Client狀態]
    AA --> MM[同步查詢結果到其他Client]
    
    %% 系統維護
    NN[定期清理任務] --> OO[清理過期暫存檔案]
    NN --> PP[資料庫索引優化]
    
    %% 樣式定義
    classDef userAction fill:#e1f5fe
    classDef processing fill:#fff3e0
    classDef database fill:#f3e5f5
    classDef api fill:#e8f5e8
    classDef error fill:#ffebee
    classDef sync fill:#fafafa
    
    class A,O userAction
    class G,H,J,K,R,S,Y processing
    class D,I,L,P,Q database
    class R,S,Y api
    class BB,CC,DD,EE,FF,GG,HH,II error
    class LL,MM,NN sync
```

## 詳細子流程圖

### 1. 檔案處理流程 (資料準備階段)

```mermaid
graph TD
    A1[檔案上傳] --> B1[計算檔案雜湊SHA-256]
    B1 --> C1{檔案已存在於資料庫?}
    C1 -->|是| D1[標記為已選取並返回]
    C1 -->|否| E1[建立papers表記錄]
    E1 --> F1[暫存PDF到temp目錄]
    F1 --> G1[加入processing_queue表]
    G1 --> H1[背景任務開始處理]
    
    H1 --> I1[更新狀態為processing]
    I1 --> J1[調用Grobid API處理PDF]
    J1 --> K1[解析TEI XML結構]
    K1 --> L1[提取章節並儲存到paper_sections]
    L1 --> M1[調用Split Sentences服務]
    M1 --> N1[逐句進行N8N OD/CD分析]
    N1 --> O1[儲存到sentences表]
    O1 --> P1[刪除暫存PDF檔案]
    P1 --> Q1[更新狀態為completed]
    Q1 --> R1[自動加入paper_selections]
```

### 2. 查詢處理流程 (使用者發問階段)

```mermaid
graph TD
    A2[使用者輸入查詢] --> B2[檢查已選取的論文清單]
    B2 --> C2{有選取的論文?}
    C2 -->|否| D2[提示選擇論文]
    C2 -->|是| E2[獲取papers section摘要]
    
    E2 --> F2[調用N8N關鍵詞提取API]
    F2 --> G2[調用N8N智能section選擇API]
    G2 --> H2[LLM分析並選擇相關sections]
    H2 --> I2[根據focus_type提取內容]
    
    I2 --> J2{focus_type判斷}
    J2 -->|definitions| K2[從sentences表提取OD/CD句子]
    J2 -->|full_section| L2[從paper_sections表提取完整內容]
    J2 -->|key_sentences| M2[基於關鍵詞搜尋相關句子]
    
    K2 --> N2[調用N8N統一內容分析API]
    L2 --> N2
    M2 --> N2
    N2 --> O2[生成整合回應]
    O2 --> P2[處理引用格式 [[ref:id]]]
    P2 --> Q2[前端顯示結果]
    Q2 --> R2[提供引用按鈕與來源資訊]
```

### 3. 錯誤處理與重試機制

```mermaid
graph TD
    A3[處理過程中發生錯誤] --> B3[記錄詳細錯誤資訊]
    B3 --> C3[更新papers表error_message]
    C3 --> D3[更新processing_queue狀態為failed]
    D3 --> E3{錯誤是否可重試?}
    
    E3 -->|是| F3[提供重試按鈕]
    E3 -->|否| G3[顯示永久錯誤訊息]
    
    F3 --> H3[使用者點擊重試]
    H3 --> I3[重置處理狀態]
    I3 --> J3[清除錯誤訊息]
    J3 --> K3[重新加入處理佇列]
    K3 --> L3[從失敗階段重新開始]
    
    G3 --> M3[建議手動檢查檔案]
```

### 4. 多Client同步機制

```mermaid
graph TD
    A4[Client A 執行操作] --> B4[更新後端狀態]
    B4 --> C4[其他Client定時輪詢]
    C4 --> D4[檢查狀態變更]
    D4 --> E4{狀態有變更?}
    
    E4 -->|是| F4[更新本地狀態]
    E4 -->|否| G4[繼續輪詢]
    
    F4 --> H4[更新UI顯示]
    H4 --> I4[通知使用者狀態變更]
    
    G4 --> C4
```

## 技術架構組件圖

```mermaid
graph TB
    subgraph "前端層 (React + TypeScript)"
        A[檔案上傳組件]
        B[聊天介面]
        C[論文選擇面板]
        D[進度顯示]
    end
    
    subgraph "API層 (FastAPI)"
        E[檔案上傳API]
        F[查詢處理API]
        G[論文管理API]
        H[狀態監控API]
    end
    
    subgraph "外部服務"
        I[Grobid TEI處理]
        J[Split Sentences]
        K[N8N Workflow APIs]
    end
    
    subgraph "資料庫層 (PostgreSQL)"
        L[(papers表)]
        M[(paper_sections表)]
        N[(sentences表)]
        O[(paper_selections表)]
        P[(processing_queue表)]
    end
    
    subgraph "背景任務"
        Q[檔案處理流水線]
        R[定期清理任務]
        S[佇列管理器]
    end
    
    A --> E
    B --> F
    C --> G
    D --> H
    
    E --> I
    F --> K
    E --> J
    
    E --> L
    F --> N
    G --> O
    H --> P
    
    Q --> I
    Q --> J
    Q --> K
    R --> L
    S --> P
```

## 資料流向圖

```mermaid
graph LR
    subgraph "輸入層"
        A[PDF檔案]
        B[使用者查詢]
    end
    
    subgraph "處理層"
        C[Grobid TEI]
        D[Split Sentences]
        E[N8N OD/CD分析]
        F[N8N查詢處理]
    end
    
    subgraph "儲存層"
        G[(TEI XML)]
        H[(章節資料)]
        I[(句子資料)]
        J[(選取狀態)]
    end
    
    subgraph "輸出層"
        K[整合回應]
        L[引用來源]
        M[進度狀態]
    end
    
    A --> C --> G
    G --> D --> H
    H --> E --> I
    
    B --> F
    F --> I
    F --> H
    F --> J
    
    I --> K
    H --> L
    G --> M
```

## 系統狀態轉換圖

```mermaid
stateDiagram-v2
    [*] --> 檔案上傳中: 使用者上傳PDF
    檔案上傳中 --> 處理佇列中: 上傳完成
    處理佇列中 --> Grobid處理中: 開始處理
    Grobid處理中 --> 句子分析中: TEI解析完成
    句子分析中 --> 處理完成: 所有句子分析完成
    處理完成 --> 可查詢: 加入選取清單
    
    Grobid處理中 --> 處理失敗: Grobid錯誤
    句子分析中 --> 處理失敗: 分析錯誤
    處理失敗 --> 等待重試: 提供重試選項
    等待重試 --> Grobid處理中: 使用者重試
    
    可查詢 --> 查詢處理中: 使用者發送查詢
    查詢處理中 --> 查詢完成: 回應生成
    查詢完成 --> 可查詢: 等待下次查詢
    
    查詢處理中 --> 查詢失敗: API錯誤
    查詢失敗 --> 可查詢: 錯誤處理完成
```

## 總結

這個流程圖完整描述了論文分析系統的運作機制，包括：

1. **資料準備階段**：從檔案上傳到句子分析完成的完整流程
2. **查詢處理階段**：從使用者查詢到結果顯示的智能處理流程
3. **錯誤處理機制**：完善的錯誤捕獲、記錄和重試機制
4. **多Client同步**：支援多個瀏覽器視窗同時操作的同步機制
5. **技術架構**：清晰的分層架構和組件關係

系統採用PostgreSQL資料庫、Grobid TEI處理、N8N工作流API和FastAPI後端，提供了一個完整的學術論文分析解決方案。