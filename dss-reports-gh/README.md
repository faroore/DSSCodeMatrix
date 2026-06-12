# DSS Reports

Interactive HTML dashboard generator for DSS (Distributor Support System) data.

## Reports

| Report | Script | Input | Output |
|--------|--------|-------|--------|
| **Advisors by Channel** | `reports/advisors_by_channel.py` | `data/Advisors_by_Channel.csv` | `output/advisors_by_channel_report.html` |
| **Channel Mandatory Requirements** | `reports/channel_mandatory_requirements.py` | `data/channel_mandatoryrequirements_finalprod.csv` | `output/channel_mandatoryrequirements_finalprod.html` |
| **Entity Classification** | `reports/entity_classification.py` | `data/tables.sql` | `output/dss_entity_classification.html` |

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place input data files in data/ folder (see above)

# 4. Generate all reports
python run.py --all

# 5. Generate a specific report
python run.py --advisors
python run.py --mandatory
python run.py --entity

# 6. Launch dashboard server (opens browser)
python run.py --serve
```

## Project Structure

```
dss-reports/
├── run.py                  # Main launcher (CLI)
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── data/                   # Input data files (CSV, SQL)
├── output/                 # Generated HTML reports
└── reports/                # Report generator scripts
    ├── __init__.py
    ├── advisors_by_channel.py
    ├── channel_mandatory_requirements.py
    └── entity_classification.py
```

## Data Sources

- **Advisors_by_Channel.csv**: Extracted from MS_DSS_A1 via SQL query (party_contract_manu → party_contract → party_role_instance → party → adm_channel)
- **channel_mandatoryrequirements_finalprod.csv**: Channel mandatory requirements export
- **tables.sql**: DDL schema from MS_DSS_A1 database (`docs/SQL-DB/MS_DSS_A1/tables.sql` in main repo)

## Features

All reports include:
- Dark/light mode toggle
- Interactive charts (Chart.js)
- Searchable, sortable data tables
- CSV export
- Keyboard shortcuts (`/` to search)
- Print-friendly layout
