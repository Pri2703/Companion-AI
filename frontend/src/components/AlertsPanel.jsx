import { useEffect, useState, useRef } from "react";
import GlassCard from "./ui/GlassCard";
import StatusBadge from "./ui/StatusBadge";

export default function AlertsPanel({ running }) {
  const [data, setData] = useState({ objects: [], alerts: [] });
  const [status, setStatus] = useState("Connecting...");
  const lastSpoken = useRef("");
  const lastSpeechTime = useRef(0);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/data?user_id=${user.user_id || ""}`);
        const json = await res.json();
        setData(json);
        setStatus("System Active");
      } catch (err) {
        console.error("Fetch error:", err);
        setStatus("Disconnected");
      }
    }, 250); // Aggressive low-latency 250ms polling for instant audio dispatch

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!running) {
      // Cancel any currently playing or queued voices instantly if paused
      window.speechSynthesis.cancel();
      return;
    }
    
    if (data.alerts && data.alerts.length > 0) {
      const text = data.alerts[0]; // Speak highest priority alert
      const now = Date.now();
      
      // Determine if this is a completely different object type
      const isNewObject = lastSpoken.current.split(' ')[0] !== text.split(' ')[0];
      
      // Speak if 2.5s elapsed, OR if it's a new object and 1s elapsed (strict immediate dispatch)
      if (text !== "Detection paused") {
        if ((now - lastSpeechTime.current > 2500) || (isNewObject && now - lastSpeechTime.current > 1000)) {
           // Clear any old queue so we don't build a backlog
           window.speechSynthesis.cancel(); 
           
           const msg = new SpeechSynthesisUtterance(text);
           window.speechSynthesis.speak(msg);
           
           lastSpoken.current = text;
           lastSpeechTime.current = now;
        }
      }
    }
  }, [data.alerts, running]);

  return (
    <GlassCard glowColor={running ? "rgba(46, 213, 115, 0.2)" : "rgba(255, 71, 87, 0.2)"} style={{height: '100%', padding: '24px'}}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{margin: 0, color: 'var(--primary)'}}>Real-Time Alerts</h2>
        <StatusBadge status={status === "System Active" ? "active" : "paused"} text={status} />
      </div>

      <div style={{ marginBottom: "24px" }}>
        <h3 style={{fontSize: '1rem', color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', letterSpacing: '1px'}}>Critical Triggers</h3>
        {data.alerts.length === 0 ? (
          <p style={{color: 'rgba(255,255,255,0.3)', fontStyle: 'italic'}}>No active risk alerts...</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {data.alerts.map((alert, idx) => (
              <li key={idx} className="animate-slide" style={{ 
                 background: 'rgba(255, 71, 87, 0.1)', 
                 borderLeft: '4px solid var(--error)',
                 padding: '12px 16px',
                 borderRadius: '0 8px 8px 0',
                 display: 'flex',
                 alignItems: 'center',
                 gap: '12px',
                 boxShadow: '0 0 15px rgba(255, 71, 87, 0.15)'
              }}>
                <span style={{color: 'var(--error)', fontSize: '1.2rem'}}>⚠️</span>
                <span style={{fontWeight: '500'}}>{alert}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 style={{fontSize: '1rem', color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', letterSpacing: '1px'}}>Radar Objects</h3>
        {data.objects.length === 0 ? (
          <p style={{color: 'rgba(255,255,255,0.3)', fontStyle: 'italic'}}>Scanning environment...</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {data.objects.map((obj, i) => (
              <li key={i} className="animate-slide" style={{
                 padding: '10px 14px',
                 background: 'rgba(255,255,255,0.03)',
                 borderRadius: '6px',
                 display: 'flex',
                 justifyContent: 'space-between'
              }}>
                <span style={{color: 'var(--secondary)', textTransform: 'capitalize', fontWeight: '500'}}>{obj.label}</span>
                <span style={{color: 'rgba(255,255,255,0.8)'}}>
                   {obj.direction} 
                   {obj.distance !== null ? ` | ${parseFloat(obj.distance).toFixed(2)}m` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </GlassCard>
  );
}
