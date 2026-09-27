import { hasCoordinates, miles, RADIUS_MILES, TIMELINE, utility } from "../lib/format.js";
import { Badge, UtilityDot } from "./ui.jsx";

function EmptyState({ projects }) {
  const validatedMapped = (id) =>
    projects.filter((p) => p.utility_id === id && p.review_status === "validated" && hasCoordinates(p)).length;
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
      <p className="font-medium text-slate-800">No coordination opportunities yet</p>
      <p className="mt-1">
        A pair needs validated projects from both utilities, with coordinates, within {RADIUS_MILES} miles.
        Most projects are not expected to overlap, and none are invented.
      </p>
      <ul className="mt-2 space-y-1">
        {["dominion_sc", "georgia_power"].map((id) => (
          <li key={id} className="flex items-center gap-2">
            <UtilityDot id={id} /> {utility(id).label}: {validatedMapped(id)} validated with coordinates
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function OpportunityList({ opportunities, projects, selection, onSelect }) {
  if (opportunities.length === 0) return <EmptyState projects={projects} />;
  const byId = Object.fromEntries(projects.map((p) => [p.project_id, p]));
  return (
    <ol className="space-y-2">
      {opportunities.map((o, index) => {
        const a = byId[o.project_id_a];
        const b = byId[o.project_id_b];
        const key = `${o.project_id_a}|${o.project_id_b}`;
        const active =
          selection?.kind === "opportunity" &&
          `${selection.opportunity.project_id_a}|${selection.opportunity.project_id_b}` === key;
        const timeline = TIMELINE[o.timeline_status];
        return (
          <li key={key}>
            <button
              onClick={() => onSelect(o)}
              className={`w-full rounded-lg border p-3 text-left transition hover:border-slate-400 ${
                active ? "border-slate-900 bg-slate-50 ring-1 ring-slate-900" : "border-slate-200 bg-white"
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1 space-y-1">
                  {[a, b].map((p, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <UtilityDot id={p?.utility_id} />
                      <span className="truncate">{p?.project_name ?? [o.project_id_a, o.project_id_b][i]}</span>
                    </div>
                  ))}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <Badge tone="bg-slate-900 text-white">{miles(o.distance_miles)}</Badge>
                    <Badge tone={timeline.tone}>{timeline.label}</Badge>
                    {o.location_uncertain && <Badge tone="bg-amber-100 text-amber-800">Provisional location</Badge>}
                  </div>
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
