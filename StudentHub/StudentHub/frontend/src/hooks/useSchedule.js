import { useEffect, useState } from "react";
import api from "../services/api";

/** Loads the logged-in faculty/student's weekly schedule (built by the backend from the Admin's timetable). */
export default function useSchedule() {
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.get("/timetable/my-schedule")
      .then(({ data }) => setSlots(data.slots))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return { slots, loading, error };
}
