import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/Layout/AppLayout";

const LandingPage = lazy(() => import("./pages/LandingPage"));
const ForecastPage = lazy(() => import("./pages/ForecastPage"));
const ResultsPage = lazy(() => import("./pages/ResultsPage"));

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
    <AppLayout>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/forecast" element={<ForecastPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/dashboard" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AppLayout>
  );
}

export default App;
