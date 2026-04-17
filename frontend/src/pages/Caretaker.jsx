import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import TopNav from "../components/ui/TopNav";
import GlassCard from "../components/ui/GlassCard";
import SectionContainer from "../components/ui/SectionContainer";

export default function CaretakerDashboard() {
  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [location, setLocation] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  // Localize user explicitly so sharing localhost over multiple tabs doesn't corrupt React's re-render bounds!
  const [user] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));

  useEffect(() => {
    if (!user || user.role !== "caretaker") {
      navigate("/");
      return;
    }

    const fetchData = async () => {
      try {
        const statusRes = await fetch(`http://localhost:8000/caretaker/${user.user_id}/status`);
        const statusData = await statusRes.json();
        if (statusData.error) throw new Error(statusData.error);
        setStatus(statusData);

        const logsRes = await fetch(`http://localhost:8000/caretaker/${user.user_id}/logs`);
        const logsData = await logsRes.json();
        if (logsData.error) throw new Error(logsData.error);
        setLogs(logsData);
        
        const locRes = await fetch(`http://localhost:8000/caretaker/location/${user.user_id}`);
        const locData = await locRes.json();
        if (!locData.error && locData.lat && locData.lng) {
            setLocation(locData);
        }
        
      } catch (err) {
        setError(err.message || "Failed to fetch caretaker data. Check if backend is active/seeded.");
      }
    };
    
    fetchData();
    const interval = setInterval(fetchData, 2000); // Polling 2s
    return () => clearInterval(interval);
  }, [navigate]);

  useEffect(() => {
    if (logs.length > 0) {
      const topLog = logs[0];
      if (topLog.risk === "HIGH") {
         // Placeholder notification
         console.warn("HIGH RISK ALERT SOUND TRIGGERED");
      }
    }
  }, [logs]);

  if (!user || user.role !== "caretaker") return null;

  return (
    <div className="page-container">
      <TopNav statusState={status?.state} isCaretaker={true} />

      {error && <div style={{background: 'rgba(255, 71, 87, 0.1)', color: 'var(--error)', padding: '16px', border: '1px solid var(--error)', borderRadius: '8px', marginBottom: '24px'}}>{error}</div>}

      <main className="hud-grid">
         
         {/* LEFT COLUMN: Status & Maps */}
         <div className="hud-col-4" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
           <GlassCard style={{ padding: '24px' }}>
              <SectionContainer title="System Status" className="hud-panel">
                {status ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                     <div>
                       <span style={{color: 'rgba(255,255,255,0.6)', display: 'block', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px'}}>State</span>
                       <span style={{color: status.state === 'ACTIVE' ? 'var(--success)' : 'var(--error)', fontWeight: '700', fontSize: '1.2rem', letterSpacing: '1px', textShadow: `0 0 10px ${status.state === 'ACTIVE' ? 'var(--success)' : 'var(--error)'}`}}>{status.state}</span>
                     </div>
                     <div>
                       <span style={{color: 'rgba(255,255,255,0.6)', display: 'block', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px'}}>Last Seen</span>
                       <span style={{fontWeight: '500', fontFamily: 'monospace', fontSize: '1rem'}}>{new Date(status.last_seen).toLocaleString()}</span>
                     </div>
                     <div>
                       <span style={{color: 'rgba(255,255,255,0.6)', display: 'block', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px'}}>Telemetry Node</span>
                       <span style={{fontWeight: '500'}}>{status.environment}</span>
                     </div>
                  </div>
                ) : <p style={{color: 'rgba(255,255,255,0.3)', fontStyle: 'italic'}}>Awaiting handshake...</p>}
              </SectionContainer>
           </GlassCard>

           <GlassCard style={{ padding: '24px' }}>
              <SectionContainer title="Live GPS Tracking" className="hud-panel">
                {location ? (
                   <div style={{ position: 'relative' }}>
                     <iframe
                        title="User Tracking"
                        src={`https://maps.google.com/maps?q=${location.lat},${location.lng}&z=15&output=embed`}
                        width="100%"
                        height="240"
                        style={{ border: 0, borderRadius: '8px', filter: 'invert(1) hue-rotate(180deg) brightness(1.2)' }}
                     />
                     <div style={{
                       position: 'absolute', top: 10, right: 10, 
                       background: 'rgba(0,0,0,0.7)', padding: '4px 8px', borderRadius: '4px',
                       fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--secondary)'
                     }}>
                        {new Date(location.timestamp).toLocaleTimeString()}
                     </div>
                   </div>
                ) : <p style={{color: 'rgba(255,255,255,0.3)', fontStyle: 'italic'}}>Awaiting GPS signal satellite targeting...</p>}
              </SectionContainer>
           </GlassCard>
         </div>

         {/* RIGHT COLUMN: Video & Timeline */}
         <div className="hud-col-8" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
           
           <GlassCard style={{ padding: '0', overflow: 'hidden' }}>
              <div className="hud-video-wrapper" style={{ border: 'none', borderRadius: '0' }}>
                <div style={{position: 'absolute', top: 16, left: 16, zIndex: 20}}>
                   <span style={{background: 'rgba(255, 71, 87, 0.2)', color: 'var(--error)', padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold', fontFamily: 'Space Grotesk', letterSpacing: '1px', border: '1px solid rgba(255, 71, 87, 0.4)'}}>LIVE FEED</span>
                </div>
                <img src="http://localhost:8000/video_raw" width="100%" style={{display: 'block', objectFit: 'cover'}} alt="Patient Sync" />
              </div>
           </GlassCard>

           <GlassCard style={{ padding: '24px' }}>
              <SectionContainer title="Critical Activity Timeline" className="hud-panel">
                <div style={{maxHeight: '300px', overflowY: 'auto', paddingRight: '10px' }}>
                   {logs.filter(log => log.risk === "MODERATE" || log.risk === "HIGH").length === 0 && (
                     <p style={{color: 'rgba(255,255,255,0.3)', fontStyle: 'italic', margin: 0}}>No recent critical threshold breaches observed.</p>
                   )}
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                     {logs.filter(log => log.risk === "MODERATE" || log.risk === "HIGH").map((log) => (
                        <div key={log._id} className="animate-slide" style={{ 
                          background: log.risk === 'HIGH' ? 'rgba(255, 71, 87, 0.05)' : 'rgba(255, 165, 2, 0.05)',
                          borderLeft: log.risk === 'HIGH' ? '4px solid var(--error)' : '4px solid var(--warning)',
                          padding: '16px',
                          borderRadius: '0 8px 8px 0',
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '16px',
                          boxShadow: log.risk === 'HIGH' ? '0 0 10px rgba(255, 71, 87, 0.1)' : 'none'
                        }}>
                          <div style={{ color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace', fontSize: '0.9rem', paddingTop: '2px', flexShrink: 0 }}>
                             {new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                          </div>
                          <div>
                            <span style={{
                               display: 'inline-block',
                               padding: '2px 8px',
                               borderRadius: '4px',
                               fontSize: '0.7rem',
                               fontWeight: 'bold',
                               marginBottom: '6px',
                               letterSpacing: '1px',
                               background: log.risk === 'HIGH' ? 'rgba(255, 71, 87, 0.2)' : 'rgba(255, 165, 2, 0.2)',
                               color: log.risk === 'HIGH' ? 'var(--error)' : 'var(--warning)'
                            }}>{log.risk}</span>
                            <div style={{fontWeight: '500', lineHeight: '1.4'}}>
                              {log.alerts.length > 0 ? log.alerts.join(" • ") : "Unclassified Detection Triggered"}
                            </div>
                          </div>
                        </div>
                     ))}
                   </div>
                </div>
              </SectionContainer>
           </GlassCard>
           
         </div>
      </main>
    </div>
  );
}
