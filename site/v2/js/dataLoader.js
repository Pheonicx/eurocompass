import { REPO_RAW, EXPORT_PATH } from './config.js';

// Populates state.data with the full v2 export. Throws on failure so
// the caller can show the error screen. Unlike v1's loader, this is a
// single fetch — v2_exports/latest.json already bundles rates, trends,
// history, and recommendations together, so there's no separate
// per-bank history fetch (and no Promise.allSettled juggling) needed.
export async function loadAll(state) {
  const url = `${REPO_RAW}/${EXPORT_PATH}?_=${Date.now()}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${EXPORT_PATH} (${res.status})`);
  }
  state.data = await res.json();
}
