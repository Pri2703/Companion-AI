import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import GlassCard from "../components/ui/GlassCard";
import GlowButton from "../components/ui/GlowButton";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch("http://localhost:8000/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        headers: { "Content-Type": "application/json" }
      });

      const data = await res.json();

      if (data.error) {
        setError(data.error);
        return;
      }

      localStorage.setItem("user", JSON.stringify(data));

      if (data.role === "caretaker") {
         navigate("/caretaker");
      } else {
         navigate("/user");
      }
    } catch (err) {
       setError("Failed to connect to backend");
    }
  };

  return (
    <div className="page-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <GlassCard style={{ width: '100%', maxWidth: '420px', padding: '40px' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '32px', color: 'var(--primary)', letterSpacing: '2px', textTransform: 'uppercase' }}>System Login</h2>
        
        {error && <div style={{ background: 'rgba(255, 71, 87, 0.1)', color: 'var(--error)', padding: '12px', border: '1px solid var(--error)', borderRadius: '8px', marginBottom: '20px', textAlign: 'center' }}>{error}</div>}
        
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <input 
            type="email" 
            className="glass-input"
            placeholder="Email address" 
            value={email} 
            onChange={(e) => setEmail(e.target.value)} 
            required 
          />
          <input 
            type="password" 
            className="glass-input"
            placeholder="Password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            required 
          />
          <GlowButton type="submit" variant="primary" style={{ marginTop: '10px' }}>
            Initialize Link
          </GlowButton>
        </form>
        
        <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '0.9rem', color: 'rgba(255,255,255,0.6)' }}>
           Unregistered Entity? <Link to="/signup" style={{ color: 'var(--secondary)', textDecoration: 'none', fontWeight: 'bold' }}>Register Node</Link>
        </div>
      </GlassCard>
    </div>
  );
}
