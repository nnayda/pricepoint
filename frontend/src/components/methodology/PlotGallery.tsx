import DashboardCard from "../dashboard/DashboardCard";
import { getModelArtifactUrl } from "../../services/model";

interface PlotItem {
  path: string;
  title: string;
}

interface PlotGalleryProps {
  plots: PlotItem[];
  columns?: number;
}

function PlotGallery({ plots, columns = 2 }: PlotGalleryProps) {
  if (plots.length === 0) return null;

  return (
    <div
      className="grid gap-4"
      style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
    >
      {plots.map((plot) => (
        <DashboardCard key={plot.path} expandable title={plot.title}>
          <img
            src={getModelArtifactUrl(plot.path)}
            alt={plot.title}
            loading="lazy"
            className="w-full rounded"
            style={{ backgroundColor: "white" }}
          />
        </DashboardCard>
      ))}
    </div>
  );
}

export default PlotGallery;
