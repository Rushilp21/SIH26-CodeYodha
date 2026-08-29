import { createContext, useContext, useState, useCallback } from "react";
import { parcels as initialParcels } from "../data/mockData";

const ParcelContext = createContext(null);

export function ParcelProvider({ children }) {
  const [parcels, setParcels] = useState(() =>
    initialParcels.map(p => ({ ...p }))
  );
  const [activityLog, setActivityLog] = useState([]);

  const logActivity = useCallback((type, parcelId, message) => {
    setActivityLog(prev => [
      { id: Date.now(), type, parcelId, message, time: "Just now" },
      ...prev.slice(0, 49),
    ]);
  }, []);

  const approveParcel = useCallback((id, note = "") => {
    setParcels(prev =>
      prev.map(p =>
        p.id === id
          ? { ...p, status: "approved", confidence: Math.max(p.confidence, 85), lastUpdated: "2026-08-29" }
          : p
      )
    );
    logActivity("approved", id, `Approved by officer${note ? ": " + note : ""}`);
  }, [logActivity]);

  const rejectParcel = useCallback((id, reason = "") => {
    setParcels(prev =>
      prev.map(p =>
        p.id === id
          ? { ...p, status: "field", priority: "High", lastUpdated: "2026-08-29" }
          : p
      )
    );
    logActivity("field", id, `Rejected — sent to field verification${reason ? ": " + reason : ""}`);
  }, [logActivity]);

  const editBoundary = useCallback((id, newPolygon, newArea) => {
    setParcels(prev =>
      prev.map(p =>
        p.id === id
          ? {
              ...p,
              polygon: newPolygon,
              area: newArea,
              lastUpdated: "2026-08-29",
              status: p.status === "field" ? "review" : p.status,
            }
          : p
      )
    );
    logActivity("edited", id, `Boundary edited by officer — area updated to ${newArea} m²`);
  }, [logActivity]);

  const addGroundTruth = useCallback((id, note = "") => {
    setParcels(prev =>
      prev.map(p =>
        p.id === id
          ? { ...p, status: "approved", lastUpdated: "2026-08-29" }
          : p
      )
    );
    logActivity("approved", id, `Ground truth submitted${note ? ": " + note : ""}`);
  }, [logActivity]);

  return (
    <ParcelContext.Provider value={{ parcels, approveParcel, rejectParcel, editBoundary, addGroundTruth, activityLog }}>
      {children}
    </ParcelContext.Provider>
  );
}

export function useParcels() {
  const ctx = useContext(ParcelContext);
  if (!ctx) throw new Error("useParcels must be used within ParcelProvider");
  return ctx;
}
