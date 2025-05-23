import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MainLayout from './components/MainLayout';
import './index.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 30, // 30 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="app">
        <MainLayout />
      </div>
    </QueryClientProvider>
  );
}

export default App;
