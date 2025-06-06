import React, { useState } from 'react';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import { errorHandler } from '../../services/error_handler';

interface RetryButtonProps {
  onRetry: () => Promise<void> | void;
  disabled?: boolean;
  className?: string;
  children?: React.ReactNode;
  maxRetries?: number;
  showRetryCount?: boolean;
}

const RetryButton: React.FC<RetryButtonProps> = ({
  onRetry,
  disabled = false,
  className = '',
  children = '重試',
  maxRetries = 3,
  showRetryCount = true
}) => {
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const handleRetry = async () => {
    if (isRetrying || disabled || retryCount >= maxRetries) {
      return;
    }

    setIsRetrying(true);
    
    try {
      await errorHandler.retry(async () => {
        await onRetry();
      }, {
        component: 'RetryButton',
        retryCount: retryCount + 1
      });
      
      // 成功後重置計數
      setRetryCount(0);
    } catch (error) {
      setRetryCount(prev => prev + 1);
      console.error('重試失敗:', error);
    } finally {
      setIsRetrying(false);
    }
  };

  const isMaxRetriesReached = retryCount >= maxRetries;
  const buttonDisabled = disabled || isRetrying || isMaxRetriesReached;

  return (
    <button
      onClick={handleRetry}
      disabled={buttonDisabled}
      className={`
        inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md
        transition-colors duration-200
        ${buttonDisabled 
          ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
          : 'bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
        }
        ${className}
      `}
    >
      <ArrowPathIcon 
        className={`h-4 w-4 mr-2 ${isRetrying ? 'animate-spin' : ''}`} 
      />
      {isRetrying ? '重試中...' : children}
      {showRetryCount && retryCount > 0 && (
        <span className="ml-2 text-xs opacity-75">
          ({retryCount}/{maxRetries})
        </span>
      )}
    </button>
  );
};

export default RetryButton; 