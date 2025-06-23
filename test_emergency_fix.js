/**
 * 緊急修復測試腳本
 * 這個腳本可以在瀏覽器開發者工具中運行，用於測試API修復
 */

console.log('🚀 開始執行緊急修復測試...');

// 測試基礎URL
const BASE_URL = 'http://localhost:28001';
const WORKSPACE_ID = 'temp-workspace-id';

// 測試函數
async function testAPI(url, description, options = {}) {
    console.log(`\n🧪 測試: ${description}`);
    console.log(`📍 URL: ${url}`);
    
    try {
        const response = await fetch(url, {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: options.body ? JSON.stringify(options.body) : null
        });
        
        const data = await response.json();
        
        if (response.ok) {
            console.log(`✅ 成功: ${response.status}`);
            console.log('📦 回應數據:', data);
            return { success: true, data };
        } else {
            console.log(`❌ 失敗: ${response.status}`);
            console.log('📦 錯誤數據:', data);
            return { success: false, data };
        }
    } catch (error) {
        console.log(`💥 網路錯誤:`, error);
        return { success: false, error: error.message };
    }
}

// 執行測試套件
async function runEmergencyFixTests() {
    console.log('\n=== 緊急修復測試套件 ===\n');
    
    // 1. 健康檢查
    await testAPI(`${BASE_URL}/api/health/`, '後端健康檢查');
    
    // 2. 測試新的工作區化API
    console.log('\n--- 測試新的工作區化API ---');
    await testAPI(
        `${BASE_URL}/api/workspaces/${WORKSPACE_ID}/files/`, 
        '工作區檔案列表'
    );
    
    await testAPI(
        `${BASE_URL}/api/workspaces/${WORKSPACE_ID}/query/`,
        '工作區AI查詢',
        {
            method: 'POST',
            body: { query: '測試查詢問題' }
        }
    );
    
    // 3. 測試舊的API（向後相容性）
    console.log('\n--- 測試舊的API（向後相容性） ---');
    await testAPI(`${BASE_URL}/api/papers/`, '舊的論文列表API');
    
    await testAPI(
        `${BASE_URL}/api/query/`,
        '舊的AI查詢API',
        {
            method: 'POST',
            body: { query: '舊API測試查詢' }
        }
    );
    
    console.log('\n🎉 緊急修復測試完成！');
    console.log('\n📋 總結:');
    console.log('✅ 如果看到上面的測試都成功了，說明我們的API修復工作正常');
    console.log('✅ 前端現在可以與後端正確通訊');
    console.log('✅ 新的工作區化API端點運作正常');
    console.log('✅ 舊的API端點保持向後相容性');
}

// 運行測試
runEmergencyFixTests().catch(console.error);

// 匯出測試函數供手動呼叫
window.emergencyFixTest = {
    runTests: runEmergencyFixTests,
    testAPI,
    BASE_URL,
    WORKSPACE_ID
};

console.log('\n💡 提示: 您也可以手動呼叫 window.emergencyFixTest.runTests() 重新運行測試'); 