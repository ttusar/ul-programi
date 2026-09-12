import {
  INTEREST_LABELS,
  getInterest,
  loadData,
  loadInterestMap,
  localeCompare,
  makeTextElement,
  renderTextLines,
  setInterest,
} from "./common.js";

const container = document.querySelector("#program-details");
const status = document.querySelector("#details-status");
const filterLabel = document.querySelector("#details-filter-label");
const sampleBanner = document.querySelector("#sample-banner");

document.querySelector("#print-page").addEventListener("click", () => window.print());

function selectedInterests() {
  const raw = new URLSearchParams(window.location.search).get("interest") || "yes,maybe";
  const values = raw.split(",").filter((value) => value in INTEREST_LABELS);
  return values.length ? [...new Set(values)] : ["yes", "maybe"];
}

function metadataItem(label, value) {
  const wrapper = document.createElement("div");
  wrapper.className = "meta-item";
  wrapper.append(
    makeTextElement("dt", "meta-label", label),
    makeTextElement("dd", "meta-value", String(value ?? "")),
  );
  return wrapper;
}

function createProgramCard(program) {
  const article = document.createElement("article");
  article.className = "program-card";
  article.dataset.programId = program.id;

  const top = document.createElement("div");
  top.className = "program-card-top";
  const titleGroup = document.createElement("div");
  titleGroup.append(makeTextElement("p", "program-faculty", program.faculty), makeTextElement("h2", "", program.name));

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "button button-danger button-small no-print";
  remove.textContent = "Odstrani";
  remove.addEventListener("click", () => {
    setInterest(program.id, "no");
    article.remove();
    updateEmptyState();
  });
  top.append(titleGroup, remove);

  const meta = document.createElement("dl");
  meta.className = "program-meta";
  meta.append(
    metadataItem("Članica UL", program.faculty),
    metadataItem("Ime programa", program.name),
    metadataItem("Vrsta programa", program.type),
    metadataItem("Trajanje v letih", program.duration),
  );

  const descriptionSection = document.createElement("section");
  descriptionSection.className = "detail-section";
  descriptionSection.append(makeTextElement("h3", "", "Opis"));
  renderTextLines(descriptionSection, program.description);

  const criteriaSection = document.createElement("section");
  criteriaSection.className = "detail-section";
  criteriaSection.append(makeTextElement("h3", "", "Merila za izbiro ob omejitvi vpisa:"));
  renderTextLines(criteriaSection, program.criteriaGeneralMatura);

  const source = document.createElement("a");
  source.href = program.sourceUrl;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.className = "source-link";
  source.textContent = "Odpri uradno stran programa na UL";

  article.append(top, meta, descriptionSection, criteriaSection, source);
  return article;
}

function updateEmptyState() {
  if (container.children.length) {
    status.hidden = true;
    return;
  }
  status.hidden = false;
  status.textContent = "V izbranih skupinah ni več programov.";
}

async function init() {
  const interests = selectedInterests();
  filterLabel.textContent = `Prikaz: ${interests.map((value) => INTEREST_LABELS[value]).join(", ")}`;

  try {
    const payload = await loadData();
    sampleBanner.hidden = !payload.isSample;
    const interestMap = loadInterestMap();
    const programs = payload.programs
      .filter((program) => interests.includes(getInterest(program.id, interestMap)))
      .sort((a, b) => localeCompare(a.faculty, b.faculty) || localeCompare(a.name, b.name));

    container.replaceChildren(...programs.map(createProgramCard));
    status.textContent = `${programs.length} programov`;
    if (programs.length) status.hidden = true;
    updateEmptyState();
  } catch (error) {
    console.error(error);
    status.hidden = false;
    status.textContent = "Podatkov ni bilo mogoče naložiti. Vrnite se na seznam in preverite, ali je datoteka data/programs.json na voljo.";
  }
}

init();
