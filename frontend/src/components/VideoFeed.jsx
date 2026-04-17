export default function VideoFeed() {
  return (
    <div className="card">
      <h2 style={{marginTop: 0}}>Live Feed</h2>
      <img src="http://localhost:8000/video" width="640" alt="Video Stream" />
    </div>
  );
}
