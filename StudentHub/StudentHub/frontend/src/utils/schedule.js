// Shared timetable helpers used by the My Schedule page and dashboard widgets.

export const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
export const WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export const toMinutes = (t) => {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
};

const sortByStart = (a, b) => a.start_time.localeCompare(b.start_time);

export function format12h(t) {
  const [h, m] = t.split(":").map(Number);
  const suffix = h >= 12 ? "PM" : "AM";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}:${String(m).padStart(2, "0")} ${suffix}`;
}

/**
 * Works out everything the UI needs for "today":
 * numbered lectures (Lecture 2 of 4), which one is live right now, which is next,
 * and (if today has no more classes) the next class in the coming days.
 */
export function analyseSchedule(slots, now) {
  const dayName = DAY_NAMES[now.getDay()];
  const nowMin = now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60;

  const today = slots
    .filter((s) => s.day_of_week === dayName)
    .sort(sortByStart)
    .map((s, i, arr) => ({
      ...s,
      lecture: i + 1,
      total: arr.length,
      status: nowMin >= toMinutes(s.end_time) ? "completed" : nowMin >= toMinutes(s.start_time) ? "live" : "upcoming",
    }));

  const current = today.find((s) => s.status === "live") || null;
  const nextToday = today.find((s) => s.status === "upcoming") || null;

  let nextLater = null;
  if (!nextToday) {
    for (let i = 1; i <= 7 && !nextLater; i++) {
      const name = DAY_NAMES[(now.getDay() + i) % 7];
      const first = slots.filter((s) => s.day_of_week === name).sort(sortByStart)[0];
      if (first) nextLater = { ...first, dayLabel: i === 1 ? "Tomorrow" : name };
    }
  }
  return { dayName, today, current, nextToday, nextLater };
}

/** "1h 05m 09s" style countdown from `now` to a HH:MM time today. */
export function countdownTo(timeStr, now) {
  const target = new Date(now);
  const [h, m] = timeStr.split(":").map(Number);
  target.setHours(h, m, 0, 0);
  const diff = Math.max(0, Math.floor((target - now) / 1000));
  return formatSeconds(diff);
}

export function formatSeconds(diff) {
  const h = Math.floor(diff / 3600);
  const m = Math.floor((diff % 3600) / 60);
  const s = diff % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}h ${pad(m)}m ${pad(s)}s` : `${m}m ${pad(s)}s`;
}
