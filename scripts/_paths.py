"""Central path constants for the VAXT data repository.

Every script imports from here instead of computing paths relative to
__file__.  This keeps the directory layout in one place.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Top-level dirs
DATASETS_DIR = PROJECT_ROOT / "datasets"
OUTPUT_DIR = PROJECT_ROOT / "output"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Dataset category dirs
VARIETIES_DIR = DATASETS_DIR / "varieties"
GENOMICS_DIR = DATASETS_DIR / "genomics"
BREEDING_DIR = DATASETS_DIR / "breeding"
GROWING_DIR = DATASETS_DIR / "growing"
CULTURE_DIR = DATASETS_DIR / "culture"
REFERENCE_DIR = DATASETS_DIR / "reference"

# Config
SOURCES_TOML = PROJECT_ROOT / "sources.toml"

# DuckDB
DUCKDB_PATH = OUTPUT_DIR / "heritage-grain.duckdb"

# CSV_MAP: filename -> absolute path  (used by sync_csv_to_airtable.py)
CSV_MAP = {
    # varieties
    "nordic_variety_trait_index.csv": VARIETIES_DIR / "nordic_variety_trait_index.csv",
    "variety_growing_enrichment.csv": VARIETIES_DIR / "variety_growing_enrichment.csv",
    "phenotype_template.csv": VARIETIES_DIR / "phenotype_template.csv",
    # genomics
    "cold_tolerance_markers.csv": GENOMICS_DIR / "cold_tolerance_markers.csv",
    "disease_resistance.csv": GENOMICS_DIR / "disease_resistance.csv",
    "crop_wild_relatives.csv": GENOMICS_DIR / "crop_wild_relatives.csv",
    # breeding
    "breeding_programs.csv": BREEDING_DIR / "breeding_programs.csv",
    "field_trial_sites.csv": BREEDING_DIR / "field_trial_sites.csv",
    "grin_accessions.csv": BREEDING_DIR / "grin_accessions.csv",
    # growing
    "planting_calendars.csv": GROWING_DIR / "planting_calendars.csv",
    "climate_zones.csv": GROWING_DIR / "climate_zones.csv",
    "seed_sources.csv": GROWING_DIR / "seed_sources.csv",
    "rootstock_compatibility.csv": GROWING_DIR / "rootstock_compatibility.csv",
    # culture
    "sourdough_starters.csv": CULTURE_DIR / "sourdough_starters.csv",
    "sourdough_recipes.csv": CULTURE_DIR / "sourdough_recipes.csv",
    "distillery_profiles.csv": CULTURE_DIR / "distillery_profiles.csv",
    "community_grain_projects.csv": CULTURE_DIR / "community_grain_projects.csv",
    # reference
    "eppo_pathogens.csv": REFERENCE_DIR / "eppo_pathogens.csv",
}
