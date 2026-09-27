import { useEffect } from "react";
import {
  Circle,
  CircleMarker,
  MapContainer,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import { hasCoordinates, METERS_PER_MILE, RADIUS_MILES, utility } from "../lib/format.js";

const DEFAULT_CENTER = [32.8, -82.0];

function FitTo({ points }) {
  const map = useMap();
  const key = JSON.stringify(points);
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 9);
    else if (points.length > 1) map.fitBounds(points, { padding: [48, 48], maxZoom: 11 });
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export default function MapView({ projects, highlightedIds, selection, onSelectProject }) {
  const mapped = projects.filter(hasCoordinates);
  const byId = Object.fromEntries(projects.map((p) => [p.project_id, p]));

  let focus = mapped.map((p) => [p.latitude, p.longitude]);
  let pair = null;
  let radiusProject = null;
  if (selection?.kind === "opportunity") {
    pair = [byId[selection.opportunity.project_id_a], byId[selection.opportunity.project_id_b]]
      .filter((p) => p && hasCoordinates(p));
    if (pair.length) focus = pair.map((p) => [p.latitude, p.longitude]);
  } else if (selection?.kind === "project") {
    const p = byId[selection.projectId];
    if (p && hasCoordinates(p)) {
      radiusProject = p;
      focus = [[p.latitude, p.longitude]];
    }
  }

  const selectedIds = new Set(
    selection?.kind === "opportunity"
      ? [selection.opportunity.project_id_a, selection.opportunity.project_id_b]
      : selection?.kind === "project"
        ? [selection.projectId]
        : [],
  );

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={7} className="h-full w-full" preferCanvas>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitTo points={focus} />

      {radiusProject && (
        <Circle
          center={[radiusProject.latitude, radiusProject.longitude]}
          radius={RADIUS_MILES * METERS_PER_MILE}
          pathOptions={{ color: utility(radiusProject.utility_id).color, weight: 1, dashArray: "6 6", fillOpacity: 0.05 }}
        />
      )}

      {pair?.length === 2 && (
        <Polyline
          positions={pair.map((p) => [p.latitude, p.longitude])}
          pathOptions={{ color: "#0f172a", weight: 3, dashArray: "8 6" }}
        />
      )}

      {mapped.map((p) => {
        const color = utility(p.utility_id).color;
        const selected = selectedIds.has(p.project_id);
        const inOpportunity = highlightedIds.has(p.project_id);
        const approximate = p.location_quality !== "verified";
        return (
          <CircleMarker
            key={p.project_id}
            center={[p.latitude, p.longitude]}
            radius={selected ? 11 : inOpportunity ? 8 : 6}
            pathOptions={{
              color: selected ? "#0f172a" : color,
              weight: selected ? 3 : 2,
              fillColor: color,
              fillOpacity: approximate ? 0.35 : 0.85,
              dashArray: approximate ? "3 3" : null,
            }}
            eventHandlers={{ click: () => onSelectProject(p.project_id) }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              <div className="text-xs">
                <div className="font-semibold">{p.project_name}</div>
                <div>
                  {utility(p.utility_id).label}
                  {approximate && " · approximate location"}
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
