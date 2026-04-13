# -*- coding: utf-8 -*-
# No auto-instalación: instalar manualmente desde Apps (requiere mrp + sale). Odoo 19.
{
    "name": "BOM multinivel",
    "version": "19.0.1.0.1",
    "summary": "[Odoo 19] Project number y explosión multinivel de MOs al confirmar",
    "description": """
Odoo 19.0 — Requiere servidor en rama / versión 19.0.

Unifica la lógica de:
- Secuencia y herencia de Project Number en mrp.production (MO raíz e hijas por origin).
- Propagación recursiva al confirmar la MO: por cada línea de la LdM busca una LdM de tipo
  fabricación (normal) del componente y crea la MO hija; hasta 25 niveles; omite subcontratación
  y líneas saltadas por variantes (_skip_bom_line). Usa el mismo criterio de búsqueda de LdM
  que la MO estándar (empresa, tipo de operación, active_test).

Si también tiene instalado otro módulo que confirme y genere MO hijas (p. ej. Mass Router
Production Scheduler), puede haber doble lógica: use solo uno o unifique dependencias.
    """,
    "category": "Manufacturing",
    "author": "FCS / Leandro Contino",
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
