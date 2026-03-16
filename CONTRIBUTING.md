# Contributing to VAXT Data

Thank you for your interest in contributing to the VAXT heritage grain data repository.

## Ways to Contribute

### Data corrections
If you find an error in a CSV dataset (wrong coordinates, misspelled variety name, incorrect marker data), please open an issue using the **Data Correction** template.

### New variety submissions
Have data on a heritage grain variety not in our index? Open an issue using the **New Variety** template with as much detail as you can provide.

### ETL scripts
If you want to add a new data source or improve an existing ETL pipeline:

1. Fork the repository
2. Create a feature branch (`git checkout -b add-source-xyz`)
3. Add your script to `scripts/` and register it in `sources.toml`
4. Run `make validate` to ensure nothing breaks
5. Open a pull request

### Documentation
Improvements to the data dictionary, README, or inline comments are always welcome.

## Development Setup

```bash
git clone https://github.com/vaxt-foundation/vaxt-data.git
cd vaxt-data
make bootstrap
make doctor
make validate
```

## Code Style

- Python 3.11+ (for `tomllib`)
- Use `urllib.request` for HTTP calls — no `requests` library
- Follow existing patterns in the codebase
- All path constants go through `scripts/_paths.py`

## CSV Conventions

- UTF-8 encoding, comma-delimited
- First row is always headers
- Use empty string (not "N/A" or "null") for missing values
- Coordinates in decimal degrees (WGS84)
- Dates in ISO 8601 format (YYYY-MM-DD)

## Commit Messages

Use conventional commits:
- `fix: correct latitude for SITE-023`
- `feat: add Estonian breeding programs`
- `docs: update data dictionary for sourdough_recipes`

## License

By contributing, you agree that your contributions will be licensed under:
- **MIT** for code (scripts, Makefile, CI)
- **CC BY 4.0** for data (CSVs, schemas, documentation)
