import {
  INTEREST_LABELS,
  INTEREST_ORDER,
  formatGeneratedAt,
  getInterest,
  loadData,
  loadInterestMap,
  localeCompare,
  setInterest,
} from "./common.js";

const tableBody = document.querySelector("#program-table-body");
const dataStatus = document.querySelector("#data-status");
const interestSummary = document.querySelector("#interest-summary");
const sampleBanner = document.querySelector("#sample-banner");
const showDetailsButton = document.querySelector("#show-details");
const mobileSortSelect = document.querySelector("#mobile-sort-select");
const mobileSortDirection = document.querySelector("#mobile-sort-direction");

const state = {
  programs: [],
  sortKey: "faculty",
  sortDirection: "asc",
};

function sortValue(program, key, interestMap) {
  if (key === "interest") return INTEREST_ORDER[getInterest(program.id, interestMap)];
  return program[key];
}

function sortedPrograms() {
  const interestMap = loadInterestMap();
  const direction = state.sortDirection === "asc" ? 1 : -1;
  return [...state.programs].sort((a, b) => {
    let result;
    if (state.sortKey === "duration" || state.sortKey === "interest") {
      result = Number(sortValue(a, state.sortKey, interestMap)) - Number(sortValue(b, state.sortKey, interestMap));
    } else {
      result = localeCompare(sortValue(a, state.sortKey, interestMap), sortValue(b, state.sortKey, interestMap));
    }
    if (result === 0) result = localeCompare(a.faculty, b.faculty);
    if (result === 0) result = localeCompare(a.name, b.name);
    return result * direction;
  });
}

function interestControl(program, currentInterest) {
  const fieldset = document.createElement("fieldset");
  fieldset.className = "interest-options";
  fieldset.setAttribute("aria-label", `Interes za program ${program.name}`);

  for (const value of ["yes", "maybe", "no"]) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "radio";
    input.name = `interest-${program.id}`;
    input.value = value;
    input.checked = currentInterest === value;
    input.addEventListener("change", () => {
      setInterest(program.id, value);
      updateSummary();
      if (state.sortKey === "interest") renderTable();
    });
    label.append(input, document.createTextNode(INTEREST_LABELS[value]));
    fieldset.append(label);
  }
  return fieldset;
}

function makeCell(label, value) {
  const cell = document.createElement("td");
  cell.dataset.label = label;
  if (value instanceof Node) cell.append(value);
  else cell.textContent = String(value ?? "");
  return cell;
}

function renderTable() {
  const interestMap = loadInterestMap();
  tableBody.replaceChildren();

  for (const program of sortedPrograms()) {
    const row = document.createElement("tr");
    row.append(
      makeCell("Članica UL", program.faculty),
      makeCell("Ime programa", program.name),
      makeCell("Vrsta programa", program.type),
      makeCell("Trajanje v letih", program.duration),
      makeCell("Interes", interestControl(program, getInterest(program.id, interestMap))),
    );
    tableBody.append(row);
  }
}

function updateSummary() {
  const map = loadInterestMap();
  const counts = { yes: 0, maybe: 0, no: 0 };
  for (const program of state.programs) counts[getInterest(program.id, map)] += 1;
  interestSummary.textContent = `Ja: ${counts.yes} · Mogoče: ${counts.maybe} · Ne: ${counts.no}`;
}

function updateSortUI() {
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    const key = th.dataset.sort;
    const active = key === state.sortKey;
    th.setAttribute("aria-sort", active ? (state.sortDirection === "asc" ? "ascending" : "descending") : "none");
    const indicator = th.querySelector(".sort-indicator");
    indicator.textContent = active ? (state.sortDirection === "asc" ? "↑" : "↓") : "";
  });
  mobileSortSelect.value = state.sortKey;
  mobileSortDirection.textContent = state.sortDirection === "asc" ? "Naraščajoče" : "Padajoče";
}

function setSort(key, toggle = true) {
  if (state.sortKey === key && toggle) {
    state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
  } else {
    state.sortKey = key;
    state.sortDirection = "asc";
  }
  updateSortUI();
  renderTable();
}

document.querySelectorAll(".sort-button").forEach((button) => {
  button.addEventListener("click", () => setSort(button.closest("th").dataset.sort));
});

mobileSortSelect.addEventListener("change", () => setSort(mobileSortSelect.value, false));
mobileSortDirection.addEventListener("click", () => {
  state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
  updateSortUI();
  renderTable();
});

showDetailsButton.addEventListener("click", () => {
  const selected = [...document.querySelectorAll('input[name="details-interest"]:checked')].map((input) => input.value);
  if (!selected.length) {
    window.alert("Izberite vsaj eno možnost interesa.");
    return;
  }
  const params = new URLSearchParams({ interest: selected.join(",") });
  window.location.href = `details.html?${params.toString()}`;
});

async function init() {
  try {
    const payload = await loadData();
    state.programs = payload.programs;
    sampleBanner.hidden = !payload.isSample;
    dataStatus.textContent = `${state.programs.length} programov · podatki osveženi: ${formatGeneratedAt(payload.generatedAt)}`;
    updateSortUI();
    renderTable();
    updateSummary();
  } catch (error) {
    console.error(error);
    dataStatus.textContent = "Podatkov ni bilo mogoče naložiti. Preverite README in zaženite skripto za osvežitev podatkov.";
    interestSummary.textContent = "";
  }
}

init();
