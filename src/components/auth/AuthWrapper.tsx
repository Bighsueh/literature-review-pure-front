/**
 * 身份驗證包裝組件 - FE-01 身份驗證系統整合
 * 負責檢查用戶登入狀態並提供路由保護
 */

import React, { useEffect, useState } from 'react';
import { TokenManager, workspaceApiService } from '../../services/workspace_api_service';
import { User, UserWithWorkspaces, Workspace } from '../../types/api';
import LoginPage from './LoginPage';
import LoadingSpinner from '../common/LoadingSpinner';

interface AuthWrapperProps {
  children: React.ReactNode;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  workspaces: Workspace[];
  isLoading: boolean;
  error: string | null;
}

export const AuthWrapper: React.FC<AuthWrapperProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    workspaces: [],
    isLoading: true,
    error: null
  });

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      // 檢查是否有 token
      if (!TokenManager.isAuthenticated()) {
        setAuthState({
          isAuthenticated: false,
          user: null,
          workspaces: [],
          isLoading: false,
          error: null
        });
        return;
      }

      // 驗證 token 並獲取用戶資訊
      const response = await workspaceApiService.getCurrentUser();
      
      if (response.success && response.data) {
        const userData = response.data as UserWithWorkspaces;
        
        setAuthState({
          isAuthenticated: true,
          user: userData,
          workspaces: userData.workspaces || [],
          isLoading: false,
          error: null
        });

        // 如果用戶有工作區但沒有選擇當前工作區，自動選擇第一個
        if (userData.workspaces?.length > 0 && !workspaceApiService.getCurrentWorkspaceId()) {
          workspaceApiService.setCurrentWorkspace(userData.workspaces[0].id);
        }
      } else {
        // Token 無效，清除認證狀態
        TokenManager.clearAuth();
        setAuthState({
          isAuthenticated: false,
          user: null,
          workspaces: [],
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
        workspaces: [],
        isLoading: false,
        error: error instanceof Error ? error.message : 'Authentication error'
      });
    }
  };

  const handleLogin = () => {
    workspaceApiService.googleLogin();
  };

  const handleLogout = async () => {
    try {
      await workspaceApiService.logout();
      setAuthState({
        isAuthenticated: false,
        user: null,
        workspaces: [],
        isLoading: false,
        error: null
      });
    } catch (error) {
      console.error('Logout failed:', error);
      // 即使登出失敗，也清除本地狀態
      TokenManager.clearAuth();
      setAuthState({
        isAuthenticated: false,
        user: null,
        workspaces: [],
        isLoading: false,
        error: null
      });
    }
  };

  // 處理 OAuth 回調
  useEffect(() => {
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

    handleOAuthCallback();
  }, []);

  if (authState.isLoading) {
    return <LoadingSpinner message="檢查登入狀態中..." />;
  }

  if (!authState.isAuthenticated) {
    return (
      <LoginPage 
        onLogin={handleLogin}
        error={authState.error}
      />
    );
  }

  // 提供認證上下文給子組件
  return (
    <AuthContext.Provider value={{
      user: authState.user!,
      workspaces: authState.workspaces,
      onLogout: handleLogout,
      refreshAuth: checkAuthStatus
    }}>
      {children}
    </AuthContext.Provider>
  );
};

// 認證上下文
interface AuthContextType {
  user: User;
  workspaces: Workspace[];
  onLogout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

export const AuthContext = React.createContext<AuthContextType | null>(null);

// 自定義 Hook 用於獲取認證上下文
export const useAuth = (): AuthContextType => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthWrapper');
  }
  return context;
};

export default AuthWrapper; 