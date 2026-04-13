# -*- coding: utf-8 -*-
{
    "name": "Open Sales Order Lines by Product",
    "version": "19.0.1.0.8",
    "category": "Sales/Reporting",
    "summary": "Instant visibility of pending product deliveries from all confirmed Sales Orders (Odoo 19).",
    "description": """
Pending Sales Orders by Product (Odoo 19 Enterprise/Community)
=============================================================

Stop hunting through multiple Sales Orders to find out what products you still need to
deliver. This module provides an instant, read-only dashboard of all confirmed sales order
lines that have a remaining quantity to be delivered (Ordered Qty - Delivered Qty).

Key Benefits for Your Business:
-------------------------------
* **Optimize inventory:** See which products are committed to customers and still pending delivery.
* **Improve customer service:** Answer fulfilment questions from one consolidated view.
* **Save time:** Reduce manual spreadsheets and repetitive searching; group by product or customer.
* **Decision making:** Spot products that are often ordered but slow to ship.

Technical Features:
-------------------
* High-performance SQL view (`open_sales_report`) for fast loading with large datasets.
* Odoo 19 list, graph, and pivot views.
* Works with standard Sales and Inventory apps.

Requires: ``sale_management`` and ``stock``.
    """,
    "author": "Armonia",
    "website": "https://www.armonia.com.ar",
    "license": "OPL-1",
    "price": 5.00,
    "currency": "USD",
    "depends": ["sale_management", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/open_sales_report_views.xml",
    ],
    "images": [
        "static/description/icon.png",
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
