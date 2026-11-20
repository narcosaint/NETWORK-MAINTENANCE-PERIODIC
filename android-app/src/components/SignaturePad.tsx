import { useEffect, useRef } from "react";
import type { Strokes } from "../services/completion";
export function SignaturePad({
  value,
  onChange,
  disabled,
}: {
  value: Strokes;
  onChange: (strokes: Strokes) => void;
  disabled: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null),
    drawing = useRef<Strokes | null>(null);
  useEffect(() => {
    const node = canvas.current,
      ctx = node?.getContext("2d");
    if (!node || !ctx) return;
    ctx.clearRect(0, 0, node.width, node.height);
    ctx.strokeStyle = "#133e35";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    for (const stroke of value) {
      ctx.beginPath();
      stroke.forEach(([x, y], i) => {
        if (i) ctx.lineTo(x * node.width, y * node.height);
        else ctx.moveTo(x * node.width, y * node.height);
      });
      ctx.stroke();
    }
  }, [value]);
  const coordinate = (
    event: React.PointerEvent<HTMLCanvasElement>,
  ): [number, number] => {
    const r = event.currentTarget.getBoundingClientRect();
    return [
      Math.max(0, Math.min(1, (event.clientX - r.left) / r.width)),
      Math.max(0, Math.min(1, (event.clientY - r.top) / r.height)),
    ];
  };
  return (
    <div>
      <canvas
        ref={canvas}
        width={660}
        height={240}
        className="signature-pad"
        aria-label="Area tanda tangan PIC"
        role="img"
        onPointerDown={(e) => {
          if (disabled) return;
          e.currentTarget.setPointerCapture(e.pointerId);
          drawing.current = [...value, [coordinate(e)]];
          onChange(drawing.current);
        }}
        onPointerMove={(e) => {
          if (disabled || !drawing.current) return;
          const next = drawing.current.map((s, i) =>
            i === drawing.current!.length - 1 ? [...s, coordinate(e)] : s,
          );
          if (next.reduce((n, s) => n + s.length, 0) > 8000) return;
          drawing.current = next;
          onChange(next);
        }}
        onPointerUp={() => {
          drawing.current = null;
        }}
        onPointerCancel={() => {
          drawing.current = null;
        }}
      />
      <button
        className="secondary"
        disabled={disabled || !value.length}
        onClick={() => {
          drawing.current = null;
          onChange([]);
        }}
      >
        Hapus goresan
      </button>
    </div>
  );
}
