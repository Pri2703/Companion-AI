import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Controls from "../components/Controls";
import AlertsPanel from "../components/AlertsPanel";
import TopNav from "../components/ui/TopNav";
import GlassCard from "../components/ui/GlassCard";

export default function UserDashboard() {
  const [running, setRunning] = useState(false);
  const navigate = useNavigate();

  // Prevent cross-tab overwrites from crashing dashboard
  const [user] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));

  useEffect(() => {
    if (!user || user.role !== "blind") {
      navigate("/");
    }
  }, [navigate]);

  useEffect(() => {
    if (!user || user.role !== "blind") return;

    const sendLocation = async (lat, lng) => {
      try {
        await fetch("http://localhost:8000/location/update", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user.user_id,
            lat,
            lng
          })
        });
      } catch (err) {
        console.error("Location link failed", err);
      }
    };

    const interval = setInterval(() => {
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => sendLocation(pos.coords.latitude, pos.coords.longitude),
          (err) => console.warn("GPS disabled or blocked"),
          { enableHighAccuracy: true }
        );
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [user]);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch("http://localhost:8000/status");
        if (res.ok) {
           const data = await res.json();
           setRunning(data.running);
        }
      } catch(err) {
        console.error("Status fetch failed", err);
      }
    }
    fetchStatus();
  }, []);

  if (!user || user.role !== "blind") return null;

  return (
    <div className="page-container">
      <TopNav statusState={running} />

      <main className="hud-grid">
        <div className="hud-col-8">
          <GlassCard style={{ padding: '0', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
              <Controls running={running} setRunning={setRunning} />
            </div>
            <div className="hud-video-wrapper" style={{ flexGrow: 1, border: 'none', borderRadius: '0', boxShadow: 'none' }}>
              <img src="http://localhost:8000/video" width="100%" style={{ display: 'block', height: '100%', objectFit: 'cover' }} alt="Camera Feed" />
            </div>
          </GlassCard>
        </div>
        
        <div className="hud-col-4">
          <AlertsPanel running={running} />
        </div>
      </main>
    </div>
  );
}
