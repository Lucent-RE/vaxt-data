#!/usr/bin/env python3
"""
VÄXT Foundation — Airtable → Frontend JSON Export Pipeline

Fetches all tables from the VÄXT Airtable base (appgv7zVxZnT2q9BX),
denormalizes linked records, and writes JSON files to frontend/public/data/.

Usage:
    export AIRTABLE_TOKEN="pat..."   # or VAXT_AIRTABLE_PAT
    python export_website_data.py [--output-dir frontend/public/data]

Output files:
    varieties.json            — denormalized variety records
    breeding_programs.json    — breeding program records
    field_trial_sites.json    — field trial site records
    sourdough_starters.json   — sourdough starter records
    seed_sources.json         — seed source records
    distillery_profiles.json  — distillery profile records
    community_projects.json   — community grain project records
    planting-calendars.json   — planting calendar sowing windows
"""

import os
import sys
import json
import re
import time
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# ─── Config ───────────────────────────────────────────────────────────────────

BASE_ID = "appgv7zVxZnT2q9BX"
API_BASE = f"https://api.airtable.com/v0/{BASE_ID}"

# Table IDs (from list_tables_for_base)
TABLES = {
    "varieties":          "tblMogZ5yBubxATP3",
    "seed_sources":       "tblXSBBa5Q7i2Bosg",
    "breeding_programs":  "tblJKLE8rjYFRXDxC",
    "research_resources": "tblgz8VckGNeLkGAU",
    "cold_markers":       "tblWFbFGbzrg08BHT",
    "field_trial_sites":  "tblqmaoyJ79LRUiNb",
    "grin_accessions":    "tblSeK1i4NgyzHoan",
    "crop_wild_relatives":"tblfrP3Hq9FMyJs0h",
    "disease_resistance": "tblEtIt4liRaZZ6DT",
    "climate_zones":      "tbl4xPCwx1PCjcPxF",
    "rootstock":          "tbliCpponMHAIbwru",
    "planting_calendars": "tblCW1MU4S9w8LbGu",
    "sourdough_starters": "tblwUbHTGv6gs0wcb",
    "sourdough_recipes":  "tblr6VLkODWukswxS",
    "distillery_profiles":"tblryxiQkwTiwe5co",
    "community_projects": "tblzuMZwPYtxhhzlV",
}

# Crop → Supercategory mapping
CROP_SUPERCATEGORY = {
    "wheat": "grain", "rye": "grain", "barley": "grain", "oat": "grain",
    "spelt": "grain", "emmer": "grain", "einkorn": "grain", "triticale": "grain",
    "apple": "fruit", "pear": "fruit", "plum": "fruit", "cherry": "fruit", "apricot": "fruit",
    "haskap": "berry", "sea buckthorn": "berry", "lingonberry": "berry",
    "arctic bramble": "berry", "blueberry": "berry", "saskatoon": "berry",
    "cloudberry": "berry", "black currant": "berry", "red currant": "berry",
    "raspberry": "berry", "gooseberry": "berry",
    "grape": "grape",
    "forage grass": "forage", "other": "forage",
}


# ─── Airtable API helpers ─────────────────────────────────────────────────────

def get_token():
    token = os.environ.get("AIRTABLE_TOKEN") or os.environ.get("VAXT_AIRTABLE_PAT")
    if not token:
        print("ERROR: Set AIRTABLE_TOKEN or VAXT_AIRTABLE_PAT environment variable", file=sys.stderr)
        sys.exit(1)
    return token


def fetch_table(table_id, token):
    """Fetch all records from a table with cursor-based pagination."""
    records = []
    cursor = None
    page = 0

    while True:
        url = f"{API_BASE}/{table_id}?pageSize=100"
        if cursor:
            url += f"&offset={cursor}"

        req = Request(url, headers={"Authorization": f"Bearer {token}"})

        try:
            with urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code == 429:
                # Rate limited — wait and retry
                print(f"    Rate limited, waiting 30s...")
                time.sleep(30)
                continue
            raise

        batch = data.get("records", [])
        records.extend(batch)
        page += 1

        cursor = data.get("offset")
        if not cursor:
            break

        # Airtable rate limit: 5 requests/sec
        time.sleep(0.25)

    return records


def fetch_all_tables(token):
    """Fetch all tables and return a dict of {table_name: [records]}."""
    all_data = {}
    for name, table_id in TABLES.items():
        print(f"  Fetching {name}...")
        records = fetch_table(table_id, token)
        all_data[name] = records
        print(f"    → {len(records)} records")
        time.sleep(0.25)
    return all_data


# ─── Field extraction helpers ─────────────────────────────────────────────────

def get_field(record, field_name):
    """Get a field value from a record, returning None if missing."""
    return record.get("fields", {}).get(field_name)


def flatten_select(value):
    """Convert a singleSelect object to its name string."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("name")
    return str(value)


def flatten_multi_select(value):
    """Convert a multipleSelects array to a list of name strings."""
    if not value:
        return []
    if isinstance(value, list):
        return [item.get("name") if isinstance(item, dict) else str(item) for item in value]
    return []


def get_linked_ids(record, field_name):
    """Get linked record IDs from a multipleRecordLinks field."""
    value = get_field(record, field_name)
    if not value:
        return []
    if isinstance(value, list):
        return [item if isinstance(item, str) else item.get("id", "") for item in value]
    return []


def slugify(name):
    """Convert a variety name to a URL-safe slug."""
    slug = name.lower().strip()
    # Handle special characters (ö → o, å → a, etc.)
    replacements = {
        "ö": "o", "ä": "a", "å": "a", "ü": "u", "é": "e", "è": "e",
        "ê": "e", "ë": "e", "à": "a", "â": "a", "ô": "o", "î": "i",
        "ç": "c", "ñ": "n", "ß": "ss",
    }
    for char, repl in replacements.items():
        slug = slug.replace(char, repl)
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


# ─── Lookup dict builders ─────────────────────────────────────────────────────

def build_breeding_program_lookup(records):
    """Build a dict of record_id → {institution, country, city, lat, lng}."""
    lookup = {}
    for r in records:
        f = r.get("fields", {})
        lookup[r["id"]] = {
            "institution": f.get("Institution"),
            "country": flatten_select(f.get("Country")),
            "city": f.get("City"),
            "lat": f.get("Latitude"),
            "lng": f.get("Longitude"),
        }
    return lookup


def build_marker_lookup(records):
    """Build a dict of record_id → {locus, gene, chromosome, markerType}."""
    lookup = {}
    for r in records:
        f = r.get("fields", {})
        lookup[r["id"]] = {
            "locus": f.get("Locus"),
            "gene": f.get("Gene"),
            "chromosome": f.get("Chromosome"),
            "markerType": flatten_select(f.get("Marker Type")),
        }
    return lookup


def build_trial_site_lookup(records):
    """Build a dict of record_id → {name, country, lat, lng, institution}."""
    lookup = {}
    for r in records:
        f = r.get("fields", {})
        lookup[r["id"]] = {
            "name": f.get("Name"),
            "country": flatten_select(f.get("Country")),
            "lat": f.get("Latitude"),
            "lng": f.get("Longitude"),
            "institution": f.get("Institution"),
        }
    return lookup


def build_starter_lookup(records):
    """Build a dict of record_id → {name, grainBase, flavorProfile, originCountry}."""
    lookup = {}
    for r in records:
        f = r.get("fields", {})
        lookup[r["id"]] = {
            "name": f.get("Name"),
            "grainBase": flatten_select(f.get("Grain Base")),
            "flavorProfile": f.get("Flavor Profile"),
            "originCountry": flatten_select(f.get("Origin Country")),
        }
    return lookup


def build_grin_lookup(records):
    """Build a dict of record_id → {piNumber, species, originCountry}."""
    lookup = {}
    for r in records:
        f = r.get("fields", {})
        lookup[r["id"]] = {
            "piNumber": f.get("PI Number"),
            "species": f.get("Species"),
            "originCountry": f.get("Origin Country"),
        }
    return lookup


def build_disease_resistance_lookup(records):
    """Build a dict of record_id → {varietyOrGene, pathogen, resistanceLevel}."""
    lookup = {}
    for r in records:
        f = r.get("fields", {})
        lookup[r["id"]] = {
            "varietyOrGene": f.get("Variety or Gene"),
            "pathogen": flatten_select(f.get("Pathogen")),
            "resistanceLevel": flatten_select(f.get("Resistance Level")),
        }
    return lookup


# ─── Variety denormalization ──────────────────────────────────────────────────

def denormalize_variety(record, lookups):
    """Transform a raw Airtable variety record into the frontend JSON shape."""
    f = record.get("fields", {})
    prog_lookup, marker_lookup, site_lookup, starter_lookup, grin_lookup, disease_lookup = lookups

    crop = flatten_select(f.get("Crop"))
    crop_lower = (crop or "").lower()

    # Resolve linked records
    breeding_programs = []
    for rid in get_linked_ids(record, "Breeding Program"):
        prog = prog_lookup.get(rid)
        if prog and prog.get("institution"):
            breeding_programs.append({
                "institution": prog["institution"],
                "country": prog["country"],
            })

    markers = []
    for rid in get_linked_ids(record, "Cold Tolerance Markers"):
        m = marker_lookup.get(rid)
        if m and m.get("locus"):
            markers.append({
                "locus": m["locus"],
                "gene": m["gene"],
                "chromosome": m["chromosome"],
                "markerType": m["markerType"],
            })

    trial_sites = []
    for rid in get_linked_ids(record, "Field Trial Sites"):
        site = site_lookup.get(rid)
        if site and site.get("name"):
            trial_sites.append({
                "name": site["name"],
                "country": site["country"],
                "lat": site["lat"],
                "lng": site["lng"],
            })

    sourdough_starters = []
    for rid in get_linked_ids(record, "Sourdough Starters"):
        s = starter_lookup.get(rid)
        if s and s.get("name"):
            sourdough_starters.append({
                "name": s["name"],
                "grainBase": s["grainBase"],
                "flavorProfile": s["flavorProfile"],
            })

    grin_accessions = []
    for rid in get_linked_ids(record, "GRIN Accessions"):
        g = grin_lookup.get(rid)
        if g and g.get("piNumber"):
            grin_accessions.append({
                "piNumber": g["piNumber"],
                "species": g["species"],
                "originCountry": g["originCountry"],
            })

    disease_resistance = []
    for rid in get_linked_ids(record, "Disease Resistance"):
        d = disease_lookup.get(rid)
        if d and d.get("varietyOrGene"):
            disease_resistance.append({
                "varietyOrGene": d["varietyOrGene"],
                "pathogen": d["pathogen"],
                "resistanceLevel": d["resistanceLevel"],
            })

    # Parse seed sources (stored as plain text, semicolon-separated in some records)
    seed_sources_raw = f.get("Seed Sources") or ""
    seed_sources = [s.strip() for s in seed_sources_raw.split(";") if s.strip()]

    name = f.get("Name", "Unknown")

    return {
        "id": record["id"],
        "slug": slugify(name),
        "name": name,
        "species": f.get("Species"),
        "crop": crop_lower,
        "supercategory": CROP_SUPERCATEGORY.get(crop_lower, "other"),
        "country": flatten_select(f.get("Country")),
        "origin": f.get("Origin"),
        "usdaZone": f.get("USDA Zone"),
        "protein": f.get("Protein"),
        "traits": flatten_multi_select(f.get("Traits")),
        "endUse": flatten_multi_select(f.get("End Use")),
        "glutenStrength": flatten_select(f.get("Gluten Strength")),
        "status": flatten_select(f.get("Status")),
        "seedingRate": f.get("Seeding Rate"),
        "seedingDepth": f.get("Seeding Depth"),
        "seedingWindow": f.get("Seeding Window"),
        "daysToMaturity": f.get("Days to Maturity"),
        "rowSpacing": f.get("Row Spacing"),
        "harvestNotes": f.get("Harvest Notes"),
        "growerTips": f.get("Grower Tips"),
        "coldToleranceNotes": f.get("Cold Tolerance Notes"),
        "sourdoughNotes": f.get("Sourdough Notes"),
        "breadNotes": f.get("Bread Notes"),
        "maltProfile": f.get("Malt Profile"),
        "maltType": flatten_select(f.get("Malt Type")),
        "fallingNumber": f.get("Falling Number"),
        "testWeight": f.get("Test Weight"),
        "flourExtraction": f.get("Flour Extraction %"),
        "ashContent": f.get("Ash Content %"),
        "waterAbsorption": f.get("Water Absorption %"),
        "millingNotes": f.get("Milling Notes"),
        "seedSources": seed_sources,
        "markers": markers,
        "breedingPrograms": breeding_programs,
        "trialSites": trial_sites,
        "sourdoughStarters": sourdough_starters,
        "grinAccessions": grin_accessions,
        "diseaseResistance": disease_resistance,
    }


# ─── Secondary collection builders ───────────────────────────────────────────

def build_breeding_programs_json(records):
    """Build the standalone breeding_programs.json collection."""
    out = []
    for r in records:
        f = r.get("fields", {})
        out.append({
            "id": r["id"],
            "programId": f.get("Program ID"),
            "institution": f.get("Institution"),
            "country": flatten_select(f.get("Country")),
            "city": f.get("City"),
            "lat": f.get("Latitude"),
            "lng": f.get("Longitude"),
            "crops": f.get("Crops"),
            "focusAreas": f.get("Focus Areas"),
            "notableReleases": f.get("Notable Releases"),
            "establishedYear": f.get("Established Year"),
            "website": f.get("Website"),
        })
    return out


def build_field_trial_sites_json(records):
    """Build the standalone field_trial_sites.json collection."""
    out = []
    for r in records:
        f = r.get("fields", {})
        out.append({
            "id": r["id"],
            "siteId": f.get("Site ID"),
            "name": f.get("Name"),
            "country": flatten_select(f.get("Country")),
            "lat": f.get("Latitude"),
            "lng": f.get("Longitude"),
            "elevation": f.get("Elevation (m)"),
            "usdaZone": f.get("USDA Zone"),
            "trialTypes": flatten_multi_select(f.get("Trial Types")),
            "cropsTested": f.get("Crops Tested"),
            "active": f.get("Active"),
            "institution": f.get("Institution"),
            "meanJanTemp": f.get("Mean Jan Temp (°C)"),
            "recordLow": f.get("Record Low (°C)"),
            "snowCoverDays": f.get("Snow Cover Days"),
        })
    return out


def build_sourdough_starters_json(records):
    """Build the standalone sourdough_starters.json collection."""
    out = []
    for r in records:
        f = r.get("fields", {})
        out.append({
            "id": r["id"],
            "starterId": f.get("Starter ID"),
            "name": f.get("Name"),
            "originCountry": flatten_select(f.get("Origin Country")),
            "originCity": f.get("Origin City"),
            "estimatedAge": f.get("Estimated Age (years)"),
            "grainBase": flatten_select(f.get("Grain Base")),
            "flavorProfile": f.get("Flavor Profile"),
            "preservationMethod": flatten_select(f.get("Preservation Method")),
            "cultureType": flatten_select(f.get("Culture Type")),
            "hydration": f.get("Hydration %"),
            "breadStyle": flatten_multi_select(f.get("Bread Style")),
            "notes": f.get("Notes"),
        })
    return out


def build_seed_sources_json(records):
    """Build the standalone seed_sources.json collection."""
    out = []
    for r in records:
        f = r.get("fields", {})
        out.append({
            "id": r["id"],
            "sourceId": f.get("Source ID"),
            "name": f.get("Name"),
            "type": flatten_select(f.get("Type")),
            "country": flatten_select(f.get("Country")),
            "website": f.get("Website"),
            "shipsTo": f.get("Ships To"),
            "specialties": f.get("Specialties"),
            "access": f.get("Access"),
            "notes": f.get("Notes"),
        })
    return out


def build_distillery_profiles_json(records):
    """Build the standalone distillery_profiles.json collection."""
    out = []
    for r in records:
        f = r.get("fields", {})
        out.append({
            "id": r["id"],
            "distilleryId": f.get("Distillery ID"),
            "name": f.get("Name"),
            "country": flatten_select(f.get("Country")),
            "city": f.get("City"),
            "founded": f.get("Founded"),
            "spiritType": f.get("Spirit Type"),
            "heritageFocus": f.get("Heritage Focus"),
            "malting": flatten_select(f.get("Malting")),
            "lat": f.get("Latitude"),
            "lng": f.get("Longitude"),
            "website": f.get("Website"),
            "notes": f.get("Notes"),
        })
    return out


def build_community_projects_json(records):
    """Build the standalone community_projects.json collection."""
    out = []
    for r in records:
        f = r.get("fields", {})
        out.append({
            "id": r["id"],
            "projectId": f.get("Project ID"),
            "name": f.get("Name"),
            "country": flatten_select(f.get("Country")),
            "city": f.get("City"),
            "lat": f.get("Latitude"),
            "lng": f.get("Longitude"),
            "crops": flatten_multi_select(f.get("Crops")),
            "foundedYear": f.get("Founded Year"),
            "members": f.get("Members"),
            "hectares": f.get("Hectares"),
            "model": flatten_select(f.get("Model")),
            "focus": flatten_multi_select(f.get("Focus")),
            "varietiesGrown": f.get("Varieties Grown"),
            "website": f.get("Website"),
            "notes": f.get("Notes"),
        })
    return out


def build_planting_calendars_json(records):
    """Build the standalone planting-calendars.json collection."""
    out = []
    for r in records:
        f = r.get("fields", {})
        out.append({
            "crop": (flatten_select(f.get("Crop")) or "").lower(),
            "type": (flatten_select(f.get("Type")) or "").lower(),
            "zone": f.get("Zone") or "",
            "sowStart": f.get("Sow Start") or "",
            "sowEnd": f.get("Sow End") or "",
            "vern": f.get("Vernalization (weeks)") or "0",
            "harvest": f.get("Harvest Window") or "",
            "notes": f.get("Notes") or "",
        })
    return out


# ─── Slug deduplication ───────────────────────────────────────────────────────

def deduplicate_slugs(varieties):
    """Ensure all slugs are unique by appending -2, -3, etc. for duplicates."""
    seen = {}
    for v in varieties:
        slug = v["slug"]
        if slug in seen:
            seen[slug] += 1
            v["slug"] = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 1


# ─── Main pipeline ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VÄXT Airtable → Frontend JSON export")
    parser.add_argument(
        "--output-dir", default="frontend/public/data",
        help="Output directory for JSON files (default: frontend/public/data)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be fetched without making API calls"
    )
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — would fetch these tables:")
        for name, tid in TABLES.items():
            print(f"  {name}: {tid}")
        print(f"\nOutput dir: {args.output_dir}")
        return

    token = get_token()
    output_dir = args.output_dir

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # ── Step 1: Fetch all tables ──────────────────────────────────────────
    print("═══ VÄXT Export Pipeline ═══")
    print(f"Base: {BASE_ID}")
    print(f"Output: {output_dir}\n")
    print("Step 1: Fetching all tables from Airtable...")

    all_data = fetch_all_tables(token)

    total_records = sum(len(v) for v in all_data.values())
    print(f"\n  Total records fetched: {total_records}\n")

    # ── Step 2: Build lookup dicts ────────────────────────────────────────
    print("Step 2: Building lookup dictionaries...")

    prog_lookup = build_breeding_program_lookup(all_data["breeding_programs"])
    marker_lookup = build_marker_lookup(all_data["cold_markers"])
    site_lookup = build_trial_site_lookup(all_data["field_trial_sites"])
    starter_lookup = build_starter_lookup(all_data["sourdough_starters"])
    grin_lookup = build_grin_lookup(all_data["grin_accessions"])
    disease_lookup = build_disease_resistance_lookup(all_data["disease_resistance"])

    lookups = (prog_lookup, marker_lookup, site_lookup, starter_lookup, grin_lookup, disease_lookup)
    print(f"  Lookups built: {len(prog_lookup)} programs, {len(marker_lookup)} markers, "
          f"{len(site_lookup)} sites, {len(starter_lookup)} starters, "
          f"{len(grin_lookup)} GRIN, {len(disease_lookup)} disease")

    # ── Step 3: Denormalize varieties ─────────────────────────────────────
    print("\nStep 3: Denormalizing varieties...")

    varieties = []
    for record in all_data["varieties"]:
        try:
            v = denormalize_variety(record, lookups)
            varieties.append(v)
        except Exception as e:
            name = record.get("fields", {}).get("Name", "?")
            print(f"  WARNING: Failed to process variety '{name}': {e}", file=sys.stderr)

    deduplicate_slugs(varieties)

    # Sort by name for consistent output
    varieties.sort(key=lambda v: (v.get("name") or "").lower())

    print(f"  Denormalized {len(varieties)} varieties")

    # Supercategory counts
    cat_counts = {}
    for v in varieties:
        cat = v.get("supercategory", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for cat, count in sorted(cat_counts.items()):
        print(f"    {cat}: {count}")

    # Flag "other" supercategory records for manual review
    others = [v for v in varieties if v.get("supercategory") == "other"]
    if others:
        print(f"\n  ⚠ {len(others)} varieties mapped to 'other' — review these:")
        for v in others:
            print(f"    - {v['name']} (crop: {v['crop']})")

    # ── Step 4: Build secondary collections ───────────────────────────────
    print("\nStep 4: Building secondary collections...")

    breeding_programs = build_breeding_programs_json(all_data["breeding_programs"])
    field_trial_sites = build_field_trial_sites_json(all_data["field_trial_sites"])
    sourdough_starters = build_sourdough_starters_json(all_data["sourdough_starters"])
    seed_sources = build_seed_sources_json(all_data["seed_sources"])
    distillery_profiles = build_distillery_profiles_json(all_data["distillery_profiles"])
    community_projects = build_community_projects_json(all_data["community_projects"])
    planting_calendars = build_planting_calendars_json(all_data["planting_calendars"])

    # ── Step 5: Write JSON files ──────────────────────────────────────────
    print("\nStep 5: Writing JSON files...")

    files = {
        "varieties.json": varieties,
        "breeding_programs.json": breeding_programs,
        "field_trial_sites.json": field_trial_sites,
        "sourdough_starters.json": sourdough_starters,
        "seed_sources.json": seed_sources,
        "distillery_profiles.json": distillery_profiles,
        "community_projects.json": community_projects,
        "planting-calendars.json": planting_calendars,
    }

    total_size = 0
    for filename, data in files.items():
        filepath = os.path.join(output_dir, filename)
        content = json.dumps(data, indent=2, ensure_ascii=False)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        size = len(content.encode("utf-8"))
        total_size += size
        print(f"  {filename}: {len(data)} records, {size:,} bytes")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n═══ Export Complete ═══")
    print(f"  Files written: {len(files)}")
    print(f"  Total records: {sum(len(d) for d in files.values())}")
    print(f"  Total size: {total_size:,} bytes ({total_size / 1024:.0f} KB)")
    print(f"  Output dir: {os.path.abspath(output_dir)}")
    print(f"\n  Estimated gzipped size: ~{total_size // 6:,} bytes ({total_size // 6 // 1024:.0f} KB)")


if __name__ == "__main__":
    main()
