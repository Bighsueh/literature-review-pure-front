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
  const [tourInstance, setTourInstance] = useState<ReturnType<typeof driver> | null>(null);
  const [showWelcome, setShowWelcome] = useState(false);
  const [showAnimation, setShowAnimation] = useState(false);
  const { files } = useFileStore();
  const { conversations } = useChatStore();
  const { isMobile } = useResponsive();

  useEffect(() => {
    // 檢查是否是第一次訪問
    const hasSeenTour = localStorage.getItem('hasSeenWelcomeTour');
    if (!hasSeenTour && files.length === 0 && conversations.length === 0) {
      setShowAnimation(true);
    }
  }, [files, conversations]);

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

  const initializeTour = () => {
    const driverInstance = driver({
      showProgress: true,
      showButtons: ['next', 'previous', 'close'],
      nextBtnText: '下一步',
      prevBtnText: '上一步',
      doneBtnText: '開始使用',
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

    setTourInstance(driverInstance);
    driverInstance.drive();
  };

  const restartTour = () => {
    if (tourInstance) {
      tourInstance.drive();
    } else {
      setShowWelcome(true);
    }
  };

  return (
    <>
      {/* Welcome Animation */}
      {showAnimation && (
        <WelcomeAnimation onComplete={handleAnimationComplete} />
      )}
      
      {/* Tour Guide Button */}
      <div className={`fixed right-4 z-50 ${
        isMobile && activePanel === 'chat' ? 'bottom-28' : 'bottom-4'
      }`}>
        <button
          onClick={restartTour}
          className="bg-blue-500 hover:bg-blue-600 text-white p-3 rounded-full shadow-lg transition-all duration-200 hover:scale-105"
          title="重新開始引導"
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
    </>
  );
};

export default WelcomeTour; 