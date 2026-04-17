import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import GlowButton from "./GlowButton";

export default function TopNav({ statusState, isCaretaker = false }) {
  const navigate = useNavigate();
  return (
    <header className="top-nav animate-enter">
      <h1 className="brand-title">
        <span style={{color: 'var(--primary)'}}>◓</span> COMPANION AI
        {isCaretaker && <span style={{fontSize: '0.8rem', color: 'var(--secondary)', marginLeft: 10}}>CARETAKER PORTAL</span>}
      </h1>
      
      <div style={{display: 'flex', gap: '16px', alignItems: 'center'}}>
        {statusState !== undefined && statusState !== null && (
          <StatusBadge status={statusState === "ACTIVE" || statusState === true ? "active" : "paused"} />
        )}
        <GlowButton variant="secondary" onClick={() => { localStorage.clear(); navigate("/"); }}>
          Logout
        </GlowButton>
      </div>
    </header>
  );
}
