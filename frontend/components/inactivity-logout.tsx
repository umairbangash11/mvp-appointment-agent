"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { clearTokens } from "@/lib/auth";

const INACTIVITY_MS = 15 * 60 * 1000; // 15 minutes

export default function InactivityLogout() {
  const router = useRouter();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function resetTimer() {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      clearTokens();
      router.push("/login");
    }, INACTIVITY_MS);
  }

  useEffect(() => {
    const events = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"];
    events.forEach((e) => window.addEventListener(e, resetTimer));
    resetTimer();
    return () => {
      events.forEach((e) => window.removeEventListener(e, resetTimer));
      if (timer.current) clearTimeout(timer.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}
