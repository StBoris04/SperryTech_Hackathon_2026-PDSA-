import { useEffect, useState } from "react";
import { API_BASE_URL, getHealth, getOpportunities, getProjects } from "./api.js";

const UTILITY_LABELS = { dominion_sc: "Dominion SC", georgia_power: "Georgia Power" };

function useRequest(load) {
  const [state, setState] = useState({ status: "loading" });
  useEffect(() => {
    load()
      .then((data) => setState({ status: "ok", data }))
      .catch((error) => setState({ status: "error", error: error.message }));
  }, [load]);
  return state;
}

function Status({ label, state, summary }) {
  const text =
    state.status === "loading"
      ? "loading…"
      : state.status === "error"
        ? state.error
        : summary(state.data);
  return (
    <li className={state.status}>
      <strong>{label}:</strong> {text}
    </li>
  );
}

function countBy(items, key) {
  return items.reduce((counts, item) => {
    counts[item[key]] = (counts[item[key]] ?? 0) + 1;
    return counts;
  }, {});
}

export default function App() {
  const health = useRequest(getHealth);
  const projects = useRequest(getProjects);
  const opportunities = useRequest(getOpportunities);

  return (
    <main>
      <h1>GridLock</h1>
      <p>
        API: <code>{API_BASE_URL}</code>
      </p>
      <ul>
        <Status label="GET /health" state={health} summary={(d) => d.status} />
        <Status
          label="GET /projects"
          state={projects}
          summary={(d) => {
            const byUtility = countBy(d, "utility_id");
            const located = d.filter((p) => p.latitude !== null).length;
            return `${d.length} projects (${Object.entries(byUtility)
              .map(([u, n]) => `${n} ${UTILITY_LABELS[u] ?? u}`)
              .join(", ")}); ${located} with coordinates`;
          }}
        />
        <Status
          label="GET /opportunities"
          state={opportunities}
          summary={(d) =>
            d.length === 0
              ? "0 opportunities (expected until Georgia records are validated)"
              : `${d.length} opportunities`
          }
        />
      </ul>

      {projects.status === "ok" && (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Utility</th>
              <th>Name</th>
              <th>Type</th>
              <th>Location quality</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {projects.data.map((p) => (
              <tr key={p.project_id}>
                <td>{p.project_id}</td>
                <td>{UTILITY_LABELS[p.utility_id] ?? p.utility_id}</td>
                <td>{p.project_name}</td>
                <td>{p.project_type}</td>
                <td>{p.location_quality}</td>
                <td>{p.review_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <style>{`
        body { font-family: system-ui, sans-serif; margin: 2rem; }
        li.error { color: #b00020; }
        li.ok { color: #1b5e20; }
        table { border-collapse: collapse; margin-top: 1rem; font-size: 0.9rem; }
        th, td { border: 1px solid #ccc; padding: 0.25rem 0.5rem; text-align: left; }
      `}</style>
    </main>
  );
}
