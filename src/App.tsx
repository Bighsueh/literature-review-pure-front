import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useEffect, useState } from 'react';
import ResponsiveMainLayout from './components/ResponsiveMainLayout';
import WorkspaceSelector from './components/workspace/WorkspaceSelector';
import WorkspaceSwitcher from './components/workspace/WorkspaceSwitcher';
import ErrorBoundary from './components/common/ErrorBoundary';
import { TokenManager, workspaceApiService } from './services/workspace_api_service';
import { WorkspaceProvider, useWorkspaceContext } from './contexts/WorkspaceContext';
import { useWorkspaceStore } from './stores/workspace';
import { useResponsive } from './hooks/useResponsive';
import { User, UserWithWorkspaces } from './types/api';
import './index.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (updated from cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// 簡化的認證上下文 (工作區管理移到 WorkspaceProvider)
interface AuthContextType {
  user: User;
  onLogout: () => Promise<void>;
}

export const AuthContext = React.createContext<AuthContextType | null>(null);

// 自定義 Hook
export const useAuth = (): AuthContextType => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an authenticated context');
  }
  return context;
};

// 登入頁面組件
const LoginPage: React.FC<{ onLogin: () => void; error?: string }> = ({ onLogin, error }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="max-w-md w-full space-y-8 p-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">登入您的帳戶</h2>
        <p className="text-gray-600 mb-8">使用 Google 帳戶快速登入</p>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <button
          onClick={onLogin}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          <span>使用 Google 登入</span>
        </button>
      </div>
    </div>
  </div>
);

// 載入組件
const LoadingScreen: React.FC<{ message?: string }> = ({ message = '載入中...' }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">{message}</p>
    </div>
  </div>
);

// 認證狀態
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

// 工作區感知佈局組件
const WorkspaceAwareLayout: React.FC = () => {
  const { hasValidWorkspace, currentWorkspace } = useWorkspaceContext();
  const { isDesktop, isMobile } = useResponsive();
  
  // 如果沒有有效的工作區，顯示工作區選擇器
  if (!hasValidWorkspace) {
    return <WorkspaceSelector />;
  }
  
  // 渲染工作區頂部導航欄
  const renderWorkspaceHeader = () => {
    if (!currentWorkspace) return null;

    return (
      <div className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* 左側：應用標題和工作區切換器 */}
          <div className="flex items-center space-x-4">
            {isDesktop && (
              <h1 className="text-xl font-semibold text-gray-900">
                個人化研究助手
              </h1>
            )}
            <div className="flex items-center">
              <WorkspaceSwitcher 
                className={isDesktop ? "min-w-48" : ""}
                compact={isMobile}
                showUserInfo={!isMobile}
              />
            </div>
          </div>

          {/* 右側：工作區資訊和快捷操作 */}
          <div className="flex items-center space-x-3">
            {/* 工作區狀態指示器 */}
            {isDesktop && (
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>已連線</span>
                </div>
                <span>•</span>
                <span>{currentWorkspace.name}</span>
              </div>
            )}
            
            {/* 快捷操作按鈕 */}
            {!isMobile && (
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
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };
  
  // 有有效工作區，顯示主應用界面
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
};

// 主應用組件（已認證狀態）
const AuthenticatedApp: React.FC<{ user: User; onLogout: () => Promise<void> }> = ({ 
  user, 
  onLogout 
}) => {
  return (
    <WorkspaceProvider>
      <AuthContext.Provider value={{
        user,
        onLogout
      }}>
        <WorkspaceAwareLayout />
      </AuthContext.Provider>
    </WorkspaceProvider>
  );
};

function App() {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
    error: null
  });

  useEffect(() => {
    checkAuthStatus();
    handleOAuthCallback();
  }, []);

  const checkAuthStatus = async () => {
    try {
      if (!TokenManager.isAuthenticated()) {
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
          error: null
        });
        return;
      }

      const response = await workspaceApiService.getCurrentUser();
      
      if (response.success && response.data) {
        const userData = response.data as UserWithWorkspaces;
        
        setAuthState({
          isAuthenticated: true,
          user: userData,
          isLoading: false,
          error: null
        });

        // 初始化工作區狀態管理
        const workspaceStore = useWorkspaceStore.getState();
        
        // 設定用戶和工作區
        workspaceStore.setCurrentUser(userData);
        workspaceStore.setWorkspaces(userData.workspaces || []);
        
        // 恢復或設定當前工作區
        const savedWorkspaceId = workspaceApiService.getCurrentWorkspaceId();
        if (savedWorkspaceId && userData.workspaces?.some(w => w.id === savedWorkspaceId)) {
          workspaceStore.setCurrentWorkspace(savedWorkspaceId);
        } else if (userData.workspaces?.length > 0) {
          const firstWorkspace = userData.workspaces[0];
          workspaceStore.setCurrentWorkspace(firstWorkspace.id);
        }
      } else {
        TokenManager.clearAuth();
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
          error: response.error || 'Authentication failed'
        });
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      TokenManager.clearAuth();
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Authentication error'
      });
    }
  };

  const handleOAuthCallback = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    const userParam = urlParams.get('user');
    
    if (token && userParam) {
      try {
        const user = JSON.parse(decodeURIComponent(userParam));
        TokenManager.setToken(token);
        TokenManager.setCurrentUser(user);
        
        // 清除 URL 參數
        window.history.replaceState({}, document.title, window.location.pathname);
        
        // 重新檢查認證狀態
        checkAuthStatus();
      } catch (error) {
        console.error('Failed to parse OAuth callback:', error);
        setAuthState(prev => ({
          ...prev,
          isLoading: false,
          error: 'Failed to complete login'
        }));
      }
    }
  };

  const handleLogin = () => {
    workspaceApiService.googleLogin();
  };

  const handleLogout = async () => {
    try {
      await workspaceApiService.logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      TokenManager.clearAuth();
      workspaceApiService.clearCurrentWorkspace();
      
      // 清理工作區狀態
      const workspaceStore = useWorkspaceStore.getState();
      workspaceStore.clearWorkspaceData();
      
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
        error: null
      });
    }
  };

  if (authState.isLoading) {
    return <LoadingScreen message="檢查登入狀態中..." />;
  }

  if (!authState.isAuthenticated) {
    return (
      <ErrorBoundary>
        <LoginPage onLogin={handleLogin} error={authState.error || undefined} />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthenticatedApp 
          user={authState.user!} 
          onLogout={handleLogout}
        />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
