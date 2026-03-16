import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import * as Sentry from '@sentry/react';
import { AuthProvider } from './hooks/useAuth';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppShell } from './components/layout/AppShell';
import { ToastContainer } from './components/ui/Toast';
import { LoginPage } from './pages/Login';
import { SignupPage } from './pages/Signup';
import { DashboardPage } from './pages/Dashboard';
import { CallsPage } from './pages/Calls';
import { SettingsPage } from './pages/Settings';
import { GoogleCalendarCallbackPage } from './pages/GoogleCalendarCallback';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 10_000,
      refetchOnWindowFocus: true,
    },
  },
});

function App() {
  return (
    <Sentry.ErrorBoundary
      fallback={
        <div className="min-h-screen flex items-center justify-center p-6">
          <div className="glass rounded-2xl p-8 max-w-md text-center">
            <h2 className="text-xl font-bold text-red-400 mb-2">
              Something went wrong
            </h2>
            <p className="text-gray-300 mb-4">
              An unexpected error occurred. Please refresh the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-cyan-500 hover:bg-cyan-600 rounded-xl text-white font-semibold transition-all"
            >
              Refresh Page
            </button>
          </div>
        </div>
      }
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route
                path="/auth/google-calendar/callback"
                element={<GoogleCalendarCallbackPage />}
              />

              {/* Protected routes */}
              <Route
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
                <Route path="calls" element={<CallsPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
          <ToastContainer />
        </AuthProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </Sentry.ErrorBoundary>
  );
}

export default App;
