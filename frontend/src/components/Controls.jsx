import { useState } from "react";
import GlowButton from "./ui/GlowButton";

export default function Controls({ running, setRunning }) {
  const [source, setSource] = useState("0");
  const [ipUrl, setIpUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const toggleDetection = async () => {
    const endpoint = running ? "pause" : "start";
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    try {
      await fetch(`http://localhost:8000/${endpoint}`, { 
          method: "POST",
          body: JSON.stringify({ user_id: user.user_id }),
          headers: { "Content-Type": "application/json" }
      });
      setRunning(!running);
    } catch(err) {
      console.error("Toggle error", err);
    }
  };

  const applySource = async () => {
    if (source === "mobile" && !ipUrl) return alert("Please enter a valid IP Webcam URL");
    
    const finalSource = source === "mobile" ? ipUrl : 0;
    setLoading(true);
    try {
      await fetch("http://localhost:8000/set_source", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: finalSource })
      });
    } catch (err) {
      console.error("Source toggle error", err);
    }
    setLoading(false);
  };

  return (
    <div style={{ display: 'flex', gap: '15px', alignItems: 'center', width: '100%', justifyContent: 'space-between', padding: '10px 0' }}>
      {/* Source Selector Container */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <select 
          value={source} 
          onChange={(e) => setSource(e.target.value)}
          className="glass-input"
        >
          <option value="0">Laptop Web Camera</option>
          <option value="mobile">Mobile IP Camera</option>
        </select>
        
        {source === "mobile" && (
          <input
            type="text"
            className="glass-input"
            placeholder="http://192.168.1.X:8080/video"
            value={ipUrl}
            onChange={(e) => setIpUrl(e.target.value)}
            style={{ width: '250px' }}
          />
        )}
        
        <GlowButton variant="secondary" onClick={applySource} disabled={loading} style={{padding: '12px 20px'}}>
          {loading ? "..." : "Link Source"}
        </GlowButton>
      </div>

      <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
        <GlowButton 
          variant={running ? "danger" : "primary"} 
          onClick={toggleDetection}
        >
          {running ? "Pause Detection" : "Start Detection"}
        </GlowButton>
      </div>
    </div>
  );
}
