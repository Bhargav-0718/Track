import { cn, getConfidenceConfig } from "@/lib/utils/format";

interface ConfidenceBadgeProps {
  level: string;
  score?: number;
  className?: string;
}

export function ConfidenceBadge({ level, score, className }: ConfidenceBadgeProps) {
  const config = getConfidenceConfig(level);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold",
        config.bg,
        config.text,
        className
      )}
    >
      {/* Dots */}
      <span className="flex gap-0.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "w-1 h-1 rounded-full transition-all",
              i < config.dots ? "opacity-100" : "opacity-25"
            )}
            style={{ background: "currentColor" }}
          />
        ))}
      </span>
      {config.label}
    </span>
  );
}
