import { NavLink, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { ParcelDetailPage } from "./pages/ParcelDetailPage";

export default function App() {
  return (
    <div className="mx-auto max-w-5xl p-4">
      <nav className="mb-4 flex gap-4 text-sm">
        <NavLink to="/" className="text-sky-400">
          Dashboard
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/projects/:projectId/queue" element={<ReviewQueuePage />} />
        <Route path="/projects/:projectId/parcels/:parcelId" element={<ParcelDetailPage />} />
      </Routes>
    </div>
  );
}
