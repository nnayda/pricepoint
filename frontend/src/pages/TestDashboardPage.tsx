import DashboardLayout from "../components/dashboard/DashboardLayout";
import { mockDashboardData } from "../data/mockDashboardData";

function TestDashboardPage() {
  return <DashboardLayout data={mockDashboardData} />;
}

export default TestDashboardPage;
