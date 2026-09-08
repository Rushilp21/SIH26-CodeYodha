import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { ParcelDetailPage } from "./pages/ParcelDetailPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/projects/:projectId/queue" element={<ReviewQueuePage />} />
        <Route path="/projects/:projectId/parcels/:parcelId" element={<ParcelDetailPage />} />
      </Routes>
    </AppShell>
  );
}
