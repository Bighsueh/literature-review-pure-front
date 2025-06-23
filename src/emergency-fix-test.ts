/**
 * 緊急修復測試文件
 * 用於驗證前端能否與後端API正常通訊
 * 
 * 執行方式：在瀏覽器控制台中運行或作為臨時頁面
 */

import { apiService } from './services/api_service';

interface TestResult {
  test: string;
  status: 'PASS' | 'FAIL' | 'SKIP';
  message: string;
  details?: unknown;
}

class EmergencyAPITester {
  private results: TestResult[] = [];

  async runAllTests(): Promise<TestResult[]> {
    console.log('🚨 開始緊急API連接測試...');
    
    await this.testHealthCheck();
    await this.testWorkspaceFilesList();
    await this.testFileUpload();
    await this.testQuery();
    
    this.printResults();
    return this.results;
  }

  private async testHealthCheck(): Promise<void> {
    try {
      console.log('🧪 測試健康檢查...');
      const response = await apiService.healthCheck();
      
      if (response.success) {
        this.addResult('健康檢查', 'PASS', '後端API可正常存取', response.data);
      } else {
        this.addResult('健康檢查', 'FAIL', `API回應錯誤: ${response.error}`);
      }
    } catch (error) {
      this.addResult('健康檢查', 'FAIL', `網路錯誤: ${error}`);
    }
  }

  private async testWorkspaceFilesList(): Promise<void> {
    try {
      console.log('🧪 測試工作區檔案列表...');
      const response = await apiService.getPapers();
      
      if (response.success) {
        this.addResult('工作區檔案列表', 'PASS', 
          `成功獲取檔案列表，共 ${Array.isArray(response.data) ? response.data.length : 0} 個檔案`, 
          response.data);
      } else {
        this.addResult('工作區檔案列表', 'FAIL', `API錯誤: ${response.error}`);
      }
    } catch (error) {
      this.addResult('工作區檔案列表', 'FAIL', `請求失敗: ${error}`);
    }
  }

  private async testFileUpload(): Promise<void> {
    try {
      console.log('🧪 測試檔案上傳 (模擬)...');
      
      // 創建一個測試用的小檔案
      const testContent = 'This is a test PDF content for emergency API testing.';
      const blob = new Blob([testContent], { type: 'application/pdf' });
      const testFile = new File([blob], 'emergency-test.pdf', { type: 'application/pdf' });
      
      const response = await apiService.uploadFile(testFile);
      
      if (response.success) {
        this.addResult('檔案上傳', 'PASS', '檔案上傳成功', response.data);
      } else {
        this.addResult('檔案上傳', 'FAIL', `上傳失敗: ${response.error}`);
      }
    } catch (error) {
      this.addResult('檔案上傳', 'FAIL', `上傳錯誤: ${error}`);
    }
  }

  private async testQuery(): Promise<void> {
    try {
      console.log('🧪 測試AI查詢...');
      const response = await apiService.query({ query: 'test emergency query' });
      
      if (response.success) {
        this.addResult('AI查詢', 'PASS', 'AI查詢功能正常', response.data);
      } else {
        this.addResult('AI查詢', 'FAIL', `查詢失敗: ${response.error}`);
      }
    } catch (error) {
      this.addResult('AI查詢', 'FAIL', `查詢錯誤: ${error}`);
    }
  }

  private addResult(test: string, status: 'PASS' | 'FAIL' | 'SKIP', message: string, details?: unknown): void {
    this.results.push({ test, status, message, details });
  }

  private printResults(): void {
    console.log('\n🚨 緊急API測試結果：');
    console.log('========================');
    
    this.results.forEach(result => {
      const emoji = result.status === 'PASS' ? '✅' : result.status === 'FAIL' ? '❌' : '⏸️';
      console.log(`${emoji} ${result.test}: ${result.message}`);
      if (result.details && result.status === 'PASS') {
        console.log('   詳細資料:', result.details);
      }
    });
    
    const passCount = this.results.filter(r => r.status === 'PASS').length;
    const totalCount = this.results.length;
    
    console.log('\n========================');
    console.log(`🎯 測試結果: ${passCount}/${totalCount} 通過`);
    
    if (passCount === totalCount) {
      console.log('🎉 所有測試通過！前端可以與後端通訊。');
    } else {
      console.log('⚠️ 部分測試失敗，需要進一步檢查。');
    }
  }

  getCurrentWorkspaceId(): string {
    return apiService.getCurrentWorkspaceId();
  }

  setTestWorkspaceId(workspaceId: string): void {
    console.log(`🚨 設置測試工作區ID: ${workspaceId}`);
    apiService.setEmergencyWorkspaceId(workspaceId);
  }
}

// 導出測試器供使用
export const emergencyTester = new EmergencyAPITester();

// 如果在瀏覽器環境中，將測試器添加到全域物件
if (typeof window !== 'undefined') {
  (window as Window & { emergencyTester: EmergencyAPITester }).emergencyTester = emergencyTester;
  console.log('🚨 緊急測試器已準備就緒');
  console.log('🚨 在控制台執行: emergencyTester.runAllTests()');
} 