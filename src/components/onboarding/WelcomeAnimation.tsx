import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface WelcomeAnimationProps {
  onComplete?: () => void;
}

const WelcomeAnimation: React.FC<WelcomeAnimationProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  const steps = [
    {
      icon: '📚',
      title: '歡迎使用定義查詢助手',
      description: '智能學術論文定義查找系統',
      color: 'from-blue-400 to-blue-600'
    },
    {
      icon: '📄',
      title: '上傳 PDF 檔案',
      description: '支援學術論文的智能分析',
      color: 'from-green-400 to-green-600'
    },
    {
      icon: '🤖',
      title: 'AI 智能分析',
      description: '自動識別概念型與操作型定義',
      color: 'from-purple-400 to-purple-600'
    },
    {
      icon: '🔍',
      title: '精準查詢',
      description: '找到您需要的定義和解釋',
      color: 'from-orange-400 to-orange-600'
    }
  ];

  useEffect(() => {
    if (currentStep < steps.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStep(prev => prev + 1);
      }, 2000);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => {
          onComplete?.();
        }, 500);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [currentStep, steps.length, onComplete]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-gradient-to-br from-blue-50 via-sky-100 to-blue-200 flex items-center justify-center z-50"
        >
          {/* Background Pattern */}
          <div className="absolute inset-0 opacity-30">
            <div className="absolute inset-0" style={{
              backgroundImage: `radial-gradient(circle at 25% 25%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
                               radial-gradient(circle at 75% 75%, rgba(147, 197, 253, 0.1) 0%, transparent 50%)`
            }} />
          </div>

          <div className="relative z-10 text-center">
            {/* Main Container */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5 }}
              className="bg-white/80 backdrop-blur-lg rounded-3xl p-12 max-w-md mx-4 border border-blue-200/50 shadow-xl"
            >
              {/* Step Indicators */}
              <div className="flex justify-center space-x-2 mb-8">
                {steps.map((_, index) => (
                  <motion.div
                    key={index}
                    className={`h-2 rounded-full transition-all duration-300 ${
                      index <= currentStep ? 'bg-blue-500' : 'bg-blue-200'
                    }`}
                    style={{ width: index <= currentStep ? '24px' : '8px' }}
                  />
                ))}
              </div>

              {/* Content */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentStep}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -20, opacity: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  {/* Icon */}
                  <div className="text-6xl mb-6">
                    {steps[currentStep].icon}
                  </div>

                  {/* Title */}
                  <motion.h1
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="text-2xl font-bold text-gray-800 mb-4"
                  >
                    {steps[currentStep].title}
                  </motion.h1>

                  {/* Description */}
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="text-gray-600 text-lg"
                  >
                    {steps[currentStep].description}
                  </motion.p>
                </motion.div>
              </AnimatePresence>

              {/* Progress Ring */}
              <div className="mt-8 flex justify-center">
                <div className="relative w-12 h-12">
                  <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="rgba(59, 130, 246, 0.3)"
                      strokeWidth="3"
                    />
                    <motion.path
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      fill="none"
                      stroke="rgb(59, 130, 246)"
                      strokeWidth="3"
                      strokeLinecap="round"
                      initial={{ pathLength: 0 }}
                      animate={{ pathLength: (currentStep + 1) / steps.length }}
                      transition={{ duration: 0.5 }}
                      style={{
                        strokeDasharray: '100',
                        strokeDashoffset: 0
                      }}
                    />
                  </svg>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Skip Button */}
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
            onClick={() => {
              setIsVisible(false);
              setTimeout(() => onComplete?.(), 300);
            }}
            className="absolute bottom-8 right-8 text-gray-500 hover:text-gray-700 transition-colors text-sm"
          >
            跳過動畫 →
          </motion.button>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default WelcomeAnimation; 