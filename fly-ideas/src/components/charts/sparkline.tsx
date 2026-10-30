/** Столбики без осей: показывают ритм работы, а не точные значения. */
export function Sparkline({ values, width = 132, height = 26, label }: { values: number[]; width?: number; height?: number; label?: string }) {
  if (values.length === 0) return null;
  const max = Math.max(1, ...values);
  const step = width / values.length;
  const bar = Math.max(2, Math.floor(step) - 3);
  return (
    <svg width={width} height={height} className="block" role="img" aria-label={label}>
      {values.map((v, i) => {
        const h = v > 0 ? Math.max(3, Math.round((v / max) * (height - 2))) : 1;
        return <rect key={i} x={Math.round(i * step)} y={height - h} width={bar} height={h} fill={v > 0 ? "var(--foreground)" : "var(--border)"} />;
      })}
    </svg>
  );
}
