const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function getJson(path) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`);
  } catch {
    // fetch rejects without a status on network and CORS failures.
    throw new Error(
      `Could not reach ${API_BASE_URL}${path}. Is the API running, and does ` +
        `GRIDLOCK_CORS_ORIGINS include ${window.location.origin}?`,
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? `${path} returned HTTP ${response.status}`);
  }
  return body;
}

export { API_BASE_URL };
export const getHealth = () => getJson("/health");
export const getProjects = () => getJson("/projects").then((b) => b.projects);
export const getOpportunities = () =>
  getJson("/opportunities").then((b) => b.opportunities);
