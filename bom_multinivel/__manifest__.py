# -*- coding: utf-8 -*-
# Not auto-installed: install manually from Apps (requires Manufacturing and Sales). Odoo 19.
{
    "name": "Multilevel BOM",
    "version": "19.0.1.0.3",
    "summary": "[Odoo 19] Project number and multilevel manufacturing order explosion on confirm",
    "description": """
Odoo 19.0 — Requires a 19.0 server / branch.

Features:
- Sequence and inheritance of Project Number on manufacturing orders (root MO and children linked by origin).
- Recursive propagation when confirming an MO: for each BoM line, finds a manufacturing BoM for the component
  (normal type) or expands phantom kits; creates child MOs up to 25 levels; skips subcontracting and lines
  ignored by variants (_skip_bom_line). BoM lookup matches standard MO behaviour (company, operation type, active_test).

If another module also creates child MOs on confirm (e.g. a mass router scheduler), you may get overlapping logic:
use only one approach or align dependencies.
    """,
    "category": "Manufacturing",
    "author": "Armonia",
    "license": "LGPL-3",
    "auto_install": False,
    "application": True,
    "sequence": 20,
    "depends": ["mrp", "sale"],
    "data": [
        "data/project_number_sequence.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
}
