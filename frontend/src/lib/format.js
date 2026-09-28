export const UTILITIES = {
  dominion_sc: { label: "Dominion Energy SC", short: "Dominion", color: "#2563eb" },
  georgia_power: { label: "Georgia Power", short: "Georgia Power", color: "#ea580c" },
};

export const utility = (id) =>
  UTILITIES[id] ?? { label: id, short: id, color: "#64748b" };

export const PROJECT_TYPES = {
  transmission_line: "Transmission line",
  substation: "Substation",
  other: "Other",
  unknown: "Unknown type",
};

export const TIMELINE = {
  overlap: { label: "Construction overlaps", tone: "bg-emerald-100 text-emerald-800" },
  unknown: { label: "Timing unknown", tone: "bg-slate-200 text-slate-700" },
  no_overlap: { label: "No overlap", tone: "bg-rose-100 text-rose-800" },
};

// Contract dates keep source precision (YYYY, YYYY-MM, YYYY-MM-DD); show them as-is.
export const dateOrUnknown = (value) => value ?? "Unknown";

export const hasCoordinates = (p) => p.latitude !== null && p.longitude !== null;

export const miles = (value) => `${value.toFixed(2)} mi`;

// Distances are for display only; ranking and eligibility come from the API.
export const RADIUS_MILES = 25;
export const METERS_PER_MILE = 1609.344;
