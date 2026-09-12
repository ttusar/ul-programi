export const DATA_URL = "data/programs.json";
export const STORAGE_KEY = "ul-study-program-interests-v1";

export const INTEREST_LABELS = {
  yes: "Ja",
  maybe: "Mogoče",
  no: "Ne",
};

export const INTEREST_ORDER = {
  yes: 0,
  maybe: 1,
  no: 2,
};

export async function loadData() {
  const response = await fetch(DATA_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Podatkov ni bilo mogoče naložiti (${response.status}).`);
  }
  const payload = await response.json();
  if (!payload || !Array.isArray(payload.programs)) {
    throw new Error("Datoteka s podatki ni v pričakovani obliki.");
  }
  return payload;
}

export function loadInterestMap() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return stored && typeof stored === "object" ? stored : {};
  } catch {
    return {};
  }
}

export function getInterest(programId, map = loadInterestMap()) {
  const value = map[programId];
  return value === "yes" || value === "maybe" || value === "no" ? value : "no";
}

export function setInterest(programId, interest) {
  if (!(interest in INTEREST_LABELS)) return;
  const map = loadInterestMap();
  if (interest === "no") {
    delete map[programId];
  } else {
    map[programId] = interest;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

export function localeCompare(a, b) {
  return String(a ?? "").localeCompare(String(b ?? ""), "sl", {
    sensitivity: "base",
    numeric: true,
  });
}

export function formatGeneratedAt(value) {
  if (!value) return "vzorčni podatki";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("sl-SI", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function makeTextElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

export function renderTextLines(container, lines) {
  const values = Array.isArray(lines) ? lines.filter(Boolean) : [];
  if (!values.length) {
    container.append(makeTextElement("p", "muted", "Podatek ni bil najden na strani programa."));
    return;
  }

  let list = null;
  for (const raw of values) {
    const text = String(raw).trim();
    const bulletMatch = text.match(/^[-–−•]\s*(.+)$/);
    if (bulletMatch) {
      if (!list) {
        list = document.createElement("ul");
        list.className = "detail-list";
        container.append(list);
      }
      list.append(makeTextElement("li", "", bulletMatch[1]));
    } else {
      list = null;
      container.append(makeTextElement("p", "", text));
    }
  }
}
