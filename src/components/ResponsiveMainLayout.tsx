import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../stores/appStore';
import { useResponsive } from '../hooks/useResponsive';
import LeftPanel from './LeftPanel';
import CenterPanel from './CenterPanel';
import RightPanel from './RightPanel';
import Modal from './common/Modal/Modal';
import WelcomeTour from './onboarding/WelcomeTour';
import ResponsiveNavigation, { defaultNavigationItems, NavigationItem } from './common/ResponsiveNavigation';
import { useFileStore } from '../stores/fileStore';
import { ProcessedSentence } from '../types/file';
import { paperService } from '../services/paper_service';

type ActivePanel = 'files' | 'chat' | 'progress';

const ResponsiveMainLayout: React.FC = () => {
  const { ui, setUI } = useAppStore();
  const { files } = useFileStore();
  const { isTablet, isDesktop, isMobile } = useResponsive();
  const [highlightedSentence, setHighlightedSentence] = useState<ProcessedSentence | null>(null);
  const [activePanel, setActivePanel] = useState<ActivePanel>('chat');
  const [navigationItems, setNavigationItems] = useState<NavigationItem[]>(defaultNavigationItems);
  
  // 滑動相關狀態
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);
  const mainContentRef = useRef<HTMLDivElement>(null);

  // 面板順序
  const panelOrder: ActivePanel[] = ['files', 'chat', 'progress'];

  // 應用啟動時初始化資料同步
  useEffect(() => {
    const initializeApp = async () => {
      try {
        console.log('Initializing app and checking for completed papers...');
        
        const hasCompleted = await paperService.hasAnyCompletedPapers();
        
        if (hasCompleted) {
          console.log('Found completed papers, syncing sentence data...');
          const sentencesData = await paperService.getAllSelectedPapersSentences();
          
          if (sentencesData.totalSentences > 0) {
            console.log(`App initialization complete: ${sentencesData.totalSentences} sentences synced from ${sentencesData.totalPapers} papers`);
          }
        }
      } catch (error) {
        console.error('Error during app initialization:', error);
      }
    };
    
    initializeApp();
  }, []);

  // 更新導航項目的活動狀態
  useEffect(() => {
    setNavigationItems(items => 
      items.map(item => ({
        ...item,
        active: item.id === activePanel
      }))
    );
  }, [activePanel]);

  // 滑動檢測邏輯
  const minSwipeDistance = 50; // 最小滑動距離

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    if (!isMobile) return;
    setTouchEnd(null);
    setDragOffset(0);
    setIsDragging(false);
    setTouchStart({
      x: e.targetTouches[0].clientX,
      y: e.targetTouches[0].clientY
    });
  }, [isMobile]);

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isMobile || !touchStart) return;
    
    const currentTouch = {
      x: e.targetTouches[0].clientX,
      y: e.targetTouches[0].clientY
    };
    
    setTouchEnd(currentTouch);
    
    const distanceX = currentTouch.x - touchStart.x; // 修正：當前位置減去起始位置
    const distanceY = currentTouch.y - touchStart.y;
    
    // 判斷是否為水平滑動
    if (Math.abs(distanceX) > Math.abs(distanceY) && Math.abs(distanceX) > 10) {
      setIsDragging(true);
      
      // 計算拖拽偏移量（vw 單位）
      const currentIndex = panelOrder.indexOf(activePanel);
      const maxOffset = 30; // 最大偏移量（vw）
      let offset = (distanceX / window.innerWidth) * 100; // 轉換為 vw
      
      // 限制邊界 - 防止滑動超出範圍
      if (currentIndex === 0 && offset > 0) {
        // 第一個面板，不能向右滑動太多
        offset = Math.min(offset * 0.3, maxOffset);
      } else if (currentIndex === panelOrder.length - 1 && offset < 0) {
        // 最後一個面板，不能向左滑動太多
        offset = Math.max(offset * 0.3, -maxOffset);
      } else {
        // 中間面板，限制偏移量
        offset = Math.max(-maxOffset, Math.min(maxOffset, offset));
      }
      
      setDragOffset(offset);
    }
  }, [isMobile, touchStart, activePanel, panelOrder]);

  const onTouchEnd = useCallback(() => {
    if (!isMobile || !touchStart || !touchEnd) return;

    const distanceX = touchEnd.x - touchStart.x; // 修正：保持與 onTouchMove 一致
    const distanceY = touchEnd.y - touchStart.y;
    const isRightSwipe = distanceX > minSwipeDistance; // 向右滑動（正值）
    const isLeftSwipe = distanceX < -minSwipeDistance; // 向左滑動（負值）
    const isVerticalSwipe = Math.abs(distanceY) > Math.abs(distanceX);

    // 重置拖拽狀態
    setIsDragging(false);
    setDragOffset(0);

    // 如果是垂直滑動，不處理
    if (isVerticalSwipe) return;

    const currentIndex = panelOrder.indexOf(activePanel);
    
    if (isLeftSwipe && currentIndex < panelOrder.length - 1) {
      // 向左滑動，切換到下一個面板
      setActivePanel(panelOrder[currentIndex + 1]);
    } else if (isRightSwipe && currentIndex > 0) {
      // 向右滑動，切換到上一個面板
      setActivePanel(panelOrder[currentIndex - 1]);
    }
  }, [isMobile, touchStart, touchEnd, activePanel, minSwipeDistance, panelOrder]);

  // 處理導航項目點擊
  const handleNavigationClick = (item: NavigationItem) => {
    setActivePanel(item.id as ActivePanel);
  };

  // Panel resize handlers
  const handleLeftPanelResize = (newWidth: number) => {
    setUI({ leftPanelWidth: newWidth });
  };
  
  const handleRightPanelResize = (newWidth: number) => {
    setUI({ rightPanelWidth: newWidth });
  };

  // Reference info modal handlers
  const handleOpenInfoModal = () => {
    setUI({ isPDFModalOpen: true });
  };
  
  const handleCloseInfoModal = () => {
    setUI({ isPDFModalOpen: false });
  };

  // Reference click handler
  const handleReferenceClick = (sentence: ProcessedSentence) => {
    setHighlightedSentence(sentence);
    handleOpenInfoModal();
  };

  // 工具函數
  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'OD': return '操作型定義';
      case 'CD': return '概念型定義';
      default: return '其他';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'OD': return 'bg-blue-100 text-blue-800';
      case 'CD': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getFileName = (fileId?: string) => {
    if (!fileId) return '未知檔案';
    const file = files.find(f => f.id === fileId);
    return file?.name || '未知檔案';
  };

  // 獲取當前面板索引
  const getCurrentPanelIndex = () => {
    return panelOrder.indexOf(activePanel);
  };

  // 渲染移動版面板容器
  const renderMobilePanelContainer = () => {
    const currentIndex = getCurrentPanelIndex();
    // 簡化邏輯：每個面板移動 100vw（視窗寬度）
    // 由於容器寬度是 300vw，每個面板寬度是 100vw
    const baseTranslateX = -currentIndex * 100; // 每個面板移動 100vw
    const finalTranslateX = baseTranslateX + dragOffset; // 加上拖拽偏移量
    
    // 根據是否正在拖拽來決定動畫
    const transitionClass = isDragging ? '' : 'transition-transform duration-300 ease-out';
    
    // 調試信息（開發環境）
    if (process.env.NODE_ENV === 'development' && isDragging) {
      console.log(`Panel: ${activePanel}, Index: ${currentIndex}, Base: ${baseTranslateX}vw, Offset: ${dragOffset}vw, Final: ${finalTranslateX}vw`);
    }

    return (
      <div 
        className={`flex h-full ${transitionClass}`}
        style={{ 
          transform: `translateX(${finalTranslateX}vw)`, // 使用 vw 單位更精確
          width: '300vw' // 三個面板的總寬度，每個 100vw
        }}
      >
        {/* Files Panel */}
        <div className="h-full flex-shrink-0 overflow-hidden bg-white" style={{ width: '100vw' }}>
          <div className="h-full w-full">
            <LeftPanel onResize={handleLeftPanelResize} />
          </div>
        </div>
        
        {/* Chat Panel */}
        <div className="h-full flex-shrink-0 overflow-hidden bg-white" style={{ width: '100vw' }}>
          <div className="h-full w-full">
            <CenterPanel onReferenceClick={handleReferenceClick} />
          </div>
        </div>
        
        {/* Progress Panel */}
        <div className="h-full flex-shrink-0 overflow-hidden bg-white" style={{ width: '100vw' }}>
          <div className="h-full w-full">
            <RightPanel onResize={handleRightPanelResize} />
          </div>
        </div>
      </div>
    );
  };

  // 渲染面板指示器
  const renderPanelIndicator = () => {
    if (!isMobile) return null;

    // 當在聊天面板時，調整指示器位置避免遮擋輸入框
    const isInChatPanel = activePanel === 'chat';
    const bottomPosition = isInChatPanel ? 'bottom-28' : 'bottom-4';

    return (
      <div className={`fixed ${bottomPosition} left-1/2 transform -translate-x-1/2 z-40`}>
        <div className="flex space-x-2 bg-white bg-opacity-90 backdrop-blur-sm rounded-full px-4 py-2 shadow-lg">
          {panelOrder.map((panelId) => {
            const item = navigationItems.find(item => item.id === panelId);
            const isActive = activePanel === panelId;
            return (
              <button
                key={panelId}
                onClick={() => setActivePanel(panelId)}
                className={`w-3 h-3 rounded-full transition-all duration-200 ${
                  isActive ? 'bg-blue-500' : 'bg-gray-300'
                }`}
                aria-label={`切換到${item?.label}`}
              />
            );
          })}
        </div>
        
        {/* 滑動提示 - 只在非聊天面板顯示，避免干擾 */}
        {!isInChatPanel && (
          <div className="mt-2 text-center">
            <p className="text-xs text-gray-500">
              左右滑動切換面板
            </p>
          </div>
        )}
      </div>
    );
  };

  // 桌面版佈局
  if (isDesktop) {
    return (
      <div className="flex flex-col h-screen bg-gray-100">
        <ResponsiveNavigation 
          items={navigationItems}
          onItemClick={handleNavigationClick}
          currentPanel={activePanel}
        />
        
        <div className="flex flex-1 overflow-hidden">
          {/* Left Panel - File Management */}
          <div 
            className="h-full bg-white shadow-sm" 
            style={{ width: `${ui.leftPanelWidth}px` }}
          >
            <LeftPanel onResize={handleLeftPanelResize} />
          </div>
          
          {/* Center Panel - Chat */}
          <div className="flex-1 h-full flex flex-col">
            <CenterPanel onReferenceClick={handleReferenceClick} />
          </div>
          
          {/* Right Panel - References Details */}
          <div 
            className="h-full bg-white shadow-sm" 
            style={{ width: `${ui.rightPanelWidth}px` }}
          >
            <RightPanel onResize={handleRightPanelResize} />
          </div>
        </div>

        <WelcomeTour activePanel={activePanel} />
        {renderModal()}
      </div>
    );
  }

  // 平板版佈局
  if (isTablet) {
    return (
      <div className="flex flex-col h-screen bg-gray-100">
        <ResponsiveNavigation 
          items={navigationItems}
          onItemClick={handleNavigationClick}
          currentPanel={activePanel}
        />
        
        <div className="flex flex-1 overflow-hidden pt-16">
          {/* 主要內容區域 */}
          <div className="flex-1 h-full flex">
            {/* 左側內容 */}
            <div className="flex-1 h-full flex flex-col pl-16">
              {activePanel === 'files' && <LeftPanel onResize={handleLeftPanelResize} />}
              {activePanel === 'chat' && <CenterPanel onReferenceClick={handleReferenceClick} />}
              {activePanel === 'progress' && <RightPanel onResize={handleRightPanelResize} />}
            </div>
            
            {/* 右側可能的輔助面板 */}
            {activePanel === 'chat' && (
              <div className="w-80 h-full bg-white shadow-sm border-l">
                <RightPanel onResize={handleRightPanelResize} />
              </div>
            )}
          </div>
        </div>

        <WelcomeTour activePanel={activePanel} />
        {renderModal()}
      </div>
    );
  }

  // 移動版佈局
  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <ResponsiveNavigation 
        items={navigationItems}
        onItemClick={handleNavigationClick}
        currentPanel={activePanel}
      />
      
      {/* 主要內容區域 */}
      <div 
        ref={mainContentRef}
        className="flex-1 pt-16 overflow-hidden relative"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        style={{ 
          touchAction: 'pan-y', // 只允許垂直滾動，防止瀏覽器默認的水平滑動行為
          overscrollBehavior: 'none' // 防止過度滾動
        }}
      >
        <div className="h-full bg-white overflow-hidden relative">
          {renderMobilePanelContainer()}
        </div>
        
        {/* 面板指示器和滑動提示 */}
        {renderPanelIndicator()}
      </div>

      <WelcomeTour activePanel={activePanel} />
      {renderModal()}
    </div>
  );

  // Modal 渲染函數
  function renderModal() {
    return highlightedSentence && (
      <Modal 
        isOpen={ui.isPDFModalOpen} 
        onClose={handleCloseInfoModal}
        title="文件資訊"
        size="lg"
      >
        <div className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <p className="text-sm font-medium text-gray-500">檔案名稱</p>
              <p className="mt-1 break-words">{getFileName(highlightedSentence.fileId)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">頁碼</p>
              <p className="mt-1">{typeof highlightedSentence.pageNumber === 'number' ? highlightedSentence.pageNumber : '未知'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">類型</p>
              <p className="mt-1">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(highlightedSentence.type)}`}>
                  {getTypeLabel(highlightedSentence.type)}
                </span>
              </p>
            </div>
          </div>
          
          <div className="mb-4">
            <p className="text-sm font-medium text-gray-500">句子內容</p>
            <p className="mt-1 p-3 bg-gray-50 rounded-md break-words">{highlightedSentence.content}</p>
          </div>
          
          {highlightedSentence.reason && (
            <div>
              <p className="text-sm font-medium text-gray-500">分類原因</p>
              <p className="mt-1 p-3 bg-gray-50 rounded-md italic break-words">{highlightedSentence.reason}</p>
            </div>
          )}
        </div>
      </Modal>
    );
  }
};

export default ResponsiveMainLayout; 