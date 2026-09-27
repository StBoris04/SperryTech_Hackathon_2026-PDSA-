import { utility } from "../lib/format.js";

export function UtilityDot({ id, className = "" }) {
  return (
    <span
      className={`inline-block size-2.5 shrink-0 rounded-full ${className}`}
      style={{ backgroundColor: utility(id).color }}
    />
  );
}

export function Badge({ children, tone = "bg-slate-100 text-slate-700" }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>
      {children}
    </span>
  );
}

export function Stat({ label, value, hint }) {
  return (
    <div className="rounded-lg bg-white/10 px-3 py-2">
      <div className="text-xl font-semibold leading-tight text-white">{value}</div>
      <div className="text-xs text-slate-300">{label}</div>
      {hint && <div className="text-[11px] text-slate-400">{hint}</div>}
    </div>
  );
}

export function Field({ label, children }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-800">{children}</dd>
    </div>
  );
}
