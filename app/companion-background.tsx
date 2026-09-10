"use client";

import Image from "next/image";
import { useState } from "react";
import { COMPANION_BACKGROUNDS } from "@/lib/companion-backgrounds";
import type { CompanionKind } from "@/lib/companions";
import styles from "./companion-background.module.css";

export function CompanionBackground({ kind }: { kind: CompanionKind }) {
  const [failedKind, setFailedKind] = useState<CompanionKind | null>(null);

  return (
    <div className={styles.background} aria-hidden="true" data-companion-background={kind}>
      {failedKind === kind ? null : (
        <Image
          key={kind}
          className={styles.image}
          src={COMPANION_BACKGROUNDS[kind]}
          alt=""
          fill
          sizes="(max-width: 590px) calc(100vw - 54px), 480px"
          loading="eager"
          draggable={false}
          onError={() => setFailedKind(kind)}
        />
      )}
    </div>
  );
}
