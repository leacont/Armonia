# -*- coding: utf-8 -*-
{
    "name": "Manufacturing Planning Drag (Generic)",
    "version": "19.0.1.50.0",
    "summary": "Drag & drop production sequencer with real-time work center status, Rush priority and automatic scheduling.",
    "category": "Manufacturing/Manufacturing",
    "author": "Armonia",
    "website": "mailto:armonia.odoo@gmail.com",
    "license": "OPL-1",
    "price": 150,
    "currency": "USD",
    "application": True,
    "depends": ["mrp", "resource", "web"],
    "data": [
        "data/default_config_parameters.xml",
        "security/ir.model.access.csv",
        "views/planning_report_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/mrp_planning_wc_micro_wizard_views.xml",
        "views/planning_order_views.xml",
        "data/ir_cron_data.xml",
    ],
    "installable": True,
    "images": [
        "static/description/banner.png",
        "static/description/images/screenshot_sequencer.png",
        "static/description/images/screenshot_drag.png",
        "static/description/images/screenshot_rush.png",
        "static/description/images/screenshot_micro.png",
        "static/description/images/screenshot_report.png",
    ],
    "assets": {
        "web.assets_backend": [
            "planning_drag_generic_19/static/src/css/planning_wc_status.css",
            "planning_drag_generic_19/static/src/js/planning_list_legend.js",
            "planning_drag_generic_19/static/src/js/planning_list_wc_columns.js",
        ],
    },
}
