import {
  cloneElement,
  isValidElement,
  useId,
  type ReactNode,
  type ReactElement,
} from "react";
import {
  ArrowLeft,
  Building2,
  ClipboardCheck,
  Home,
  ListChecks,
  UserRound,
  Wifi,
} from "lucide-react";
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function Card({
  title,
  children,
  action,
  collapsible = false,
}: {
  title?: string;
  children: ReactNode;
  action?: ReactNode;
  collapsible?: boolean;
}) {
  if (collapsible)
    return (
      <details className="card report-fold">
        <summary>{title}</summary>
        <div className="report-fold-body">{children}</div>
      </details>
    );
  return (
    <section className="card">
      {title && (
        <div className="card-title">
          <h2>{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
export function Empty({
  title = "Belum tersedia",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Wifi size={28} />
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}
export function Message({
  children,
  error = false,
}: {
  children: ReactNode;
  error?: boolean;
}) {
  return (
    <p
      className={"message " + (error ? "error" : "")}
      role={error ? "alert" : "status"}
    >
      {children}
    </p>
  );
}
export function Meter({
  done,
  total,
  label = "Progress test area",
}: {
  done: number;
  total: number;
  label?: string;
}) {
  return (
    <div className="meter">
      <div>
        <span>{label}</span>
        <strong>{total ? `${done}/${total} area` : "Belum diperiksa"}</strong>
      </div>
      <progress value={done} max={total || 1} aria-label={label} />
    </div>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <label className="field">
      <span id={id}>{label}</span>
      {isValidElement(children)
        ? cloneElement(
            children as ReactElement<{ "aria-labelledby": string }>,
            { "aria-labelledby": id },
          )
        : children}
    </label>
  );
}
export type Route =
  | "home"
  | "schedule"
  | "hotel"
  | "report"
  | "floors"
  | "point"
  | "review"
  | "profile";
export function Header({
  title,
  subtitle,
  online,
  back,
}: {
  title: string;
  subtitle?: string;
  online: boolean;
  back?: () => void;
}) {
  return (
    <header className="app-header">
      <div className="header-row">
        {back ? (
          <button className="icon-button" onClick={back} aria-label="Kembali">
            <ArrowLeft />
          </button>
        ) : (
          <span className="brand-icon">
            <img
              src="/brand/nusa-maintenance-icon.png"
              alt="Nusa Maintenance"
              width="44"
              height="44"
            />
          </span>
        )}
        <div>
          <p className="eyebrow">NUSA MAINTENANCE</p>
          <h1>{title}</h1>
          {subtitle && <p className="header-subtitle">{subtitle}</p>}
        </div>
      </div>
      <span className="connection">
        <i className={online ? "online" : "offline"} />
        {online ? "Online" : "Offline"}
      </span>
    </header>
  );
}
export function BottomNav({
  route,
  go,
}: {
  route: Route;
  go: (r: Route) => void;
}) {
  return (
    <nav className="bottom-nav" aria-label="Navigasi utama">
      {(
        [
          { route: "home", label: "Beranda", Icon: Home },
          { route: "schedule", label: "Jadwal", Icon: Building2 },
          { route: "review", label: "Review", Icon: ClipboardCheck },
          { route: "profile", label: "Profil", Icon: UserRound },
        ] as const
      ).map(({ route: r, label, Icon }) => (
        <button
          key={r}
          onClick={() => go(r)}
          aria-current={route === r ? "page" : undefined}
        >
          <Icon size={21} />
          <span>{label}</span>
        </button>
      ))}
    </nav>
  );
}
export function Steps({
  active,
  go,
}: {
  active: Route;
  go: (r: Route) => void;
}) {
  return (
    <nav className="steps" aria-label="Tahap maintenance">
      {(
        [
          { route: "hotel", label: "Hotel", Icon: Building2 },
          { route: "report", label: "Laporan", Icon: ListChecks },
          { route: "floors", label: "Network Test", Icon: Wifi },
          { route: "review", label: "Review", Icon: ClipboardCheck },
        ] as const
      ).map(({ route, label, Icon }) => (
        <button
          key={route}
          aria-current={
            active === route || (active === "point" && route === "floors")
              ? "step"
              : undefined
          }
          onClick={() => go(route)}
        >
          <Icon size={16} />
          {label}
        </button>
      ))}
    </nav>
  );
}
