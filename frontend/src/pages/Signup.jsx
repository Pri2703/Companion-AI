import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import GlassCard from "../components/ui/GlassCard";
import GlowButton from "../components/ui/GlowButton";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("blind");
  const [linkedUser, setLinkedUser] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const payload = { email, password, role };
      if (role === "caretaker") {
        if (!linkedUser) {
           setError("Caretaker must link to a Blind User email");
           return;
        }
        payload.linked_user = linkedUser;
      }

      const res = await fetch("http://localhost:8000/signup", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" }
      });

      const data = await res.json();

      if (data.error) {
        setError(data.error);
        return;
      }

      // Auto-navigate to login upon successful signup
      navigate("/");
    } catch (err) {
       setError("Failed to connect to backend");
    }
  };

  return (
    <div className="page-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <GlassCard style={{ width: '100%', maxWidth: '460px', padding: '40px' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '32px', color: 'var(--primary)', letterSpacing: '2px', textTransform: 'uppercase' }}>Node Registration</h2>
        
        {error && <div style={{ background: 'rgba(255, 71, 87, 0.1)', color: 'var(--error)', padding: '12px', border: '1px solid var(--error)', borderRadius: '8px', marginBottom: '20px', textAlign: 'center' }}>{error}</div>}
        
        <form onSubmit={handleSignup} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Network Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className="glass-input">
              <option value="blind">SightAssist User (Host)</option>
              <option value="caretaker">Caretaker Network (Observer)</option>
            </select>
          </div>

          <input 
            type="email" 
            className="glass-input"
            placeholder="Operational Email address" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            required 
          />
          
          <input 
            type="password" 
            className="glass-input"
            placeholder="Secure Password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            required 
          />

          {role === "caretaker" && (
             <div style={{ padding: '20px', border: '1px solid rgba(83, 221, 252, 0.2)', borderRadius: '8px', background: 'rgba(83, 221, 252, 0.05)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <span style={{color: 'var(--secondary)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 'bold'}}>Telemetry Bonding</span>
                <input 
                  type="email" 
                  className="glass-input"
                  placeholder="Link to Primary User Email..." 
                  value={linkedUser} 
                  onChange={(e) => setLinkedUser(e.target.value)} 
                  required 
                />
             </div>
          )}

          <GlowButton type="submit" variant="primary" style={{ marginTop: '10px' }}>
            Authorize Creation
          </GlowButton>
        </form>

        <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '0.9rem', color: 'rgba(255,255,255,0.6)' }}>
           Existing Node? <Link to="/" style={{ color: 'var(--secondary)', textDecoration: 'none', fontWeight: 'bold' }}>Login Sequence</Link>
        </div>
      </GlassCard>
    </div>
  );
}
