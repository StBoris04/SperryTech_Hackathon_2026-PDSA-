import { useEffect, useMemo, useState } from "react";
import { getOpportunities, getProjects } from "./api.js";
import MapView from "./components/MapView.jsx";
import OpportunityList from "./components/OpportunityList.jsx";
import ProjectList from "./components/ProjectList.jsx";
import { OpportunityDetails, ProjectDetails } from "./components/Details.jsx";
import { Stat, UtilityDot } from "./components/ui.jsx";
import { hasCoordinates, RADIUS_MILES, UTILITIES } from "./lib/format.js";

function useRequest(load) {
  const [state, setState] = useState({ status: "loading" });
  useEffect(() => {
    load()
      .then((data) => setState({ status: "ok", data }))
      .catch((error) => setState({ status: "error", error: error.message }));
  }, [load]);
  return state;
}

function Legend() {
  return (
    <div className="absolute bottom-4 left-4 z-[1000] space-y-1 rounded-lg bg-white/95 px-3 py-2 text-xs shadow-md">
      {Object.entries(UTILITIES).map(([id, u]) => (
        <div key={id} className="flex items-center gap-2">
          <UtilityDot id={id} /> {u.label}
        </div>
      ))}
      <div className="flex items-center gap-2 text-slate-500">
        <span className="inline-block size-2.5 rounded-full border border-dashed border-slate-500 bg-slate-300/50" />
        Approximate location
      </div>
      <div className="flex items-center gap-2 text-slate-500">
        <span className="inline-block h-0 w-4 border-t-2 border-dashed border-slate-500" />
        {RADIUS_MILES}-mile radius of selected project
      </div>
    </div>
  );
}

function Methodology() {
  return (
    <details className="border-t border-slate-200 px-4 py-3 text-xs text-slate-600">
      <summary className="cursor-pointer font-medium text-slate-700">How opportunities are ranked</summary>
      <ul className="mt-2 list-disc space-y-1 pl-4">
        <li>Only validated projects from different utilities, both with coordinates, are compared.</li>
        <li>
          Primary signal: geodesic distance of {RADIUS_MILES} miles or less between representative points
          (exactly {RADIUS_MILES} miles qualifies).
        </li>
        <li>Secondary signal: overlapping construction windows. Missing dates are shown as unknown, never guessed.</li>
        <li>Ranked by distance, then overlap, unknown, no overlap. Approximate locations are marked provisional.</li>
        <li>Public data only. A flagged pair is a lead to investigate, not proof that sharing is feasible.</li>
      </ul>
    </details>
  );
}

export default function App() {
  const projectsReq = useRequest(getProjects);
  const opportunitiesReq = useRequest(getOpportunities);
  const projects = projectsReq.status === "ok" ? projectsReq.data : [];
  const opportunities = opportunitiesReq.status === "ok" ? opportunitiesReq.data : [];

  const [tab, setTab] = useState("opportunities");
  const [selection, setSelection] = useState(null);
  const [utilities, setUtilities] = useState(new Set(Object.keys(UTILITIES)));
  const [query, setQuery] = useState("");
  const [onlyMapped, setOnlyMapped] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return projects.filter(
      (p) =>
        utilities.has(p.utility_id) &&
        (!onlyMapped || hasCoordinates(p)) &&
        (!q || `${p.project_name} ${p.location_text ?? ""} ${p.project_id}`.toLowerCase().includes(q)),
    );
  }, [projects, utilities, query, onlyMapped]);

  const highlightedIds = useMemo(
    () => new Set(opportunities.flatMap((o) => [o.project_id_a, o.project_id_b])),
    [opportunities],
  );

  const count = (id) => projects.filter((p) => p.utility_id === id).length;
  const mappedCount = projects.filter(hasCoordinates).length;
  const selectedProject =
    selection?.kind === "project" ? projects.find((p) => p.project_id === selection.projectId) : null;

  const toggleUtility = (id) =>
    setUtilities((current) => {
      const next = new Set(current);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const error = projectsReq.status === "error" ? projectsReq.error : opportunitiesReq.status === "error" ? opportunitiesReq.error : null;

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 px-5 py-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">
            Grid<span className="text-amber-400">Lock</span>
          </h1>
          <p className="text-xs text-slate-400">
            Coordination opportunities between planned Dominion Energy SC and Georgia Power transmission work
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Stat label="Dominion Energy SC" value={count("dominion_sc")} />
          <Stat label="Georgia Power" value={count("georgia_power")} />
          <Stat label="On the map" value={mappedCount} hint="projects with coordinates" />
          <Stat label="Opportunities" value={opportunities.length} hint={`within ${RADIUS_MILES} mi`} />
        </div>
      </header>

      {error && (
        <div className="bg-rose-600 px-5 py-2 text-sm text-white">
          {error}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-96 shrink-0 flex-col border-r border-slate-200 bg-white">
          <div className="flex border-b border-slate-200">
            {[
              ["opportunities", `Opportunities (${opportunities.length})`],
              ["projects", `Projects (${filtered.length})`],
            ].map(([id, label]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex-1 px-4 py-3 text-sm font-medium ${
                  tab === id ? "border-b-2 border-slate-900 text-slate-900" : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "projects" && (
            <div className="space-y-2 border-b border-slate-200 p-3">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search name, location or ID"
                className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-slate-500"
              />
              <div className="flex flex-wrap gap-3 text-xs">
                {Object.entries(UTILITIES).map(([id, u]) => (
                  <label key={id} className="flex items-center gap-1.5">
                    <input type="checkbox" checked={utilities.has(id)} onChange={() => toggleUtility(id)} />
                    <UtilityDot id={id} /> {u.short}
                  </label>
                ))}
                <label className="flex items-center gap-1.5">
                  <input type="checkbox" checked={onlyMapped} onChange={(e) => setOnlyMapped(e.target.checked)} />
                  On map only
                </label>
              </div>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto">
            {projectsReq.status === "loading" || opportunitiesReq.status === "loading" ? (
              <p className="p-4 text-sm text-slate-500">Loading projects and opportunities…</p>
            ) : tab === "opportunities" ? (
              <div className="p-3">
                <OpportunityList
                  opportunities={opportunities}
                  projects={projects}
                  selection={selection}
                  onSelect={(opportunity) => setSelection({ kind: "opportunity", opportunity })}
                />
              </div>
            ) : (
              <ProjectList
                projects={filtered}
                selection={selection}
                onSelect={(projectId) => setSelection({ kind: "project", projectId })}
              />
            )}
          </div>
          <Methodology />
        </aside>

        <main className="relative min-w-0 flex-1">
          <MapView
            projects={filtered}
            highlightedIds={highlightedIds}
            selection={selection}
            onSelectProject={(projectId) => setSelection({ kind: "project", projectId })}
          />
          <Legend />
          {projects.length > 0 && mappedCount < projects.length && (
            <div className="absolute top-3 left-1/2 z-[1000] -translate-x-1/2 rounded-full bg-white/95 px-3 py-1 text-xs text-slate-600 shadow">
              {projects.length - mappedCount} projects have no verified coordinates yet and appear only in the list
            </div>
          )}
        </main>

        {selection && (
          <section className="w-96 shrink-0 overflow-y-auto border-l border-slate-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {selection.kind === "opportunity" ? "Opportunity" : "Project"}
              </h2>
              <button onClick={() => setSelection(null)} className="text-slate-400 hover:text-slate-700" aria-label="Close">
                ✕
              </button>
            </div>
            {selection.kind === "opportunity" ? (
              <OpportunityDetails opportunity={selection.opportunity} projects={projects} />
            ) : selectedProject ? (
              <ProjectDetails project={selectedProject} />
            ) : null}
          </section>
        )}
      </div>
    </div>
  );
}
