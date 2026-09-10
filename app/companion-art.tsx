import type { CSSProperties } from "react";
import { ASTERION_ATLAS, atlasTimeline } from "@/lib/animation-atlas";
import styles from "./companion-art.module.css";

/** Render the approved Asterion atlas without editing pixels or changing other companions. */
export function CompanionArt({ alt, animation, reducedMotion = false, fill = false, width = 192, height = 208, className = "" }: {
  alt: string;
  animation?: string;
  reducedMotion?: boolean;
  fill?: boolean;
  width?: number;
  height?: number;
  className?: string;
}) {
  const animated = Boolean(animation) && !reducedMotion;
  const timeline = atlasTimeline(animated ? animation : "idle");
  const style = { "--atlas-row": `${-timeline.row * ASTERION_ATLAS.cellHeight}px`, animationDuration: `${timeline.duration}ms` } as CSSProperties;
  return <svg className={`${styles.viewport} ${fill ? styles.fill : ""} ${className}`}
    viewBox="0 0 192 208" preserveAspectRatio="xMidYMid meet" width={fill ? "100%" : width} height={fill ? "100%" : height}
    role={alt ? "img" : undefined} aria-label={alt || undefined} aria-hidden={alt ? undefined : true} focusable="false"
    data-asterion-animation={animated ? timeline.name : "still"}>
    <svg width={192} height={208} overflow="hidden" aria-hidden="true">
      <image href={ASTERION_ATLAS.asset} width={ASTERION_ATLAS.width} height={ASTERION_ATLAS.height}
        className={`${styles.sprite} ${animated ? styles[timeline.name] : ""}`} style={style} />
    </svg>
  </svg>;
}
