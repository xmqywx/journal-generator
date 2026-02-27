import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from './components/layout/Sidebar';
import { MainContent } from './components/layout/MainContent';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex h-screen bg-white">
        <Sidebar />
        <MainContent />
      </div>
    </QueryClientProvider>
  );
}
