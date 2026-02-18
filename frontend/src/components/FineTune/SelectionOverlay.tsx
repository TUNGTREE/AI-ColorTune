import { useRef, useState, useCallback, useEffect } from 'react';
import type { SelectionRegion } from '../../types';

interface Props {
  width: number;
  height: number;
  tool: 'rect' | 'ellipse' | null;
  regions: SelectionRegion[];
  activeRegionIndex: number | null;
  onRegionAdd: (region: SelectionRegion) => void;
  onRegionUpdate: (index: number, region: SelectionRegion) => void;
  onRegionSelect: (index: number | null) => void;
}

export default function SelectionOverlay({
  width,
  height,
  tool,
  regions,
  activeRegionIndex,
  onRegionAdd,
  onRegionUpdate,
  onRegionSelect,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drawing, setDrawing] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [currentRect, setCurrentRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [dragging, setDragging] = useState<{ regionIdx: number; offsetX: number; offsetY: number } | null>(null);

  const getCanvasPos = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return { x: 0, y: 0 };
      const rect = canvas.getBoundingClientRect();
      return {
        x: (e.clientX - rect.left) / rect.width,
        y: (e.clientY - rect.top) / rect.height,
      };
    },
    [],
  );

  const hitTest = useCallback(
    (pos: { x: number; y: number }): number | null => {
      for (let i = regions.length - 1; i >= 0; i--) {
        const r = regions[i];
        if (
          pos.x >= r.x &&
          pos.x <= r.x + r.width &&
          pos.y >= r.y &&
          pos.y <= r.y + r.height
        ) {
          return i;
        }
      }
      return null;
    },
    [regions],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const pos = getCanvasPos(e);

      // If no tool is active, try to select/drag existing region
      if (!tool) {
        const hit = hitTest(pos);
        onRegionSelect(hit);
        if (hit !== null) {
          const r = regions[hit];
          setDragging({ regionIdx: hit, offsetX: pos.x - r.x, offsetY: pos.y - r.y });
        }
        return;
      }

      // Start drawing a new region
      setDrawing(true);
      setDragStart(pos);
      setCurrentRect(null);
    },
    [tool, getCanvasPos, hitTest, onRegionSelect, regions],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const pos = getCanvasPos(e);

      // Handle dragging existing region
      if (dragging) {
        const r = regions[dragging.regionIdx];
        const newX = Math.max(0, Math.min(1 - r.width, pos.x - dragging.offsetX));
        const newY = Math.max(0, Math.min(1 - r.height, pos.y - dragging.offsetY));
        onRegionUpdate(dragging.regionIdx, { ...r, x: newX, y: newY });
        return;
      }

      // Handle drawing new region
      if (!drawing || !dragStart) return;
      const x = Math.min(dragStart.x, pos.x);
      const y = Math.min(dragStart.y, pos.y);
      const w = Math.abs(pos.x - dragStart.x);
      const h = Math.abs(pos.y - dragStart.y);
      setCurrentRect({ x, y, w, h });
    },
    [drawing, dragStart, dragging, getCanvasPos, onRegionUpdate, regions],
  );

  const handleMouseUp = useCallback(() => {
    if (dragging) {
      setDragging(null);
      return;
    }

    if (drawing && currentRect && tool && currentRect.w > 0.01 && currentRect.h > 0.01) {
      onRegionAdd({
        type: tool,
        x: currentRect.x,
        y: currentRect.y,
        width: currentRect.w,
        height: currentRect.h,
        feather: 20,
      });
    }
    setDrawing(false);
    setDragStart(null);
    setCurrentRect(null);
  }, [drawing, currentRect, tool, onRegionAdd, dragging]);

  // Draw regions on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    const drawRegion = (r: SelectionRegion, isActive: boolean, isPreview: boolean) => {
      const px = r.x * width;
      const py = r.y * height;
      const pw = r.width * width;
      const ph = r.height * height;

      ctx.save();
      ctx.strokeStyle = isActive ? '#5b6abf' : 'rgba(255,255,255,0.6)';
      ctx.lineWidth = isActive ? 2 : 1;
      ctx.setLineDash(isPreview ? [6, 4] : []);

      if (r.type === 'rect') {
        ctx.strokeRect(px, py, pw, ph);
        ctx.fillStyle = isActive
          ? 'rgba(91, 106, 191, 0.15)'
          : 'rgba(255, 255, 255, 0.05)';
        ctx.fillRect(px, py, pw, ph);
      } else {
        ctx.beginPath();
        ctx.ellipse(px + pw / 2, py + ph / 2, pw / 2, ph / 2, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = isActive
          ? 'rgba(91, 106, 191, 0.15)'
          : 'rgba(255, 255, 255, 0.05)';
        ctx.fill();
      }
      ctx.restore();

      // Draw index label
      if (!isPreview) {
        ctx.save();
        ctx.fillStyle = isActive ? '#5b6abf' : 'rgba(255,255,255,0.7)';
        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.fillText(
          r.type === 'rect' ? 'R' : 'E',
          px + 4,
          py + 14,
        );
        ctx.restore();
      }
    };

    // Draw existing regions
    regions.forEach((r, i) => {
      drawRegion(r, i === activeRegionIndex, false);
    });

    // Draw preview region while drawing
    if (currentRect && tool) {
      drawRegion(
        {
          type: tool,
          x: currentRect.x,
          y: currentRect.y,
          width: currentRect.w,
          height: currentRect.h,
          feather: 20,
        },
        true,
        true,
      );
    }
  }, [width, height, regions, activeRegionIndex, currentRect, tool]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        cursor: tool ? 'crosshair' : dragging ? 'grabbing' : 'default',
        pointerEvents: tool || regions.length > 0 ? 'auto' : 'none',
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    />
  );
}
