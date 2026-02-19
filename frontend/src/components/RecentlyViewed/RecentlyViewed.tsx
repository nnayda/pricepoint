import { Link } from "react-router-dom";
import { useRecentlyViewed } from "../../hooks/useRecentlyViewed";

function formatTimeAgo(dateString: string): string {
  const now = Date.now();
  const viewed = new Date(dateString).getTime();
  const diffMs = now - viewed;
  const diffMinutes = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function RecentlyViewed() {
  const { recentlyViewed, clearRecentlyViewed } = useRecentlyViewed();

  if (recentlyViewed.length === 0) {
    return null;
  }

  return (
    <div className="w-full" data-testid="recently-viewed">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-sec">Recently Viewed</h2>
        <button
          onClick={clearRecentlyViewed}
          className="text-xs font-medium text-text-sec hover:text-text-pri"
        >
          Clear History
        </button>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {recentlyViewed.map((item) => (
          <Link
            key={item.address}
            to={`/results?lat=${item.lat}&lon=${item.lon}&address=${encodeURIComponent(item.address)}`}
            className="flex w-44 shrink-0 flex-col overflow-hidden rounded-md bg-bg-card shadow-soft transition-shadow hover:shadow-md"
          >
            {item.thumbnailUrl ? (
              <img
                src={item.thumbnailUrl}
                alt={item.address}
                className="h-24 w-full object-cover"
              />
            ) : (
              <div className="flex h-24 w-full items-center justify-center bg-gray-100 text-2xl text-gray-400">
                &#x1F3E0;
              </div>
            )}
            <div className="flex flex-col gap-0.5 p-2">
              <p className="truncate text-xs font-medium text-text-pri" title={item.address}>
                {item.address}
              </p>
              {item.price != null && (
                <p className="text-xs font-semibold text-brand-blue">
                  ${item.price.toLocaleString()}
                </p>
              )}
              <p className="text-[10px] text-text-sec">{formatTimeAgo(item.viewedAt)}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default RecentlyViewed;
