// Wraps a control that isn't built yet, so people know not to click it.
//
// What it does:
//   - grays the control out
//   - makes it unclickable and skips it when tabbing (the `inert` attribute)
//   - shows a small tooltip on hover explaining why
//
// Example:
//   <ComingSoon><button>Export .docx</button></ComingSoon>
//   <ComingSoon side="right" label="Not in this prototype"><NavButton … /></ComingSoon>

type ComingSoonProps = {
  children: React.ReactNode;
  label?: string; // tooltip text
  side?: "bottom" | "right" | "top"; // where the tooltip appears
  className?: string;
};

const tooltipPosition = {
  bottom: "left-1/2 top-full mt-1.5 -translate-x-1/2",
  top: "left-1/2 bottom-full mb-1.5 -translate-x-1/2",
  right: "left-full top-1/2 ml-2 -translate-y-1/2",
};

export default function ComingSoon({ children, label = "Not in this prototype", side = "bottom", className = "" }: ComingSoonProps) {
  return (
    <span className={`group/soon relative inline-flex cursor-not-allowed ${className}`} aria-disabled="true">
      {/* The control itself: faded, and `inert` so it can't be clicked or focused. */}
      <span inert className="flex w-full opacity-40 grayscale">
        {children}
      </span>

      <span
        role="tooltip"
        className={`pointer-events-none invisible absolute z-50 whitespace-nowrap rounded-md bg-espresso px-2 py-1 text-[11px] font-medium text-white opacity-0 shadow-lg transition-opacity group-hover/soon:visible group-hover/soon:opacity-100 ${tooltipPosition[side]}`}
      >
        {label}
      </span>
    </span>
  );
}
