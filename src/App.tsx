import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ResponsiveMainLayout from './components/ResponsiveMainLayout';
import ErrorBoundary from './components/common/ErrorBoundary';
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

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <div className="app">
          <ResponsiveMainLayout />
        </div>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
