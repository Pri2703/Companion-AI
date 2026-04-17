export default function SectionContainer({ title, children, className = "" }) {
  return (
    <div className={`hud-panel ${className}`}>
      {title && <h2 style={{ marginBottom: '16px', color: 'var(--primary)', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>{title}</h2>}
      {children}
    </div>
  );
}
