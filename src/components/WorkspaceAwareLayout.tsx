/**
 * 工作區感知主佈局組件 - FE-03 工作區管理界面開發
 * 整合工作區導航和主要內容佈局
 */

import React from 'react';
import { useResponsive } from '../hooks/useResponsive';
import { useWorkspaceContext } from '../contexts/WorkspaceContext';
import ResponsiveMainLayout from './ResponsiveMainLayout';
import WorkspaceSwitcher from './workspace/WorkspaceSwitcher';

const WorkspaceAwareLayout: React.FC = () => {
  const { isDesktop, isTablet, isMobile } = useResponsive();
  const { currentWorkspace } = useWorkspaceContext();

  // 渲染工作區頂部導航欄
  const renderWorkspaceHeader = () => {
    if (!currentWorkspace) return null;

    return (
      <div className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* 左側：應用標題和工作區切換器 */}
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold text-gray-900 hidden sm:block">
              個人化研究助手
            </h1>
            <div className="flex items-center">
              <WorkspaceSwitcher 
                className="min-w-48"
                compact={isMobile}
                showUserInfo={!isMobile}
              />
            </div>
          </div>

          {/* 右側：工作區資訊和快捷操作 */}
          <div className="flex items-center space-x-3">
            {/* 工作區狀態指示器 */}
            <div className="hidden md:flex items-center space-x-2 text-sm text-gray-500">
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>已連線</span>
              </div>
              <span>•</span>
              <span>{currentWorkspace.name}</span>
            </div>
            
            {/* 快捷操作按鈕 */}
            <div className="flex items-center space-x-1">
              {/* 工作區設定按鈕 */}
              <button
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                title="工作區設定"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>

              {/* 通知按鈕 */}
              <button
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors relative"
                title="通知"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM4 19h5v-5H4v5zM13 7v6h6V7h-6zM4 12V7h5v5H4z" />
                </svg>
                {/* 通知紅點（示例） */}
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 桌面版佈局（增強版）
  if (isDesktop) {
    return (
      <div className="flex flex-col h-screen bg-gray-100">
        {/* 工作區頂部導航欄 */}
        {renderWorkspaceHeader()}
        
        {/* 主要內容區域 */}
        <div className="flex-1 overflow-hidden">
          <ResponsiveMainLayout />
        </div>
      </div>
    );
  }

  // 平板和移動版佈局（可選擇性添加工作區導航）
  if (isTablet) {
    return (
      <div className="flex flex-col h-screen bg-gray-100">
        {/* 工作區頂部導航欄（簡化版） */}
        <div className="bg-white border-b border-gray-200 px-4">
          <div className="flex items-center justify-between h-12">
            <WorkspaceSwitcher 
              className="flex-1 max-w-xs"
              compact={true}
              showUserInfo={false}
            />
            
            {/* 狀態指示器 */}
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="hidden sm:inline">在線</span>
            </div>
          </div>
        </div>
        
        {/* 主要內容 */}
        <div className="flex-1 overflow-hidden">
          <ResponsiveMainLayout />
        </div>
      </div>
    );
  }

  // 移動版佈局（最小化版）
  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* 簡化的工作區導航 */}
      <div className="bg-white border-b border-gray-200 px-3">
        <div className="flex items-center justify-between h-10">
          <WorkspaceSwitcher 
            className="flex-1"
            compact={true}
            showUserInfo={false}
          />
          
          {/* 狀態指示器 */}
          <div className="w-2 h-2 bg-green-500 rounded-full ml-3"></div>
        </div>
      </div>
      
      {/* 主要內容 */}
      <div className="flex-1 overflow-hidden">
        <ResponsiveMainLayout />
      </div>
    </div>
  );
};

export default WorkspaceAwareLayout; 