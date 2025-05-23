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
      checkOdCd: "/webhook/5fd2cefe-147a-490d-ada9-8849234c1580",
      keywordExtraction: "/webhook/421337df-0d97-47b4-a96b-a70a6c35d416", 
      organizeResponse: "/webhook/1394997a-36ab-46eb-9247-8b987eca91fc"
    }
  }
};
