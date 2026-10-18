# Data availability, code availability and reproducibility statements

Ready to paste into a submission. Replace the bracketed items. Before submission:
1. **Make the repository public** (it is currently private), or archive a release on Zenodo and cite its DOI. Elsevier, IET and MDPI all prefer a DOI-archived snapshot.
2. Replace `[commit]` with the commit hash of the version you submit (e.g. `git rev-parse --short HEAD`), or with a release tag.

---

## 1. Data availability statement

### Short form (≤ 100 words; e.g. Energy Reports, Energy Strategy Reviews)

> The data that support the findings of this study are openly available. Regional electricity statistics were obtained from the KAPSARC Energy Data Portal (https://datasource.kapsarc.org; dataset identifiers listed in the repository). Renewable project records were obtained from the Global Energy Monitor wiki (https://www.gem.wiki, CC BY-NC-SA), weather data from NASA POWER (https://power.larc.nasa.gov) and province boundaries from Natural Earth. All data were retrieved on 18 October 2026. Archived source files, checksums, processed data and all result tables are available at https://github.com/mdtabrez-hub/KSA-energy [and Zenodo, https://doi.org/10.5281/zenodo.XXXXXXX].

### Long form (journals that want per-source detail, e.g. IET Renewable Power Generation)

> This study uses only publicly available data, retrieved on 18 October 2026:
>
> (i) **KAPSARC Energy Data Portal** (https://datasource.kapsarc.org): "Saudi Arabia Electricity Load Monthly by Region" (2009–2019); "Electricity Installed Capacity (Peak Load) by Region" (2005–2019); "Electricity Consumption by Sectors" (2005–2025); "Electricity Consumption, Production, Number of Subscribers, Peak Load and Actual Generating Capacity" (1980–2019); and "Saudi Arabia Planned and Installed Renewables by Project". The exact dataset identifiers are listed in `config/data_sources.yaml`.
>
> (ii) **Global Energy Monitor wiki** pages for 106 Saudi solar and wind projects (Global Solar and Wind Power Trackers; CC BY-NC-SA).
>
> (iii) **NASA POWER** hourly data, as served on the retrieval date, for 2019–2023 at the project coordinates.
>
> (iv) **Natural Earth** 1:10m admin-1 boundaries (public domain).
>
> The repository https://github.com/mdtabrez-hub/KSA-energy (version `[commit]`) [archived at https://doi.org/10.5281/zenodo.XXXXXXX] contains:
> - the downloaded files from sources whose terms permit redistribution, each with a SHA-256 manifest;
> - the processed tables derived from them;
> - a manually curated project-identity table;
> - every table and figure reported in the paper.
>
> Three KAPSARC series state no reuse licence on the portal (monthly regional load; national peak load; peak-load growth by source). For these, only the portal metadata and SHA-256 checksums are deposited; the data are re-downloaded from the public portal by the provided scripts. NASA POWER data (461 MB) and Natural Earth boundaries are also re-downloaded by the scripts rather than deposited.
>
> Derived tables based on Global Energy Monitor data are shared under CC BY-NC-SA. The source datasets are subject to revision by their publishers, so the deposited checksums identify the exact versions used.

---

## 2. Code availability statement

> All code used to download, clean, analyse and plot the data is available at https://github.com/mdtabrez-hub/KSA-energy (version `[commit]`) [archived at https://doi.org/10.5281/zenodo.XXXXXXX] under the MIT licence. It is written in Python 3.13. The main dependencies are pandas 3.0.5, NumPy 2.5.3, pvlib 0.16.1, Shapely 2.2.0 and Matplotlib 3.11.2; exact versions are pinned in `requirements-lock.txt`. The repository includes 29 automated tests and a single script, `reproduce.sh`, that regenerates every result.

---

## 3. Reproducibility statement

> All results are produced by a scripted pipeline (`reproduce.sh`) from public sources, with no manual data editing apart from one documented identity table (`data/manual/kapsarc_project_aliases.csv`).
>
> Corrections to the source data follow written rules implemented in code, and every changed value is logged (`results/tables/d2_corrections_log.csv`). Raw downloads are stored unmodified with SHA-256 checksums, and checksums of all result files are provided (`results/SHA256SUMS`).
>
> Re-running the full pipeline from the archived inputs on 18 October 2026 reproduced all 28 result files (tables and figures) byte-for-byte. The modelled results (PV and wind output) are deterministic given the weather inputs; no random sampling is used.
>
> Results reported as ranges are the minimum, median and maximum over an explicit enumeration of scenarios: 36 assignments of provinces to operating areas, 5 weather years, 2 PV mounting types and project status sets, documented in the repository. A fresh download may differ where the publishers have revised their data. The checksums in each download manifest show whether the inputs are identical to those used here.

---

## 4. Optional additions some journals request

- **Software citation:** cite pvlib (Holmgren, Hansen & Mikofski, 2018, *JOSS* 3(29):884, doi:10.21105/joss.00884) and the repository (see `CITATION.cff`).
- **Generative AI disclosure** (required by Elsevier, IET, MDPI and others): state how AI assistance was used in the study and the manuscript, following the journal's own policy wording. *[Author to complete.]*
- **Licence summary:** code MIT; project-made data tables CC BY 4.0; GEM-derived tables CC BY-NC-SA; KAPSARC data Public Domain except the three series noted above.
