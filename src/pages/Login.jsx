import { useState } from "react";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("officer@pmcgis.gov.in");
  const [pass, setPass] = useState("••••••••");
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => { setLoading(false); onLogin(); }, 1200);
  };

  return (
    <div className="login-page">
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "rgba(255,255,255,0.6)", fontSize: 12, marginBottom: 8 }}>
            <span style={{ width: 40, height: 1, background: "rgba(255,255,255,0.3)", display: "inline-block" }} />
            GOVERNMENT OF INDIA · SMART INDIA HACKATHON 2026
            <span style={{ width: 40, height: 1, background: "rgba(255,255,255,0.3)", display: "inline-block" }} />
          </div>
          <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 11 }}>Problem Statement SIH26012</div>
        </div>

        <div className="login-card fade-in">
          <div className="login-logo">
            <div className="logo-icon" style={{ width: 44, height: 44, fontSize: 17, borderRadius: 12 }}>GIS</div>
            <div>
              <div className="login-title">ParcelAI</div>
              <div className="login-subtitle">AI-Powered Urban Parcel Mapping<br />& Cadastral Extraction Platform</div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 20, padding: "10px 14px", background: "var(--primary-bg)", borderRadius: "var(--radius-sm)", border: "1px solid #BFDBFE" }}>
            <span style={{ fontSize: 18 }}>🏛️</span>
            <div style={{ fontSize: 12, color: "var(--primary)" }}>
              <strong>Pune Municipal Corporation — GIS Portal</strong><br />
              Authorized government personnel only. All sessions are monitored.
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Official Email ID</label>
              <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="form-input" type="password" value={pass} onChange={e => setPass(e.target.value)} required />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, fontSize: 12 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)", cursor: "pointer" }}>
                <input type="checkbox" defaultChecked /> Keep me signed in
              </label>
              <span style={{ color: "var(--primary)", cursor: "pointer" }}>Forgot password?</span>
            </div>
            <button className="login-btn" type="submit" disabled={loading}>
              {loading ? <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}><div className="spinner" />Authenticating…</span> : "Sign In to GIS Portal"}
            </button>
          </form>

          <div style={{ marginTop: 20, padding: "10px 14px", background: "#F8FAFC", borderRadius: 8, fontSize: 12, color: "var(--text-secondary)", textAlign: "center" }}>
            Demo credentials pre-filled · Click Sign In to access the dashboard
          </div>
        </div>
      </div>
    </div>
  );
}
