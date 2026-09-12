# University of Ljubljana study-programme browser

A small static website for comparing selected University of Ljubljana study programmes without opening every programme page separately.

The MIT License applies to the source code of this project only. Study programme data and textual content retrieved from the University of Ljubljana are not covered by this license. Rights to that content remain with the University of Ljubljana and/or the respective rights holders.

The **code and repository documentation are in English**. The **website interface is in Slovene**.

## What the site does

The main page shows only these programme types:

- `Univerzitetni`
- `Enoviti magistrski`

For each programme it shows, in this order:

1. Članica UL
2. Ime programa
3. Vrsta programa
4. Trajanje v letih
5. Interes: Ja / Mogoče / Ne

The table is sorted by faculty by default. The columns are sortable. Interest is `Ne` by default and is stored in the browser's `localStorage`, so the choices survive closing and reopening the browser on the same device.

The detail page can include any combination of `Ja`, `Mogoče`, and `Ne` (default: `Ja` + `Mogoče`). It shows the four basic fields, the full `Opis programa`, and only the part of `Merila za izbiro ob omejitvi vpisa` relevant to a candidate with a **splošna matura**. Criteria shared by all candidates (for example an aptitude test) are retained. Rules that apply only to poklicna matura, old zaključni izpit routes, or higher-year transfers are omitted where they can be identified.

`Odstrani` on the detail page removes the programme from the current page **and sets its interest to `Ne`** on the main page.

The site is responsive and has print-specific styling for the detail view.

## Technology choice

The front end intentionally uses only:

- HTML5
- CSS
- vanilla JavaScript

There is no npm dependency, front-end framework, server, or database. That makes the published site a good fit for GitHub Pages.

A small Python script downloads the public UL catalogue and produces `data/programs.json`. Python is used only when refreshing data; visitors to the website do not need Python.

## Repository structure

```text
.
├── index.html                 # sortable programme table
├── details.html               # long-form selected-programme view
├── styles.css                 # responsive + print styles
├── common.js                  # shared data/localStorage helpers
├── index.js                   # main-page behaviour
├── details.js                 # detail-page behaviour
├── data/
│   └── programs.json          # generated data (sample data in the repository)
├── scripts/
│   └── update_data.py         # UL scraper/cleaner
├── tests/
│   └── test_parser.py         # parser tests
├── requirements.txt
└── .github/workflows/pages.yml
```

## Run locally

Python 3.10+ is recommended.

### 1. Create a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Download the current UL data

```bash
python scripts/update_data.py
```

This replaces the small sample `data/programs.json` included in the repository with the current parsed data from the University of Ljubljana website.

The script first reads the UL page for undergraduate and integrated-master programmes, follows the programme links, keeps only `Univerzitetni` and `Enoviti magistrski`, extracts the description, and cleans the admission-limit criteria for the general-matura route.

### 4. Run a local web server

Do not open `index.html` directly with `file://`, because browsers normally block `fetch()` of the JSON file in that mode.

Run:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

No compilation/build step is required.

## Run the tests

```bash
python -m unittest discover -s tests
```

The tests cover programme-link discovery and several selection-criteria patterns, including:

- a separate `kandidati iz točke a)` block;
- a combined `a) in c)` block;
- criteria shared by all first-year candidates;
- excluding higher-year transfer criteria.

## Publish on GitHub Pages

The repository contains `.github/workflows/pages.yml`. The workflow:

1. installs Python dependencies;
2. runs the parser tests;
3. downloads current programme data from UL;
4. assembles the static site;
5. deploys it to GitHub Pages.

It runs on every push to `main`, can be started manually, and is also scheduled weekly.

### First publication

Create an empty GitHub repository, copy these files into it, and push them. For example:

```bash
git init
git add .
git commit -m "Initial UL programme browser"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

On GitHub, open:

**Settings → Pages → Build and deployment → Source → GitHub Actions**

Then open the **Actions** tab and confirm that `Build and deploy GitHub Pages` finishes successfully.

The same code works for both:

- a user/organization site such as `YOUR-USERNAME.github.io`;
- a project site such as `YOUR-USERNAME.github.io/YOUR-REPOSITORY/`.

All internal URLs are relative for that reason.

## Refresh data manually

Locally:

```bash
python scripts/update_data.py
```

Then inspect `data/programs.json`, commit it if you want the repository itself to contain the newest data, and push.

For the published Pages site this is not necessary: the GitHub Actions deployment regenerates the JSON before publishing.

You can also run the workflow manually from:

**GitHub → Actions → Build and deploy GitHub Pages → Run workflow**

## Data-cleaning rules

The UL website is the source of truth. The script deliberately uses text/heading heuristics rather than copying large parts of the site structure, because markup can change even when the visible headings remain stable.

For `Merila za izbiro ob omejitvi vpisa`, the parser follows these rules:

- if candidate groups `a)`, `b)`, `c)` are present, it keeps the group containing `a)` (the general-matura route);
- if `a)` is combined with another group, for example `a) in c)`, the shared criteria are kept;
- if the criteria apply to all first-year candidates, they are kept;
- later criteria for higher-year entry/transfers are excluded;
- the date range in the original heading and generic introductory wording are not shown in the GUI.

Because programme pages are maintained independently and can contain unusual wording, the generated JSON should be spot-checked after a major UL website redesign. Every detail card contains a link to the official programme page for verification.

## Browser storage

Interest choices are stored only in the current browser under the key:

```text
ul-study-program-interests-v1
```

Nothing is sent to a server. Different browsers/devices have separate selections.

To reset everything to `Ne`, clear this site's local storage/site data in the browser developer tools or browser settings.

## Notes about the included JSON

The committed `data/programs.json` is intentionally a **small sample** so that the interface can be previewed immediately. It currently contains Anglistika, Arhitektura, and Farmacija with placeholder detail text purely for interface preview. The page shows a visible warning while sample data are being used.

Running `python scripts/update_data.py` (or deploying through the included GitHub Actions workflow) replaces it with the complete current dataset.

## Disclaimer

This is an unofficial convenience view of public University of Ljubljana information. Admission conditions and selection criteria can change. For decisions and applications, verify the current official programme page and the official call for enrolment.
