import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/Layout/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import ForecastPage from "./pages/ForecastPage";

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/forecast" element={<ForecastPage />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
