import { hasCoordinates, PROJECT_TYPES } from "../lib/format.js";
import { Badge, UtilityDot } from "./ui.jsx";

export default function ProjectList({ projects, selection, onSelect }) {
  if (projects.length === 0)
    return <p className="p-4 text-sm text-slate-500">No projects match these filters.</p>;
  return (
    <ul className="divide-y divide-slate-100">
      {projects.map((p) => {
        const active = selection?.kind === "project" && selection.projectId === p.project_id;
        return (
          <li key={p.project_id}>
            <button
              onClick={() => onSelect(p.project_id)}
              className={`w-full px-3 py-2.5 text-left hover:bg-slate-50 ${active ? "bg-slate-100" : ""}`}
            >
              <div className="flex items-center gap-2">
                <UtilityDot id={p.utility_id} />
                <span className="truncate text-sm font-medium">{p.project_name}</span>
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5 pl-4.5">
                <Badge>{PROJECT_TYPES[p.project_type]}</Badge>
                {p.review_status === "validated" ? (
                  <Badge tone="bg-emerald-50 text-emerald-700">Validated</Badge>
                ) : (
                  <Badge tone="bg-amber-50 text-amber-700">Needs review</Badge>
                )}
                {!hasCoordinates(p) && <Badge tone="bg-slate-100 text-slate-500">Not on map</Badge>}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
