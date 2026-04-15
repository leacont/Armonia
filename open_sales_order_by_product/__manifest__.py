# -*- coding: utf-8 -*-
{
    "name": "Open Sales Order Report",
    "version": "19.0.1.1.5",
    "category": "Sales/Reporting",
    "summary": "Open Sales Order Report: pending quantities from confirmed orders, with filters by product and customer.",
    "description": """
Open Sales Order Report
=======================

Pending delivery from confirmed sales orders.

Read-only report of sales order lines in Sale state where ordered quantity
minus delivered quantity is still greater than zero. Use it to see what
remains to ship, by product and customer, without opening each order.

What you get
------------
- List, pivot, graph, and form views on one SQL-backed model (fast on large data).
- Columns: order date, sales order, customer, product, ordered / delivered / pending qty, unit price, pending amount, currency, UoM.
- Search panel by customer and product (list, pivot, graph).
- Group by day, week, month, year, product, or customer.

Technical notes
---------------
- Read-only; no stock moves are created from this screen.
- Confirmed orders only; excludes down payments, section/note lines, and lines without a product.
- Depends on sale_management and stock. Menu is visible to Inventory users (stock user group).

Visuals
-------
Icon, banner, and screenshots (screen_01..03) live under static/description/.
On your own Odoo server, Apps uses index.html there for the full layout with images.
Odoo.com App Store listing does not render HTML from this field; upload images there separately if needed.
""",
    "author": "Armonia",
    "website": "https://www.armonia.com.ar",
    "license": "OPL-1",
    "price": 14.0,
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


