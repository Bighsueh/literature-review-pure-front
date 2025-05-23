// constants/apiConfig.ts
export const API_CONFIG = {
  splitSentences: {
    baseUrl: "http://localhost:8000", // Docker 服務
    endpoint: "/api/process-pdf",
    method: "POST",
    contentType: "multipart/form-data"
  },
  n8n: {
    baseUrl: "https://n8n.hsueh.tw",
    endpoints: {
      // 使用 4 個 worker 來處理 checkOdCd 請求
      checkOdCdWorkers: [
        "/webhook/5fd2cefe-147a-490d-ada9-8849234c1580", // 原始 worker
        "/webhook/5fd2cefe-147a-490d-ada9-8849234c1580", // 請替換為其他 worker 的 URL
        "/webhook/5fd2cefe-147a-490d-ada9-8849234c1580", // 請替換為其他 worker 的 URL
        "/webhook/5fd2cefe-147a-490d-ada9-8849234c1580"  // 請替換為其他 worker 的 URL
      ],
      keywordExtraction: "/webhook/421337df-0d97-47b4-a96b-a70a6c35d416", 
      organizeResponse: "/webhook/1394997a-36ab-46eb-9247-8b987eca91fc"
    }
  }
};
