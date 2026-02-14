import { useRef, useState, useCallback, useEffect } from 'react';

interface Props {
  beforeSrc: string;
  afterSrc: string;
  height?: number;
}

export default function BeforeAfterSlider({ beforeSrc, afterSrc, height = 400 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState(50);
  const [dragging, setDragging] = useState(false);
  const [imgNaturalSize, setImgNaturalSize] = useState<{ w: number; h: number } | null>(null);

  // Get natural image dimensions
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      setImgNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
    };
    img.src = beforeSrc;
  }, [beforeSrc]);

  const updatePosition = useCallback(
    (clientX: number) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = clientX - rect.left;
      const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setPosition(pct);
    },
    [],
  );

  const handleMouseDown = useCallback(() => setDragging(true), []);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) updatePosition(e.clientX);
    },
    [dragging, updatePosition],
  );

  const handleMouseUp = useCallback(() => setDragging(false), []);

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      updatePosition(e.touches[0].clientX);
    },
    [updatePosition],
  );

  // Calculate rendered image height based on container width and aspect ratio
  const containerWidth = containerRef.current?.getBoundingClientRect().width ?? 800;
  const imgHeight = imgNaturalSize
    ? (containerWidth / imgNaturalSize.w) * imgNaturalSize.h
    : height;
  const needsScroll = imgHeight > height;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height,
        overflow: 'hidden',
        cursor: 'col-resize',
        userSelect: 'none',
        borderRadius: 8,
      }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleMouseUp}
    >
      {/* Scrollable inner container */}
      <div
        ref={scrollRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          overflowY: needsScroll ? 'auto' : 'hidden',
          overflowX: 'hidden',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(255,255,255,0.3) transparent',
        }}
      >
        {/* Image container with natural aspect ratio */}
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: needsScroll ? imgHeight : height,
          }}
        >
          {/* Before image (full width, natural height) */}
          <img
            src={beforeSrc}
            alt="Before"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              objectFit: needsScroll ? 'fill' : 'cover',
            }}
            draggable={false}
          />
          {/* After image (clipped) */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: `${position}%`,
              height: '100%',
              overflow: 'hidden',
            }}
          >
            <img
              src={afterSrc}
              alt="After"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: containerRef.current
                  ? `${containerRef.current.getBoundingClientRect().width}px`
                  : '100vw',
                height: '100%',
                objectFit: needsScroll ? 'fill' : 'cover',
              }}
              draggable={false}
            />
          </div>
          {/* Slider line */}
          <div
            onMouseDown={handleMouseDown}
            onTouchStart={handleMouseDown}
            style={{
              position: 'absolute',
              top: 0,
              left: `${position}%`,
              transform: 'translateX(-50%)',
              width: 4,
              height: '100%',
              background: '#fff',
              boxShadow: '0 0 6px rgba(0,0,0,0.5)',
              zIndex: 2,
            }}
          >
            {/* Handle circle — fixed to viewport center */}
            <div
              style={{
                position: 'sticky',
                top: height / 2 - 18,
                left: '50%',
                transform: 'translateX(-50%)',
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: '#fff',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 14,
                color: '#666',
                zIndex: 3,
              }}
            >
              {'<>'}
            </div>
          </div>
        </div>
      </div>
      {/* Labels — fixed at top */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          right: 8,
          background: 'rgba(0,0,0,0.6)',
          color: '#fff',
          padding: '2px 8px',
          borderRadius: 4,
          fontSize: 12,
          zIndex: 4,
          pointerEvents: 'none',
        }}
      >
        Before
      </div>
      <div
        style={{
          position: 'absolute',
          top: 8,
          left: 8,
          background: 'rgba(0,0,0,0.6)',
          color: '#fff',
          padding: '2px 8px',
          borderRadius: 4,
          fontSize: 12,
          zIndex: 4,
          pointerEvents: 'none',
        }}
      >
        After
      </div>
      {/* Scroll hint */}
      {needsScroll && (
        <div
          style={{
            position: 'absolute',
            bottom: 8,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(0,0,0,0.6)',
            color: 'rgba(255,255,255,0.7)',
            padding: '2px 12px',
            borderRadius: 4,
            fontSize: 11,
            zIndex: 4,
            pointerEvents: 'none',
          }}
        >
          Scroll to see more
        </div>
      )}
    </div>
  );
}
