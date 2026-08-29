import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Shell from "./components/Shell";
import Dashboard from "./pages/Dashboard";
import MapView from "./pages/MapView";
import ReviewQueue from "./pages/ReviewQueue";
import ChangeDetection from "./pages/ChangeDetection";
import Analytics from "./pages/Analytics";
import { ParcelProvider } from "./context/ParcelContext";
import "./index.css";

export default function App() {
  const [authed, setAuthed] = useState(false);
  if (!authed) return <Login onLogin={() => setAuthed(true)} />;
  return (
    <ParcelProvider>
      <BrowserRouter>
        <Shell onLogout={() => setAuthed(false)}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/map" element={<MapView />} />
            <Route path="/review" element={<ReviewQueue />} />
            <Route path="/changes" element={<ChangeDetection />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </Shell>
      </BrowserRouter>
    </ParcelProvider>
  );
}
