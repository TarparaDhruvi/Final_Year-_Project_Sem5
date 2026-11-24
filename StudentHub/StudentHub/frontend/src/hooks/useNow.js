import { useEffect, useState } from "react";

/** Returns the current Date and re-renders every `ms` milliseconds (default 1s) — drives live countdowns. */
export default function useNow(ms = 1000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), ms);
    return () => clearInterval(id);
  }, [ms]);
  return now;
}
