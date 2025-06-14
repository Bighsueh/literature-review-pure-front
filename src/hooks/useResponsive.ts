import { useState, useEffect } from 'react';

export type BreakpointKey = 'mobile' | 'tablet' | 'desktop';

export interface ResponsiveBreakpoints {
  mobile: number;    // < 640px
  tablet: number;    // 640px - 1024px
  desktop: number;   // > 1024px
}

export interface ResponsiveState {
  width: number;
  height: number;
  breakpoint: BreakpointKey;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  orientation: 'portrait' | 'landscape';
}

const defaultBreakpoints: ResponsiveBreakpoints = {
  mobile: 640,
  tablet: 1024,
  desktop: 1024,
};

export const useResponsive = (customBreakpoints?: Partial<ResponsiveBreakpoints>) => {
  const breakpoints = { ...defaultBreakpoints, ...customBreakpoints };
  
  const [state, setState] = useState<ResponsiveState>(() => {
    if (typeof window === 'undefined') {
      return {
        width: 1024,
        height: 768,
        breakpoint: 'desktop' as BreakpointKey,
        isMobile: false,
        isTablet: false,
        isDesktop: true,
        orientation: 'landscape' as const,
      };
    }
    
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    let breakpoint: BreakpointKey = 'desktop';
    if (width < breakpoints.mobile) {
      breakpoint = 'mobile';
    } else if (width < breakpoints.tablet) {
      breakpoint = 'tablet';
    }
    
    return {
      width,
      height,
      breakpoint,
      isMobile: breakpoint === 'mobile',
      isTablet: breakpoint === 'tablet',
      isDesktop: breakpoint === 'desktop',
      orientation: width > height ? 'landscape' : 'portrait',
    };
  });
  
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const updateState = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      
      let breakpoint: BreakpointKey = 'desktop';
      if (width < breakpoints.mobile) {
        breakpoint = 'mobile';
      } else if (width < breakpoints.tablet) {
        breakpoint = 'tablet';
      }
      
      setState({
        width,
        height,
        breakpoint,
        isMobile: breakpoint === 'mobile',
        isTablet: breakpoint === 'tablet',
        isDesktop: breakpoint === 'desktop',
        orientation: width > height ? 'landscape' : 'portrait',
      });
    };
    
    // 使用 ResizeObserver 如果可用，否則使用 resize 事件
    let resizeObserver: ResizeObserver | null = null;
    
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(updateState);
      resizeObserver.observe(document.body);
    } else {
      window.addEventListener('resize', updateState);
    }
    
    // 監聽方向變化
    const orientationHandler = () => {
      // 延遲執行以確保 innerWidth/innerHeight 已更新
      setTimeout(updateState, 100);
    };
    
    window.addEventListener('orientationchange', orientationHandler);
    
    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect();
      } else {
        window.removeEventListener('resize', updateState);
      }
      window.removeEventListener('orientationchange', orientationHandler);
    };
  }, [breakpoints.mobile, breakpoints.tablet]);
  
  return {
    ...state,
    // 輔助函數
    matches: (query: BreakpointKey | BreakpointKey[]) => {
      const queries = Array.isArray(query) ? query : [query];
      return queries.includes(state.breakpoint);
    },
    // 媒體查詢輔助函數
    matchesMinWidth: (width: number) => state.width >= width,
    matchesMaxWidth: (width: number) => state.width <= width,
    matchesWidthRange: (min: number, max: number) => state.width >= min && state.width <= max,
  };
};

// 用於虛擬鍵盤偵測的額外 hook
export const useVirtualKeyboard = () => {
  const [isVirtualKeyboardOpen, setIsVirtualKeyboardOpen] = useState(false);
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const initialViewportHeight = window.visualViewport?.height || window.innerHeight;
    
    const handleViewportChange = () => {
      if (window.visualViewport) {
        const currentHeight = window.visualViewport.height;
        const heightDifference = initialViewportHeight - currentHeight;
        
        // 如果高度差異大於 150px，認為是虛擬鍵盤開啟
        if (heightDifference > 150) {
          setIsVirtualKeyboardOpen(true);
          setKeyboardHeight(heightDifference);
        } else {
          setIsVirtualKeyboardOpen(false);
          setKeyboardHeight(0);
        }
      }
    };
    
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleViewportChange);
      
      return () => {
        window.visualViewport?.removeEventListener('resize', handleViewportChange);
      };
    }
  }, []);
  
  return {
    isVirtualKeyboardOpen,
    keyboardHeight,
  };
}; 