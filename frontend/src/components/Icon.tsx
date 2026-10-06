// Inline SVG icons (no emoji, no icon font). Stroke icons on a 24px grid, sized by the caller.
type P = { className?: string; title?: string };

function Svg({ className, title, children }: P & { children: React.ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"
      strokeLinejoin="round" className={className} role={title ? "img" : undefined} aria-label={title}
      aria-hidden={title ? undefined : true}>
      {children}
    </svg>
  );
}

export const StopIcon = (p: P) => (
  <Svg {...p}><path d="M7.9 2h8.2L22 7.9v8.2L16.1 22H7.9L2 16.1V7.9z" /><path d="M8.5 8.5l7 7M15.5 8.5l-7 7" /></Svg>
);
export const AlertIcon = (p: P) => (
  <Svg {...p}><path d="M10.3 3.9L1.8 18.5A2 2 0 0 0 3.5 21.5h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
    <path d="M12 9v4.5M12 17.3v.2" /></Svg>
);
export const CheckCircleIcon = (p: P) => (
  <Svg {...p}><circle cx="12" cy="12" r="10" /><path d="M7.5 12.5l3 3 6-6.5" /></Svg>
);
export const QuestionIcon = (p: P) => (
  <Svg {...p}><circle cx="12" cy="12" r="10" /><path d="M9.2 9.2a3 3 0 0 1 5.6 1.3c0 2-2.8 2.5-2.8 4" />
    <path d="M12 17.6v.2" /></Svg>
);
export const CheckIcon = (p: P) => <Svg {...p}><path d="M5 12.5l4.5 4.5L19 7" /></Svg>;
export const MinusIcon = (p: P) => <Svg {...p}><path d="M6 12h12" /></Svg>;
export const BangIcon = (p: P) => <Svg {...p}><path d="M12 5v9M12 19v.2" /></Svg>;
export const ArrowIcon = (p: P) => <Svg {...p}><path d="M5 12h14M13 6l6 6-6 6" /></Svg>;

export function TierIcon({ tier, className }: { tier: string; className?: string }) {
  const Icon = { red: StopIcon, amber: AlertIcon, green: CheckCircleIcon, grey: QuestionIcon }[tier] ?? QuestionIcon;
  return <Icon className={className} />;
}
