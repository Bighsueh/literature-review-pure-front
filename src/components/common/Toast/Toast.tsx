import React, { Fragment, useEffect } from 'react';
import { Transition } from '@headlessui/react';
import { 
  CheckCircleIcon, 
  ExclamationCircleIcon, 
  InformationCircleIcon, 
  XMarkIcon 
} from '@heroicons/react/24/outline';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastProps {
  show: boolean;
  type: ToastType;
  message: string;
  duration?: number;
  onClose: () => void;
}

const Toast: React.FC<ToastProps> = ({
  show,
  type,
  message,
  duration = 3000,
  onClose
}) => {
  // Auto-close after duration
  useEffect(() => {
    if (show && duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [show, duration, onClose]);
  
  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircleIcon className="h-6 w-6 text-green-500" />;
      case 'error':
        return <ExclamationCircleIcon className="h-6 w-6 text-red-500" />;
      case 'warning':
        return <ExclamationCircleIcon className="h-6 w-6 text-yellow-500" />;
      case 'info':
      default:
        return <InformationCircleIcon className="h-6 w-6 text-blue-500" />;
    }
  };
  
  const getBgColor = () => {
    switch (type) {
      case 'success': return 'bg-green-50';
      case 'error': return 'bg-red-50';
      case 'warning': return 'bg-yellow-50';
      case 'info': return 'bg-blue-50';
      default: return 'bg-gray-50';
    }
  };
  
  const getBorderColor = () => {
    switch (type) {
      case 'success': return 'border-green-200';
      case 'error': return 'border-red-200';
      case 'warning': return 'border-yellow-200';
      case 'info': return 'border-blue-200';
      default: return 'border-gray-200';
    }
  };

  return (
    <div className="fixed top-4 right-4 flex items-end justify-center px-4 py-6 pointer-events-none sm:p-6 z-50">
      <Transition
        show={show}
        as={Fragment}
        enter="transform ease-out duration-300 transition"
        enterFrom="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
        enterTo="translate-y-0 opacity-100 sm:translate-x-0"
        leave="transition ease-in duration-100"
        leaveFrom="opacity-100"
        leaveTo="opacity-0"
      >
        <div className={`max-w-sm w-full ${getBgColor()} shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden border ${getBorderColor()}`}>
          <div className="p-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                {getIcon()}
              </div>
              <div className="ml-3 w-0 flex-1 pt-0.5">
                <p className="text-sm font-medium text-gray-900">
                  {message}
                </p>
              </div>
              <div className="ml-4 flex-shrink-0 flex">
                <button
                  className="bg-transparent rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  onClick={onClose}
                >
                  <span className="sr-only">Close</span>
                  <XMarkIcon className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  );
};

export default Toast;
