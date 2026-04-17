export default function GlassCard({ children, glowColor, className = "", style = {} }) {
  return (
    <div 
      className={`glass-card ${className}`} 
      style={{ '--glow-color': glowColor, ...style }}
    >
      {children}
    </div>
  );
}
