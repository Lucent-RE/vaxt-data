# VAXT Data

Open heritage grain datasets for researchers, growers, and breeders.

**18 curated CSVs** · **280+ varieties** · **140+ genomic markers** · **83 breeding programs** · **39 field trial sites**

This repository contains the structured data layer of the VAXT project. For narrative documentation — variety profiles, methodology, field guides, and breeder notes — see the **[VAXT Knowledge Base](https://opensauce-kb.notion.site/vaxt)**.

---

## Quick Start

```bash
make bootstrap        # Create venv, install deps
make validate         # Verify all datasets
make load             # Load CSVs into DuckDB for analytics
```

## Datasets

| Category | Files | Description |
|----------|-------|-------------|
| **varieties/** | `nordic_variety_trait_index.csv`, `variety_growing_enrichment.csv`, `phenotype_template.csv` | Heritage grain, fruit, and berry varieties with cold tolerance data |
| **genomics/** | `cold_tolerance_markers.csv`, `disease_resistance.csv`, `crop_wild_relatives.csv` | Genomic markers, pathogen resistance, wild relatives |
| **breeding/** | `breeding_programs.csv`, `field_trial_sites.csv`, `grin_accessions.csv` | Institutions, trial locations, USDA GRIN germplasm |
| **growing/** | `planting_calendars.csv`, `climate_zones.csv`, `seed_sources.csv`, `rootstock_compatibility.csv` | Sowing windows, hardiness zones, seed access, rootstocks |
| **culture/** | `sourdough_starters.csv`, `sourdough_recipes.csv`, `distillery_profiles.csv`, `community_grain_projects.csv` | Sourdough cultures, heritage distilleries, community projects |
| **reference/** | `eppo_pathogens.csv`, `DATA_DICTIONARY.md` | EPPO plant pathogen reference, column definitions |

## Directory Structure

```
vaxt-data/
├── datasets/           18 curated CSVs in 6 categories
├── schemas/            JSON Schema for phenotype records
├── scripts/            ETL pipeline, validators, sync tools
├── output/             DuckDB + ETL outputs (gitignored)
├── sources.toml        Declarative pipeline manifest
├── Makefile            bootstrap, validate, etl, load, export, sync, clean
├── LICENSE-CODE        MIT (scripts)
└── LICENSE-DATA        CC BY 4.0 (datasets)
```

## ETL Pipeline

The pipeline fetches data from public APIs and loads everything into DuckDB:

```bash
make etl              # Fetch from FAOSTAT, GBIF, Eurostat, GHCN, T3/BrAPI, etc.
```

Sources are declared in `sources.toml`. Each source has validation rules (min/max rows, unique keys, numeric bounds). Run `python3 scripts/vaxt_runner.py --list` to see all sources.

## Using the Data

### DuckDB

```bash
make load
python3 -c "
import duckdb
conn = duckdb.connect('output/heritage-grain.duckdb')
print(conn.execute('SELECT variety, crop, usda_zone FROM varieties LIMIT 5').fetchdf())
"
```

### Plain CSV

Every dataset is a plain UTF-8 CSV. Load with pandas, R, Excel, or any tool:

```python
import csv
with open("datasets/varieties/nordic_variety_trait_index.csv") as f:
    for row in csv.DictReader(f):
        print(row["variety"], row["crop"], row["usda_zone"])
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome data corrections, new variety submissions, and ETL improvements.

## Citation

```bibtex
@misc{vaxt-data,
  title  = {VAXT Heritage Grain Data Repository},
  author = {VAXT Foundation},
  year   = {2026},
  url    = {https://github.com/vaxt-foundation/vaxt-data}
}
```

## License

- **Code** (scripts, Makefile, CI): [MIT](LICENSE-CODE)
- **Data** (CSVs, schemas, documentation): [CC BY 4.0](LICENSE-DATA)

## Links

- Knowledge Base: [opensauce-kb.notion.site/vaxt](https://opensauce-kb.notion.site/vaxt)
- Website: [vaxt.bio](https://vaxt.bio)
- Contact: malcolm@vav-os.com
