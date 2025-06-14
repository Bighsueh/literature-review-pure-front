import React, { useState, useRef, useEffect } from 'react';
import { useResponsive } from '../../hooks/useResponsive';
import { 
  Bars3Icon, 
  XMarkIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

export interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active?: boolean;
  onClick?: () => void;
  badge?: string | number;
}

interface ResponsiveNavigationProps {
  items: NavigationItem[];
  onItemClick?: (item: NavigationItem) => void;
  title?: string;
  currentPanel?: string;
}

const ResponsiveNavigation: React.FC<ResponsiveNavigationProps> = ({
  items,
  onItemClick,
  title = "論文分析系統",
  currentPanel
}) => {
  const { isMobile, isTablet } = useResponsive();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isTabletSidebarCollapsed, setIsTabletSidebarCollapsed] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // 關閉移動選單
  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  // 處理項目點擊
  const handleItemClick = (item: NavigationItem) => {
    item.onClick?.();
    onItemClick?.(item);
    
    // 移動裝置點擊後關閉選單
    if (isMobile) {
      closeMobileMenu();
    }
  };

  // 點擊外部關閉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        isMobileMenuOpen &&
        sidebarRef.current &&
        !sidebarRef.current.contains(event.target as Node) &&
        overlayRef.current &&
        overlayRef.current.contains(event.target as Node)
      ) {
        closeMobileMenu();
      }
    };

    if (isMobile && isMobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'hidden'; // 防止背景滾動
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'unset';
    };
  }, [isMobile, isMobileMenuOpen]);

  // ESC 鍵關閉選單
  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isMobileMenuOpen) {
        closeMobileMenu();
      }
    };

    document.addEventListener('keydown', handleEscapeKey);
    return () => document.removeEventListener('keydown', handleEscapeKey);
  }, [isMobileMenuOpen]);

  // 渲染導航項目
  const renderNavigationItem = (item: NavigationItem, isSidebar = false) => {
    const Icon = item.icon;
    const isActive = item.active;
    
    return (
      <button
        key={item.id}
        onClick={() => handleItemClick(item)}
        className={`
          ${isSidebar ? 'w-full justify-start px-4 py-3' : 'px-3 py-2'} 
          flex items-center space-x-3 rounded-lg text-sm font-medium transition-all duration-200 
          ${isActive 
            ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          }
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50
          min-h-[44px] touch-manipulation
        `}
        aria-current={isActive ? 'page' : undefined}
      >
        <Icon className={`${isSidebar ? 'h-5 w-5' : 'h-4 w-4'} flex-shrink-0`} />
        <span className={isSidebar || !isMobile ? 'block' : 'sr-only'}>
          {item.label}
        </span>
        {item.badge && (
          <span className={`
            ml-auto px-2 py-1 text-xs font-medium rounded-full
            ${isActive 
              ? 'bg-blue-100 text-blue-600' 
              : 'bg-gray-100 text-gray-600'
            }
          `}>
            {item.badge}
          </span>
        )}
      </button>
    );
  };

  // 獲取當前面板名稱
  const getCurrentPanelName = () => {
    const currentItem = items.find(item => item.id === currentPanel);
    return currentItem?.label || title;
  };

  // 桌面版不需要導航列，直接返回 null
  if (!isMobile && !isTablet) {
    return null;
  }

  // 平板版側邊欄
  if (isTablet) {
    return (
      <>
        {/* 頂部導航列 */}
        <nav className="bg-white border-b border-gray-200 fixed top-0 left-0 right-0 z-30">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setIsTabletSidebarCollapsed(!isTabletSidebarCollapsed)}
                  className="p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[44px] min-w-[44px]"
                  aria-label={isTabletSidebarCollapsed ? '展開側邊欄' : '收合側邊欄'}
                >
                  <Bars3Icon className="h-5 w-5" />
                </button>
                <h1 className="text-lg font-semibold text-gray-900">{getCurrentPanelName()}</h1>
              </div>
            </div>
          </div>
        </nav>

        {/* 側邊欄 */}
        <aside 
          className={`
            fixed top-16 left-0 bottom-0 z-20 bg-white border-r border-gray-200 transition-all duration-300
            ${isTabletSidebarCollapsed ? 'w-16' : 'w-64'}
          `}
        >
          <nav className="h-full px-3 py-4 overflow-y-auto">
            <div className="space-y-2">
              {items.map(item => (
                <div key={item.id} className="relative group">
                  {renderNavigationItem(item, !isTabletSidebarCollapsed)}
                  {isTabletSidebarCollapsed && (
                    <div className="absolute left-full top-0 ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                      {item.label}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </nav>
        </aside>
      </>
    );
  }

  // 移動版導航
  return (
    <>
      {/* 頂部導航列 */}
      <nav className="bg-white border-b border-gray-200 fixed top-0 left-0 right-0 z-50">
        <div className="px-4">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-lg font-semibold text-gray-900 truncate">{getCurrentPanelName()}</h1>
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[44px] min-w-[44px]"
              aria-label="開啟選單"
            >
              <Bars3Icon className="h-6 w-6" />
            </button>
          </div>
        </div>
      </nav>

      {/* 移動版側邊抽屜 */}
      {isMobileMenuOpen && (
        <div 
          ref={overlayRef}
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-labelledby="mobile-menu-title"
        >
          {/* 背景遮罩 */}
          <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity duration-300" />
          
          {/* 側邊欄 */}
          <div 
            ref={sidebarRef}
            className={`
              fixed top-0 right-0 bottom-0 w-80 max-w-[85vw] bg-white shadow-xl 
              transform transition-transform duration-300 ease-in-out
              ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full'}
            `}
          >
            {/* 標題列 */}
            <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200">
              <h2 id="mobile-menu-title" className="text-lg font-semibold text-gray-900">
                {title}
              </h2>
              <button
                onClick={closeMobileMenu}
                className="p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[44px] min-w-[44px]"
                aria-label="關閉選單"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            {/* 導航項目 */}
            <nav className="px-4 py-4">
              <div className="space-y-2">
                {items.map(item => renderNavigationItem(item, true))}
              </div>
            </nav>
          </div>
        </div>
      )}
    </>
  );
};

// 預設導航項目
export const defaultNavigationItems: NavigationItem[] = [
  {
    id: 'files',
    label: '檔案管理',
    icon: DocumentTextIcon,
    active: false,
  },
  {
    id: 'chat',
    label: '查詢助手',
    icon: ChatBubbleLeftRightIcon,
    active: true,
  },
  {
    id: 'progress',
    label: '引用詳情',
    icon: ChartBarIcon,
    active: false,
  },
];

export default ResponsiveNavigation; 