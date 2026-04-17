export default function GlowButton({ children, variant = "primary", onClick, disabled, className = "" }) {
  return (
    <button 
      className={`glow-btn ${variant} ${className}`} 
      onClick={onClick}
      disabled={disabled}
      style={{ opacity: disabled ? 0.6 : 1, cursor: disabled ? "not-allowed" : "pointer" }}
    >
      {children}
    </button>
  );
}
