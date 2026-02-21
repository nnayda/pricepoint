import { useParams } from "react-router-dom";
import DashboardLayout from "../components/dashboard/DashboardLayout";
import { mockDashboardData } from "../data/mockDashboardData";

function PropertyDashboardPage() {
  // address param will be used for real data fetching in the future
  useParams<{ address: string }>();
  return <DashboardLayout data={mockDashboardData} />;
}

export default PropertyDashboardPage;
