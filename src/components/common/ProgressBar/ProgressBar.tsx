import React from 'react';
import { UI_CONFIG } from '../../../constants/uiConfig';
import { ProcessingStage } from '../../../types/api';

interface ProgressBarProps {
  progress: number;
  stage: ProcessingStage;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  stage,
  size = 'md',
  showLabel = true
}) => {
  const getColorClass = (stage: ProcessingStage) => {
    const colorMap: Record<ProcessingStage, string> = {
      'idle': 'bg-gray-500',
      'uploading': 'bg-blue-500',
      'analyzing': 'bg-purple-500',
      'saving': 'bg-green-500',
      'extracting': 'bg-orange-500',
      'searching': 'bg-teal-500',
      'generating': 'bg-indigo-500',
      'completed': 'bg-green-500',
      'error': 'bg-red-500'
    };
    
    return colorMap[stage] || 'bg-gray-500';
  };
  
  const getSizeClass = (size: 'sm' | 'md' | 'lg') => {
    const sizeMap = {
      sm: 'h-1',
      md: 'h-2',
      lg: 'h-4'
    };
    
    return sizeMap[size];
  };

  // Clamp progress value between 0 and 100
  const clampedProgress = Math.min(100, Math.max(0, progress));
  
  return (
    <div className="w-full">
      <div className="relative w-full bg-gray-200 rounded-full overflow-hidden">
        <div 
          className={`${getSizeClass(size)} ${getColorClass(stage)} rounded-full transition-all`}
          style={{ 
            width: `${clampedProgress}%`, 
            transition: UI_CONFIG.animations.progressBarTransition
          }}
        />
      </div>
      
      {showLabel && (
        <div className="mt-1 flex justify-between text-xs font-medium">
          <span className="text-gray-700">
            {stage !== 'idle' ? stage.charAt(0).toUpperCase() + stage.slice(1) : 'Ready'}
          </span>
          <span className="text-gray-700">{Math.round(clampedProgress)}%</span>
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
