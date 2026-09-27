import { dateOrUnknown, hasCoordinates, miles, PROJECT_TYPES, TIMELINE, utility } from "../lib/format.js";
import { Badge, Field, UtilityDot } from "./ui.jsx";

function SourceLink({ source }) {
  const isUrl = /^https?:\/\//.test(source.reference);
  const name = isUrl ? new URL(source.reference).hostname : source.reference.split("/").pop();
  return (
    <li className="rounded-md bg-slate-50 p-2 text-xs">
      {isUrl ? (
        <a href={source.reference} target="_blank" rel="noreferrer" className="font-medium text-blue-700 hover:underline">
          {name}
        </a>
      ) : (
        <span className="font-medium" title={source.reference}>{name}</span>
      )}
      <span className="text-slate-500"> · {source.locator}</span>
      <div className="mt-0.5 text-slate-500">Supports: {source.supports.join(", ")}</div>
    </li>
  );
}

export function ProjectDetails({ project, compact = false }) {
  const u = utility(project.utility_id);
  return (
    <div className="space-y-3">
      <div>
        <div className="flex items-center gap-2 text-xs font-medium" style={{ color: u.color }}>
          <UtilityDot id={project.utility_id} /> {u.label}
          <span className="text-slate-400">· {project.project_id}</span>
        </div>
        <h3 className="mt-1 font-semibold leading-snug text-slate-900">{project.project_name}</h3>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          <Badge>{PROJECT_TYPES[project.project_type]}</Badge>
          {project.state && <Badge>{project.state}</Badge>}
          {project.review_status === "validated" ? (
            <Badge tone="bg-emerald-50 text-emerald-700">Validated</Badge>
          ) : (
            <Badge tone="bg-amber-50 text-amber-700">Needs review</Badge>
          )}
        </div>
      </div>
      {project.description && <p className="text-sm text-slate-600">{project.description}</p>}
      <dl className="grid grid-cols-3 gap-3">
        <Field label="Construction start">{dateOrUnknown(project.construction_start)}</Field>
        <Field label="Construction end">{dateOrUnknown(project.construction_end)}</Field>
        <Field label="In service">{dateOrUnknown(project.in_service_date)}</Field>
      </dl>
      {project.schedule_text && <p className="text-xs italic text-slate-500">“{project.schedule_text}”</p>}
      <dl className="space-y-2">
        <Field label="Location">
          {project.location_text ?? "Not stated"}
          <span className="ml-1 text-xs text-slate-500">
            ({hasCoordinates(project)
              ? `${project.location_quality} point, ${project.latitude.toFixed(4)}, ${project.longitude.toFixed(4)}`
              : "no coordinates; not shown on map"})
          </span>
        </Field>
        {!compact && project.location_method && <Field label="Location method">{project.location_method}</Field>}
        {!compact && project.notes && <Field label="Notes">{project.notes}</Field>}
      </dl>
      {!compact && (
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Source evidence</div>
          <ul className="mt-1 space-y-1.5">
            {project.sources.map((s, i) => <SourceLink key={i} source={s} />)}
          </ul>
        </div>
      )}
    </div>
  );
}

export function OpportunityDetails({ opportunity, projects }) {
  const byId = Object.fromEntries(projects.map((p) => [p.project_id, p]));
  const timeline = TIMELINE[opportunity.timeline_status];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-2xl font-semibold text-slate-900">{miles(opportunity.distance_miles)}</span>
        <Badge tone={timeline.tone}>{timeline.label}</Badge>
        {opportunity.location_uncertain && <Badge tone="bg-amber-100 text-amber-800">Provisional location</Badge>}
      </div>
      <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-700">{opportunity.reason}</p>
      <p className="text-xs text-slate-500">
        Distance between representative points (PostGIS geography). A candidate for investigation into shared crews,
        equipment, rights-of-way, or infrastructure, not proof that sharing is feasible. No savings estimate is shown
        because none has been calculated from public data yet.
      </p>
      {[opportunity.project_id_a, opportunity.project_id_b].map((id) =>
        byId[id] ? (
          <div key={id} className="border-t border-slate-100 pt-3">
            <ProjectDetails project={byId[id]} compact />
          </div>
        ) : (
          <p key={id} className="text-sm text-rose-700">Project {id} is missing from /projects.</p>
        ),
      )}
    </div>
  );
}
