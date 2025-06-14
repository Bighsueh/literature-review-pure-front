import React, { useEffect, useState } from 'react';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import '../../styles/driver-theme.css';
import { useFileStore } from '../../stores/fileStore';
import { useChatStore } from '../../stores/chatStore';
import { useResponsive } from '../../hooks/useResponsive';
import WelcomeAnimation from './WelcomeAnimation';

interface WelcomeTourProps {
  onTourComplete?: () => void;
  activePanel?: string;
}

const WelcomeTour: React.FC<WelcomeTourProps> = ({ onTourComplete, activePanel }) => {
  const [showWelcome, setShowWelcome] = useState(false);
  const [showAnimation, setShowAnimation] = useState(false);
  const [showTourButton, setShowTourButton] = useState(false);
  const [delayTimer, setDelayTimer] = useState<NodeJS.Timeout | null>(null);
  const { files } = useFileStore();
  const { conversations } = useChatStore();
  const { isMobile } = useResponsive();

  useEffect(() => {
    // 檢查是否是第一次訪問
    const hasSeenTour = localStorage.getItem('hasSeenWelcomeTour');
    if (!hasSeenTour && files.length === 0 && conversations.length === 0) {
      setShowAnimation(true);
    } else {
      // 如果不是第一次訪問，延遲顯示導覽按鈕
      handleDelayedButtonShow();
    }
  }, [files, conversations]);

  // 監聽面板切換，處理首次進入邏輯
  useEffect(() => {
    if (activePanel && isMobile) {
      // 面板切換後立即顯示按鈕
      setShowTourButton(true);
      
      // 檢查是否是第一次進入此面板
      const panelKey = `hasSeenPanel_${activePanel}`;
      const hasSeenPanel = localStorage.getItem(panelKey);
      
      if (!hasSeenPanel) {
        // 第一次進入此面板，延遲顯示導覽
        setTimeout(() => {
          startCurrentPanelTour();
          localStorage.setItem(panelKey, 'true');
        }, 1000);
      }
    } else if (activePanel && !isMobile) {
      // 桌面版直接顯示按鈕
      setShowTourButton(true);
    }
  }, [activePanel, isMobile]);

  // 處理延遲顯示邏輯（僅用於初始載入）
  const handleDelayedButtonShow = () => {
    // 清除之前的計時器
    if (delayTimer) {
      clearTimeout(delayTimer);
    }
    
    // 設置延遲顯示（移動裝置 2 秒，桌面 1 秒）
    const delay = isMobile ? 2000 : 1000;
    const timer = setTimeout(() => {
      setShowTourButton(true);
    }, delay);
    
    setDelayTimer(timer);
  };

  // 清理計時器
  useEffect(() => {
    return () => {
      if (delayTimer) {
        clearTimeout(delayTimer);
      }
    };
  }, [delayTimer]);

  const handleAnimationComplete = () => {
    setShowAnimation(false);
    // 動畫完成後稍微延遲一下再開始引導
    setTimeout(() => {
      setShowWelcome(true);
    }, 500);
  };

  useEffect(() => {
    if (showWelcome) {
      initializeTour();
    }
  }, [showWelcome]);

  // 獲取智能提示框位置
  const getSmartPopoverPosition = (elementId: string) => {
    const element = document.getElementById(elementId);
    if (!element) return { side: 'bottom' as const, align: 'center' as const };
    
    const rect = element.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const elementCenter = rect.top + rect.height / 2;
    
    // 如果元素在螢幕下半部，提示框顯示在上方
    if (elementCenter > viewportHeight / 2) {
      return { side: 'top' as const, align: 'center' as const };
    } else {
      return { side: 'bottom' as const, align: 'center' as const };
    }
  };



  // 根據當前面板獲取快速導覽步驟（單一面板）
  const getQuickTourSteps = () => {
    const baseSteps = [];
    
    // 根據當前面板添加相關步驟
    if (activePanel === 'files' || !activePanel) {
      baseSteps.push(
        {
          element: '#file-upload-zone',
          popover: {
            title: '📁 檔案管理區域',
            description: `
              <div class="space-y-3">
                <p>這裡是檔案管理的核心區域。您可以：</p>
                <div class="bg-blue-50 p-3 rounded-md">
                  <ul class="list-disc list-inside text-sm text-blue-800 space-y-1">
                    <li>拖放 PDF 檔案上傳</li>
                    <li>點擊選擇檔案</li>
                    <li>查看上傳進度</li>
                  </ul>
                </div>
                <p class="text-xs text-gray-500">💡 支援最大 10MB 的 PDF 檔案</p>
              </div>
            `,
            ...getSmartPopoverPosition('file-upload-zone')
          }
        },
        {
          element: '#file-upload-list',
          popover: {
            title: '📋 檔案列表',
            description: `
              <div class="space-y-3">
                <p>已上傳的檔案會顯示在這裡，包含：</p>
                <div class="bg-green-50 p-3 rounded-md">
                  <ul class="list-disc list-inside text-sm text-green-800 space-y-1">
                    <li>檔案名稱和大小</li>
                    <li>處理狀態指示</li>
                    <li>操作按鈕</li>
                  </ul>
                </div>
              </div>
            `,
            ...getSmartPopoverPosition('file-upload-list')
          }
        }
      );
    }
    
    if (activePanel === 'chat') {
      baseSteps.push(
        {
          element: '#chat-input',
          popover: {
            title: '💬 查詢輸入區',
            description: `
              <div class="space-y-3">
                <p>在這裡輸入您的查詢問題：</p>
                <div class="bg-purple-50 p-3 rounded-md">
                  <div class="text-sm font-medium text-purple-900">查詢範例：</div>
                  <ul class="list-disc list-inside text-sm text-purple-800 mt-1 space-y-1">
                    <li>「什麼是機器學習？」</li>
                    <li>「請解釋深度學習的定義」</li>
                    <li>「人工智慧的概念是什麼？」</li>
                  </ul>
                </div>
              </div>
            `,
            ...getSmartPopoverPosition('chat-input')
          }
        },
        {
          element: '#chat-messages',
          popover: {
            title: '🎯 對話結果區',
            description: `
              <div class="space-y-3">
                <p>AI 助手的回答會顯示在這裡：</p>
                <div class="bg-indigo-50 p-3 rounded-md">
                  <ul class="list-disc list-inside text-sm text-indigo-800 space-y-1">
                    <li>詳細的定義說明</li>
                    <li>原文引用標記</li>
                    <li>相關上下文</li>
                  </ul>
                </div>
                <p class="text-xs text-gray-500">💡 點擊回答可查看更多詳情</p>
              </div>
            `,
            ...getSmartPopoverPosition('chat-messages')
          }
        }
      );
    }
    
    if (activePanel === 'progress') {
      baseSteps.push(
        {
          element: '#strategy-panel',
          popover: {
            title: '📖 引用詳情面板',
            description: `
              <div class="space-y-3">
                <p>這裡顯示 AI 回答的詳細資訊：</p>
                <div class="bg-yellow-50 p-3 rounded-md">
                  <ul class="list-disc list-inside text-sm text-yellow-800 space-y-1">
                    <li>引用來源和頁碼</li>
                    <li>AI 分析策略</li>
                    <li>相關文獻片段</li>
                  </ul>
                </div>
                <p class="text-xs text-gray-500">🔍 點擊系統回答後會顯示詳情</p>
              </div>
            `,
            ...getSmartPopoverPosition('strategy-panel')
          }
        }
      );
    }
    
    return baseSteps;
  };

  const initializeTour = () => {
    // 桌面版使用原來的導覽步驟
    const driverInstance = driver({
      showProgress: true,
      showButtons: ['next', 'previous', 'close'],
      nextBtnText: '下一步',
      prevBtnText: '上一步',
      doneBtnText: '完成導覽',
      progressText: '步驟 {{current}} / {{total}}',
      onDestroyed: () => {
        localStorage.setItem('hasSeenWelcomeTour', 'true');
        setShowWelcome(false);
        onTourComplete?.();
      },
      steps: [
        {
          element: '#file-upload-zone',
          popover: {
            title: '歡迎使用定義查詢助手！ 🎉',
            description: `
              <div class="space-y-3">
                <p>我將帶您快速了解如何使用這個系統來查找學術論文中的名詞定義。</p>
                <div class="bg-blue-50 p-3 rounded-md">
                  <div class="text-sm font-medium text-blue-900">三個簡單步驟：</div>
                  <ol class="list-decimal list-inside text-sm text-blue-800 mt-1 space-y-1">
                    <li>上傳您的英文論文 PDF 檔案</li>
                    <li>等待檔案處理完成</li>
                    <li>輸入您想查詢的名詞</li>
                  </ol>
                </div>
                <p class="text-sm text-gray-600">讓我們開始吧！</p>
              </div>
            `,
            side: 'bottom',
            align: 'center'
          }
        },
        {
          element: '#file-upload-zone',
          popover: {
            title: '步驟 1: 上傳 PDF 檔案 📄',
            description: `
              <div class="space-y-3">
                <p>在這裡上傳您的英文學術論文 PDF 檔案。</p>
                <div class="bg-green-50 p-3 rounded-md">
                  <div class="text-sm font-medium text-green-900">支援兩種方式：</div>
                  <ul class="list-disc list-inside text-sm text-green-800 mt-1 space-y-1">
                    <li>直接拖放 PDF 檔案到此區域</li>
                    <li>點擊「選擇檔案」按鈕選擇檔案</li>
                  </ul>
                </div>
                <p class="text-xs text-gray-500">💡 檔案大小限制：最大 10MB</p>
              </div>
            `,
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#file-upload-list',
          popover: {
            title: '步驟 2: 檔案列表 📋',
            description: `
              <div class="space-y-3">
                <p>上傳後，您的檔案會出現在這裡，顯示檔案基本資訊。</p>
                <div class="bg-blue-50 p-3 rounded-md">
                  <div class="text-sm font-medium text-blue-900">檔案資訊包含：</div>
                  <ul class="list-disc list-inside text-sm text-blue-800 mt-1 space-y-1">
                    <li>檔案名稱和大小</li>
                    <li>上傳時間</li>
                    <li>處理狀態圖示</li>
                  </ul>
                </div>
                <p class="text-xs text-gray-500">📁 您可以管理多個檔案，點擊可切換當前檔案</p>
              </div>
            `,
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#progress-display',
          popover: {
            title: '步驟 3: 檔案處理進度 ⚙️',
            description: `
              <div class="space-y-3">
                <p>檔案上傳後，處理進度會在右側面板這裡即時顯示。</p>
                <div class="bg-yellow-50 p-3 rounded-md">
                  <div class="text-sm font-medium text-yellow-900">處理階段：</div>
                  <ol class="list-decimal list-inside text-sm text-yellow-800 mt-1 space-y-1">
                    <li>PDF 文字擷取</li>
                    <li>句子分割與分析</li>
                    <li>定義類型分類 (CD/OD)</li>
                    <li>建立搜尋索引</li>
                  </ol>
                </div>
                <p class="text-xs text-gray-500">⏱️ 處理時間視檔案大小而定，通常需要 1-3 分鐘</p>
              </div>
            `,
            side: 'left',
            align: 'start'
          }
        },
        {
          element: '#chat-input',
          popover: {
            title: '步驟 4: 輸入查詢 💬',
            description: `
              <div class="space-y-3">
                <p>檔案處理完成後，就可以在這裡輸入您想要查詢的名詞！</p>
                <div class="bg-purple-50 p-3 rounded-md">
                  <div class="text-sm font-medium text-purple-900">查詢範例：</div>
                  <ul class="list-disc list-inside text-sm text-purple-800 mt-1 space-y-1">
                    <li>「什麼是 Adaptive Expertise?」</li>
                    <li>「Machine Learning 的定義是什麼？」</li>
                    <li>「請解釋 Deep Learning」</li>
                  </ul>
                </div>
                <p class="text-xs text-gray-500">🔍 系統會自動找到相關定義並提供詳細說明</p>
              </div>
            `,
            side: 'top',
            align: 'center'
          }
        },
        {
          element: '#chat-messages',
          popover: {
            title: '步驟 5: 對話結果 🎯',
            description: `
              <div class="space-y-3">
                <p>您的查詢結果會顯示在這裡，包含找到的定義和相關引用。</p>
                <div class="bg-indigo-50 p-3 rounded-md">
                  <div class="text-sm font-medium text-indigo-900">結果特色：</div>
                  <ul class="list-disc list-inside text-sm text-indigo-800 mt-1 space-y-1">
                    <li>AI 生成的詳細定義說明</li>
                    <li>原文引用和頁碼標記</li>
                    <li>相關上下文資訊</li>
                  </ul>
                </div>
                <p class="text-xs text-gray-500">📖 點擊引用可查看原文內容</p>
              </div>
            `,
            side: 'left',
            align: 'start'
          }
        }
      ]
    });

    driverInstance.drive();
  };



  // 啟動快速導覽（當前頁面）
  const startQuickTour = () => {
    setShowTourButton(false);
    
    const steps = getQuickTourSteps();
    
    if (steps.length > 0) {
      const driverInstance = driver({
        showProgress: true,
        showButtons: ['next', 'previous', 'close'],
        nextBtnText: '下一步',
        prevBtnText: '上一步',
        doneBtnText: '完成導覽',
        progressText: '步驟 {{current}} / {{total}}',
        onDestroyed: () => {
          setShowTourButton(true);
        },
        steps
      });
      
      driverInstance.drive();
    } else {
      alert(`目前在「${activePanel === 'files' ? '檔案管理' : activePanel === 'chat' ? '查詢助手' : '引用詳情'}」頁面，請確保相關元素已載入完成。`);
      setShowTourButton(true);
    }
  };

  // 啟動當前面板導覽（移動裝置首次進入時使用）
  const startCurrentPanelTour = () => {
    const steps = getQuickTourSteps();
    
    if (steps.length > 0) {
      const driverInstance = driver({
        showProgress: true,
        showButtons: ['next', 'previous', 'close'],
        nextBtnText: '下一步',
        prevBtnText: '上一步',
        doneBtnText: '完成導覽',
        progressText: '步驟 {{current}} / {{total}}',
        onDestroyed: () => {
          // 導覽結束後不需要特別處理，按鈕保持顯示
        },
        steps
      });
      
      driverInstance.drive();
    }
  };

  // 啟動導覽
  const restartTour = () => {
    if (isMobile) {
      // 移動裝置直接啟動當前頁面導覽
      startQuickTour();
    } else {
      // 桌面版使用原來的導覽邏輯
      setShowTourButton(false);
      initializeTour();
    }
  };

  return (
    <>
      {/* Welcome Animation */}
      {showAnimation && (
        <WelcomeAnimation onComplete={handleAnimationComplete} />
      )}
      
      {/* Tour Guide Button - 智能延遲顯示 */}
      {showTourButton && (
        <div className={`fixed right-4 z-50 transition-all duration-500 ${
          isMobile && activePanel === 'chat' ? 'bottom-28' : 'bottom-4'
        } ${showTourButton ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}>
          <button
            onClick={restartTour}
            className="bg-blue-500 hover:bg-blue-600 text-white p-3 rounded-full shadow-lg transition-all duration-200 hover:scale-105 animate-pulse"
            title={isMobile ? '查看當前頁面導覽' : '開始系統導覽'}
          >
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              fill="none" 
              viewBox="0 0 24 24" 
              strokeWidth={1.5} 
              stroke="currentColor" 
              className="h-5 w-5"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z" 
              />
            </svg>
          </button>

        </div>
      )}
    </>
  );
};

export default WelcomeTour; 