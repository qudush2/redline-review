import {
  BookOpen,
  Briefcase,
  ChartColumn,
  FileText,
  CircleHelp,
  House,
  Inbox,
  PenLine,
  Settings,
} from "lucide-react";

// Left navigation rail. Only "Contracts" is real; the rest show where
// this screen would sit inside a full legal workspace.
const mainItems = [
  { label: "Home", icon: House },
  { label: "Matters", icon: Briefcase },
  { label: "Contracts", icon: FileText, active: true },
  { label: "Playbooks", icon: BookOpen },
  { label: "Intake", icon: Inbox, badge: 3 },
  { label: "Reports", icon: ChartColumn },
];

const footerItems = [
  { label: "Settings", icon: Settings },
  { label: "Help", icon: CircleHelp },
];

export default function AppNav() {
  return (
    <nav className="flex w-[68px] shrink-0 flex-col items-center bg-espresso py-4 text-[#cfc6ba]">
      <div className="mb-6 flex h-9 w-9 items-center justify-center rounded-lg bg-terracotta text-espresso">
        <PenLine size={18} strokeWidth={2.25} />
      </div>

      <ul className="flex flex-1 flex-col gap-1">
        {mainItems.map((item) => (
          <li key={item.label}>
            <NavButton {...item} />
          </li>
        ))}
      </ul>

      <ul className="flex flex-col gap-1">
        {footerItems.map((item) => (
          <li key={item.label}>
            <NavButton {...item} />
          </li>
        ))}
      </ul>
    </nav>
  );
}

type NavButtonProps = {
  label: string;
  icon: React.ComponentType<{ size?: number }>;
  active?: boolean;
  badge?: number;
};

function NavButton({ label, icon: Icon, active, badge }: NavButtonProps) {
  return (
    <button
      title={label}
      className={`relative flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium transition-colors ${
        active ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white"
      }`}
    >
      <Icon size={19} />
      {label}
      {badge ? (
        <span className="absolute right-2 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-terracotta px-1 text-[9px] font-semibold text-espresso">
          {badge}
        </span>
      ) : null}
    </button>
  );
}
