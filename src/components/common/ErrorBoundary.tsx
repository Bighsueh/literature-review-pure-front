import React, { Component, ErrorInfo, ReactNode } from 'react';
import { errorHandler } from '../../services/error_handler';
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  retryCount: number;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, retry: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  maxRetries?: number;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private readonly maxRetries: number;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.maxRetries = props.maxRetries || 3;
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // 使用全域錯誤處理器處理錯誤
    errorHandler.handleError(error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
      retryCount: this.state.retryCount
    });

    this.setState({
      errorInfo
    });

    // 調用外部錯誤處理回調
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: prevState.retryCount + 1
      }));
    }
  };

  handleReload = (): void => {
    window.location.reload();
  };

  renderDefaultFallback(): ReactNode {
    const { error, retryCount } = this.state;
    const canRetry = retryCount < this.maxRetries;

    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center px-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-lg shadow-lg p-6 text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
              <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              應用程式發生錯誤
            </h3>
            
            <p className="text-sm text-gray-500 mb-6">
              很抱歉，應用程式遇到了一個意外錯誤。您可以嘗試重新載入頁面或聯繫技術支援。
            </p>

            {process.env.NODE_ENV === 'development' && error && (
              <div className="mb-6 p-3 bg-gray-100 rounded text-left">
                <p className="text-xs font-mono text-gray-700 break-all">
                  {error.message}
                </p>
              </div>
            )}

            <div className="flex flex-col space-y-3">
              {canRetry && (
                <button
                  onClick={this.handleRetry}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  重試 ({this.maxRetries - retryCount} 次機會)
                </button>
              )}
              
              <button
                onClick={this.handleReload}
                className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                重新載入頁面
              </button>
            </div>

            {retryCount > 0 && (
              <p className="mt-4 text-xs text-gray-400">
                已重試 {retryCount} 次
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // 如果提供了自定義 fallback，使用它
      if (this.props.fallback && this.state.error) {
        return this.props.fallback(this.state.error, this.handleRetry);
      }

      // 否則使用預設的錯誤 UI
      return this.renderDefaultFallback();
    }

    return this.props.children;
  }
}

// 高階組件版本
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
}

// Hook 版本（用於函數組件中的錯誤處理）
export function useErrorHandler() {
  const handleError = React.useCallback((error: Error, context?: Record<string, unknown>) => {
    errorHandler.handleError(error, context);
  }, []);

  const retry = React.useCallback((
    operation: () => Promise<unknown>,
    context?: Record<string, unknown>
  ): Promise<unknown> => {
    return errorHandler.retry(operation, context);
  }, []);

  return { handleError, retry };
}

export default ErrorBoundary; 