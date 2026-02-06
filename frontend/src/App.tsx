import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/Layout/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import ForecastPage from "./pages/ForecastPage";
import LandingPage from "./pages/LandingPage";

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/forecast" element={<ForecastPage />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
