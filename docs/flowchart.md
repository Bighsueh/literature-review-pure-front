graph TD
    A["使用者選擇PDF檔案"] --> B["前端檔案驗證<br/>(大小、格式、完整性)"]
    B --> C["計算檔案SHA-256雜湊值"]
    C --> D{"檔案是否已存在？<br/>(檢查file_hash)"}
    
    D -->|是| E["標記為已選取<br/>返回existing paper_id"]
    D -->|否| F["POST /upload/<br/>上傳到FastAPI後端"]
    
    F --> G["儲存檔案到temp_files/目錄"]
    G --> H["建立papers表記錄<br/>(status: 'uploading')"]
    H --> I["加入background_tasks處理佇列"]
    I --> J["回傳paper_id給前端<br/>開始進度監控"]
    
    %% 背景處理流程
    J --> K["背景任務開始<br/>(status: 'processing')"]
    K --> L["Grobid TEI XML處理<br/>解析PDF結構"]
    L --> M["解析TEI並提取章節<br/>儲存到paper_sections表"]
    M --> N["Split Sentences服務<br/>逐句切分"]
    N --> O["N8N API批次分析<br/>OD/CD句子類型判定"]
    O --> P["儲存句子到sentences表<br/>(defining_type: OD/CD/OTHER)"]
    P --> Q["清理臨時PDF檔案"]
    Q --> R["更新status: 'completed'<br/>自動加入選取清單"]
    
    %% 錯誤處理
    L --> S{"處理失敗？"}
    N --> S
    O --> S
    S -->|是| T["記錄錯誤訊息<br/>status: 'error'"]
    T --> U["提供重試按鈕<br/>可重新加入處理佇列"]
    
    %% 前端監控
    E --> V["前端顯示成功<br/>更新論文清單"]
    R --> V
    U --> W["前端顯示錯誤<br/>提供重試選項"]
    
    %% 樣式
    classDef frontend fill:#e1f5fe
    classDef backend fill:#fff3e0  
    classDef database fill:#f3e5f5
    classDef process fill:#e8f5e8
    classDef error fill:#ffebee
    
    class A,B,C,J,V,W frontend
    class F,G,I,K backend
    class H,M,P,R database
    class L,N,O process
    class S,T,U error