import { useEffect, useState } from "react";
import { searchPlaces } from "../api/client";
import type { Place } from "../api/types";
import { useDebouncedValue } from "./useDebouncedValue";

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 3;

export function usePlaceSuggestions(query: string, enabled: boolean): Place[] {
  const debounced = useDebouncedValue(query.trim(), DEBOUNCE_MS);
  const [suggestions, setSuggestions] = useState<Place[]>([]);

  useEffect(() => {
    if (!enabled || debounced.length < MIN_QUERY_LENGTH) {
      setSuggestions([]);
      return;
    }
    const abort = new AbortController();
    searchPlaces(debounced, abort.signal)
      .then(setSuggestions)
      .catch(() => {
        if (!abort.signal.aborted) setSuggestions([]);
      });
    return () => abort.abort();
  }, [debounced, enabled]);

  return suggestions;
}
