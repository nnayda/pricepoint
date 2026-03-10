import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/Layout/AppLayout";
import ErrorBoundary from "./components/ErrorBoundary/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";

const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const LandingPage = lazy(() => import("./pages/LandingPage"));
const PropertyDashboardPage = lazy(() => import("./pages/PropertyDashboardPage"));
const SignInPage = lazy(() => import("./pages/SignInPage"));
const SignUpPage = lazy(() => import("./pages/SignUpPage"));
const UserSettingsPage = lazy(() => import("./pages/UserSettingsPage"));
const UploadPage = lazy(() => import("./pages/UploadPage"));
const SavedPropertiesPage = lazy(() => import("./pages/SavedPropertiesPage"));
const ComparablesPage = lazy(() => import("./pages/ComparablesPage"));

function PageLoader() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center">
      <div
        className="h-8 w-8 animate-spin rounded-full border-4 border-brand-blue border-t-transparent"
        role="status"
      >
        <span className="sr-only">Loading page...</span>
      </div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <AppLayout>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/signin" element={<SignInPage />} />
                <Route path="/signup" element={<SignUpPage />} />
                <Route path="/settings" element={<UserSettingsPage />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/saved" element={<SavedPropertiesPage />} />
                <Route path="/property/:address" element={<PropertyDashboardPage />} />
                <Route path="/compare/:address" element={<ComparablesPage />} />
                <Route path="/results" element={<Navigate to="/" replace />} />
                <Route path="/dashboard" element={<Navigate to="/" replace />} />
                <Route path="/test-dashboard-page" element={<Navigate to="/" replace />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </Suspense>
          </AppLayout>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
