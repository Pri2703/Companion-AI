export default function StatusBadge({ status, text, className="" }) {
  // status: "active" | "paused"
  const badgeClass = status === "active" ? "status-active" : "status-paused";
  
  return (
    <span className={`status-badge ${badgeClass} ${className}`}>
      {text || status}
    </span>
  );
}
