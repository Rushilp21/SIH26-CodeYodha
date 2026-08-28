// Mock data for AI Urban Parcel Mapping Platform (SIH26012)
// Coordinates centered around Pune, India

export const CITY_CENTER = [18.5204, 73.8567];

function makePolygon(lat, lng, size = 0.0008) {
  const s = size;
  return [[lat + s, lng - s],[lat + s, lng + s],[lat - s, lng + s],[lat - s, lng - s]];
}

const FLAG_REASONS = {
  OVERLAP: "Geometry overlap with adjacent parcel",
  FOOTPRINT: "Building footprint crosses predicted boundary",
  AREA_CHANGE: "Significant area change from previous survey (>15%)",
  SPLIT: "Parcel may have been split — multi-owner signature detected",
  ROAD_ENCROACH: "Boundary extends into road right-of-way",
  MISSING: "No matching record in legacy cadastral database",
  LOW_CONF: "Model confidence below threshold (segmentation ambiguity)",
  DUPLICATE: "Potential duplicate parcel — coordinate overlap >80%",
};

const LAND_USE = ["Residential","Commercial","Industrial","Agricultural","Mixed-Use","Open Space","Institutional"];
const WARDS = ["Ward A - Shivajinagar","Ward B - Kothrud","Ward C - Hadapsar","Ward D - Aundh","Ward E - Baner","Ward F - Yerawada","Ward G - Wanowrie"];
const ZONES = ["North","South","East","West","Central"];

function rnd(a, b) { return a + Math.random() * (b - a); }

// Use seeded-like fixed values for reproducibility
const SEED = [
  [18.521, 73.854, 0.0009],[18.515, 73.862, 0.0007],[18.530, 73.849, 0.0011],
  [18.508, 73.871, 0.0008],[18.543, 73.858, 0.0012],[18.517, 73.840, 0.0007],
  [18.525, 73.875, 0.0009],[18.534, 73.847, 0.0010],[18.512, 73.863, 0.0008],
  [18.548, 73.852, 0.0006],[18.503, 73.845, 0.0009],[18.538, 73.867, 0.0011],
  [18.519, 73.878, 0.0007],[18.527, 73.843, 0.0008],[18.510, 73.856, 0.0010],
  [18.541, 73.872, 0.0009],[18.506, 73.861, 0.0007],[18.533, 73.850, 0.0008],
  [18.522, 73.865, 0.0011],[18.515, 73.836, 0.0009],[18.545, 73.860, 0.0007],
  [18.508, 73.873, 0.0010],[18.529, 73.841, 0.0008],[18.536, 73.869, 0.0006],
  [18.512, 73.855, 0.0009],[18.524, 73.844, 0.0012],[18.518, 73.874, 0.0008],
  [18.540, 73.855, 0.0010],[18.504, 73.867, 0.0007],[18.531, 73.862, 0.0009],
  [18.520, 73.838, 0.0008],[18.546, 73.865, 0.0011],[18.509, 73.850, 0.0007],
  [18.537, 73.843, 0.0009],[18.516, 73.870, 0.0010],[18.527, 73.858, 0.0008],
  [18.505, 73.863, 0.0006],[18.543, 73.848, 0.0009],[18.519, 73.876, 0.0011],
  [18.532, 73.855, 0.0007],[18.511, 73.841, 0.0008],[18.526, 73.868, 0.0010],
  [18.539, 73.857, 0.0009],[18.507, 73.876, 0.0008],[18.523, 73.845, 0.0007],
  [18.548, 73.863, 0.0010],[18.514, 73.859, 0.0009],[18.535, 73.871, 0.0008],
];

const CONF_SEED = [94,71,88,45,97,38,82,63,91,56,79,41,86,68,93,52,74,89,47,96,61,83,39,77,90,55,85,72,43,95,66,80,50,87,64,92,49,76,84,58,70,98,53,88,67,91,42,78,62,95];

export const parcels = SEED.map(([lat, lng, size], i) => {
  const id = `P-${String(i + 100).padStart(4, "0")}`;
  const confidence = CONF_SEED[i] || Math.round(rnd(38,98));
  const status = confidence >= 85 ? "approved" : confidence >= 62 ? "review" : "field";
  const landUse = LAND_USE[i % LAND_USE.length];
  const ward = WARDS[i % WARDS.length];
  const zone = ZONES[i % ZONES.length];
  const area = 120 + ((i * 47 + 13) % 2280);
  const flagKeys = Object.keys(FLAG_REASONS);
  const numFlags = status === "approved" ? 0 : status === "review" ? 1 + (i % 2) : 2 + (i % 2);
  const flags = flagKeys.slice(i % 3, (i % 3) + numFlags).map(k => FLAG_REASONS[k]);
  const priority = confidence < 55 ? "High" : confidence < 75 ? "Medium" : "Low";
  const history = [
    { year: 2022, area: area - 150, status: "Surveyed" },
    { year: 2023, area: area - 80, status: "Verified" },
    { year: 2024, area: area - 20, status: "Updated" },
    { year: 2026, area, status: "AI Extracted" },
  ];
  return { id, lat, lng, polygon: makePolygon(lat, lng, size), confidence, status, landUse, ward, zone, area, flags, priority, owner: `Owner ${id}`, surveyNo: `SN-${1000 + i * 17}`, history, lastUpdated: `2026-08-${String((i % 24) + 1).padStart(2,"0")}` };
});

export const dashboardStats = {
  totalParcels: 1248, autoApproved: 847, autoApprovedPct: 67.9,
  pendingReview: 312, fieldVerification: 89, modelCorrections: 34, avgConfidence: 78.4,
};

export const processingTimeline = [
  { date: "Jan", count: 42 },{ date: "Feb", count: 78 },{ date: "Mar", count: 115 },
  { date: "Apr", count: 203 },{ date: "May", count: 287 },{ date: "Jun", count: 341 },
  { date: "Jul", count: 398 },{ date: "Aug", count: 312 },
];

export const confidenceDistribution = [
  { range: "0–20%", count: 12 },{ range: "21–40%", count: 28 },{ range: "41–60%", count: 67 },
  { range: "61–75%", count: 134 },{ range: "76–85%", count: 421 },
  { range: "86–95%", count: 489 },{ range: "96–100%", count: 97 },
];

export const recentActivity = [
  { id: 1, type: "flagged", parcelId: "P-0182", message: "Flagged for review — geometry overlap detected", time: "2 min ago" },
  { id: 2, type: "approved", parcelId: "P-0167", message: "Auto-approved — confidence 93%", time: "8 min ago" },
  { id: 3, type: "field", parcelId: "P-0141", message: "Sent to field verification — confidence 42%", time: "15 min ago" },
  { id: 4, type: "edited", parcelId: "P-0098", message: "Boundary edited by officer Sharma (Ward B)", time: "32 min ago" },
  { id: 5, type: "approved", parcelId: "P-0211", message: "Approved after ground-truth submission", time: "1 hr ago" },
  { id: 6, type: "flagged", parcelId: "P-0073", message: "Flagged — building footprint crosses boundary", time: "1 hr ago" },
  { id: 7, type: "model", parcelId: null, message: "Model re-trained — 12 new corrections applied", time: "3 hr ago" },
  { id: 8, type: "approved", parcelId: "P-0055", message: "Batch of 18 parcels auto-approved (Ward D)", time: "5 hr ago" },
];

export const landUseBreakdown = [
  { name: "Residential", value: 412, color: "#3B82F6" },
  { name: "Commercial", value: 187, color: "#10B981" },
  { name: "Industrial", value: 94, color: "#F59E0B" },
  { name: "Agricultural", value: 68, color: "#84CC16" },
  { name: "Mixed-Use", value: 231, color: "#8B5CF6" },
  { name: "Open Space", value: 145, color: "#06B6D4" },
  { name: "Institutional", value: 111, color: "#EC4899" },
];

export const anomaliesByZone = [
  { zone: "North", count: 23, resolved: 18 },{ zone: "South", count: 31, resolved: 25 },
  { zone: "East", count: 17, resolved: 11 },{ zone: "West", count: 28, resolved: 20 },
  { zone: "Central", count: 42, resolved: 31 },
];

export const modelAccuracyTrend = [
  { month: "Mar", accuracy: 71.2, iou: 0.64 },{ month: "Apr", accuracy: 74.8, iou: 0.67 },
  { month: "May", accuracy: 78.1, iou: 0.71 },{ month: "Jun", accuracy: 80.3, iou: 0.74 },
  { month: "Jul", accuracy: 83.7, iou: 0.78 },{ month: "Aug", accuracy: 86.2, iou: 0.81 },
];

export const changeEvents = [
  { id: "CD-001", type: "New Construction", lat: 18.535, lng: 73.862, parcelId: "P-0203", description: "New multi-story structure detected in 2026 survey", date: "2026-08-10", severity: "Medium", affectedArea: 340 },
  { id: "CD-002", type: "Demolition", lat: 18.512, lng: 73.848, parcelId: "P-0118", description: "Structure removed — parcel boundary may require update", date: "2026-08-12", severity: "Low", affectedArea: 180 },
  { id: "CD-003", type: "Boundary Shift", lat: 18.524, lng: 73.871, parcelId: "P-0145", description: "Parcel boundary shifted >2m from 2024 baseline", date: "2026-08-14", severity: "High", affectedArea: 620 },
  { id: "CD-004", type: "Land-Use Change", lat: 18.508, lng: 73.855, parcelId: "P-0092", description: "Residential plot shows commercial construction activity", date: "2026-08-15", severity: "High", affectedArea: 890 },
  { id: "CD-005", type: "New Construction", lat: 18.543, lng: 73.841, parcelId: "P-0231", description: "Two new structures detected on previously open land", date: "2026-08-17", severity: "Medium", affectedArea: 510 },
  { id: "CD-006", type: "Boundary Shift", lat: 18.517, lng: 73.869, parcelId: "P-0077", description: "Minor boundary adjustment — road widening project", date: "2026-08-18", severity: "Low", affectedArea: 95 },
  { id: "CD-007", type: "Land-Use Change", lat: 18.529, lng: 73.844, parcelId: "P-0162", description: "Agricultural land converted — structure footprints present", date: "2026-08-20", severity: "High", affectedArea: 2100 },
  { id: "CD-008", type: "Demolition", lat: 18.533, lng: 73.858, parcelId: "P-0189", description: "Old warehouse demolished — parcel now open space", date: "2026-08-22", severity: "Medium", affectedArea: 1240 },
];

export const turnaroundData = [
  { week: "Wk 1", avgDays: 4.2 },{ week: "Wk 2", avgDays: 3.8 },{ week: "Wk 3", avgDays: 3.1 },
  { week: "Wk 4", avgDays: 2.7 },{ week: "Wk 5", avgDays: 2.4 },{ week: "Wk 6", avgDays: 2.9 },
  { week: "Wk 7", avgDays: 2.1 },{ week: "Wk 8", avgDays: 1.8 },
];
