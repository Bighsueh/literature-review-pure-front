import React, { useState } from 'react';
import { useResponsive } from '../../hooks/useResponsive';
import { 
  DevicePhoneMobileIcon,
  DeviceTabletIcon,
  ComputerDesktopIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline';



const RWDTestComponent: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  
  const responsive = useResponsive();
  const { 
    width, 
    height, 
    breakpoint, 
    isMobile, 
    isTablet, 
    isDesktop, 
    orientation,
    matches,
    matchesMinWidth,
    matchesMaxWidth
  } = responsive;

  if (!isVisible) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => setIsVisible(true)}
          className="bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
          title="顯示 RWD 測試面板"
        >
          <EyeIcon className="h-5 w-5" />
        </button>
      </div>
    );
  }

  const getBreakpointIcon = () => {
    if (isMobile) return <DevicePhoneMobileIcon className="h-5 w-5" />;
    if (isTablet) return <DeviceTabletIcon className="h-5 w-5" />;
    if (isDesktop) return <ComputerDesktopIcon className="h-5 w-5" />;
    return <ComputerDesktopIcon className="h-5 w-5" />;
  };

  const getBreakpointColor = () => {
    if (isMobile) return 'bg-red-500';
    if (isTablet) return 'bg-yellow-500';
    if (isDesktop) return 'bg-green-500';
    return 'bg-gray-500';
  };

  const getBreakpointText = () => {
    if (isMobile) return 'Mobile';
    if (isTablet) return 'Tablet';
    if (isDesktop) return 'Desktop';
    return 'Unknown';
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-4 max-w-sm">
        {/* 標題列 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${getBreakpointColor()}`} />
            <h3 className="text-sm font-semibold text-gray-800">RWD 測試</h3>
          </div>
          <button
            onClick={() => setIsVisible(false)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            title="隱藏面板"
          >
            <EyeSlashIcon className="h-5 w-5" />
          </button>
        </div>

        {/* 基本資訊 */}
        <div className="space-y-3">
          {/* 斷點資訊 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {getBreakpointIcon()}
              <span className="text-sm font-medium text-gray-700">
                {getBreakpointText()}
              </span>
            </div>
            <span className="text-xs text-gray-500">
              {breakpoint}
            </span>
          </div>

          {/* 尺寸資訊 */}
          <div className="bg-gray-50 rounded-md p-3">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-500">寬度:</span>
                <span className="ml-1 font-mono text-gray-800">{width}px</span>
              </div>
              <div>
                <span className="text-gray-500">高度:</span>
                <span className="ml-1 font-mono text-gray-800">{height}px</span>
              </div>
              <div>
                <span className="text-gray-500">方向:</span>
                <span className="ml-1 font-mono text-gray-800">{orientation}</span>
              </div>
              <div>
                <span className="text-gray-500">比例:</span>
                <span className="ml-1 font-mono text-gray-800">
                  {(width / height).toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          {/* 斷點狀態 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">斷點狀態:</span>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-blue-600 hover:text-blue-700 transition-colors"
              >
                {showDetails ? '隱藏' : '詳細'}
              </button>
            </div>
            
            <div className="grid grid-cols-3 gap-1 text-xs">
              <div className={`p-2 rounded text-center ${
                isMobile ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
              }`}>
                Mobile
              </div>
              <div className={`p-2 rounded text-center ${
                isTablet ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'
              }`}>
                Tablet
              </div>
              <div className={`p-2 rounded text-center ${
                isDesktop ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
              }`}>
                Desktop
              </div>
            </div>
          </div>

          {/* 詳細資訊 */}
          {showDetails && (
            <div className="bg-blue-50 rounded-md p-3 space-y-2">
              <h4 className="text-xs font-semibold text-blue-800">測試功能</h4>
              
              {/* 媒體查詢測試 */}
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600">matches(['mobile']):</span>
                  <span className={matches(['mobile']) ? 'text-green-600' : 'text-red-600'}>
                    {matches(['mobile']).toString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">matchesMinWidth(768):</span>
                  <span className={matchesMinWidth(768) ? 'text-green-600' : 'text-red-600'}>
                    {matchesMinWidth(768).toString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">matchesMaxWidth(1024):</span>
                  <span className={matchesMaxWidth(1024) ? 'text-green-600' : 'text-red-600'}>
                    {matchesMaxWidth(1024).toString()}
                  </span>
                </div>
              </div>

              {/* Tailwind 類別建議 */}
              <div className="space-y-1">
                <h5 className="text-xs font-medium text-blue-700">Tailwind 類別建議:</h5>
                <div className="text-xs text-gray-600 space-y-1">
                  {isMobile && (
                    <div className="bg-white p-2 rounded border">
                      <code className="text-blue-600">
                        {`block sm:hidden, text-sm, p-4, flex-col`}
                      </code>
                    </div>
                  )}
                  {isTablet && (
                    <div className="bg-white p-2 rounded border">
                      <code className="text-blue-600">
                        {`hidden sm:block lg:hidden, text-base, p-6, flex-row`}
                      </code>
                    </div>
                  )}
                  {isDesktop && (
                    <div className="bg-white p-2 rounded border">
                      <code className="text-blue-600">
                        {`hidden lg:block, text-lg, p-8, grid-cols-3`}
                      </code>
                    </div>
                  )}
                </div>
              </div>

              {/* 效能提示 */}
              <div className="space-y-1">
                <h5 className="text-xs font-medium text-blue-700">效能提示:</h5>
                <div className="text-xs text-gray-600 space-y-1">
                  {isMobile && (
                    <div className="flex items-center space-x-1">
                      <div className="w-2 h-2 bg-orange-400 rounded-full"></div>
                      <span>考慮延遲載入非關鍵內容</span>
                    </div>
                  )}
                  {width < 400 && (
                    <div className="flex items-center space-x-1">
                      <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                      <span>極小螢幕，簡化 UI</span>
                    </div>
                  )}
                  {orientation === 'landscape' && isMobile && (
                    <div className="flex items-center space-x-1">
                      <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                      <span>橫向模式，調整佈局</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 快速測試按鈕 */}
          <div className="flex space-x-2">
            <button
              onClick={() => window.dispatchEvent(new Event('resize'))}
              className="flex-1 bg-blue-600 text-white text-xs px-3 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              重新檢測
            </button>
            <button
              onClick={() => {
                console.log('RWD State:', responsive);
                alert('RWD 狀態已輸出到控制台');
              }}
              className="flex-1 bg-gray-600 text-white text-xs px-3 py-2 rounded hover:bg-gray-700 transition-colors"
            >
              輸出狀態
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// 響應式展示卡片元件
export const ResponsiveShowcase: React.FC = () => {
  const { isMobile, isTablet, isDesktop } = useResponsive();

  return (
    <div className="space-y-6">
      {/* 響應式網格展示 */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">響應式網格展示</h2>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }, (_, i) => (
            <div
              key={i}
              className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200"
            >
              <div className="text-sm font-medium text-blue-900">
                卡片 {i + 1}
              </div>
              <div className="text-xs text-blue-600 mt-1">
                {isMobile && 'Mobile View'}
                {isTablet && 'Tablet View'}
                {isDesktop && 'Desktop View'}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 響應式文字展示 */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">響應式文字展示</h2>
        
        <div className="space-y-4">
          <h3 className="text-sm sm:text-base lg:text-lg xl:text-xl font-medium text-gray-800">
            這是響應式標題文字
          </h3>
          
          <p className="text-xs sm:text-sm lg:text-base text-gray-600 leading-relaxed">
            這是響應式段落文字。在不同螢幕尺寸下，文字大小和行距會自動調整，以提供最佳的閱讀體驗。
            移動裝置上文字較小且緊湊，桌面版本則更大更舒適。
          </p>
          
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
            <button className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm sm:text-base hover:bg-blue-700 transition-colors">
              主要按鈕
            </button>
            <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm sm:text-base hover:bg-gray-300 transition-colors">
              次要按鈕
            </button>
          </div>
        </div>
      </section>

      {/* 響應式間距展示 */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4 lg:p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2 sm:mb-3 lg:mb-4">響應式間距展示</h2>
        
        <div className="space-y-2 sm:space-y-3 lg:space-y-4">
          <div className="bg-gray-50 p-2 sm:p-3 lg:p-4 rounded-md">
            <p className="text-sm text-gray-700">
              這個區塊的內距 (padding) 在不同螢幕尺寸下會自動調整
            </p>
          </div>
          
          <div className="bg-gray-50 p-2 sm:p-3 lg:p-4 rounded-md">
            <p className="text-sm text-gray-700">
              區塊之間的間距 (margin) 也會響應式調整
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default RWDTestComponent; 