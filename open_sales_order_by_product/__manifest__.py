# -*- coding: utf-8 -*-
{
    "name": "Open Sales Order Lines by Product",
    "version": "19.0.1.1.0",
    "category": "Sales/Reporting",
    "summary": "Open Sales Order Lines by Product: pending quantities from confirmed orders, with filters by product and customer.",
    "description": """
<h1 style="font-size:36px;">Open Sales Order Lines by Product</h1>

<p style="font-size:16px;">
Get a clear and centralized view of all products that are still pending delivery from confirmed Sales Orders.
</p>

<img src="/open_sales_order_by_product/static/description/banner.png" style="width:100%; border-radius:12px;"/>

<hr/>

<h2>📊 See All Pending Items in One Place</h2>

<p>
This report shows all Sales Order lines where there is still quantity pending delivery.
</p>

<img src="/open_sales_order_by_product/static/description/screen_01.png" style="width:100%; border-radius:10px;"/>

<ul>
<li>✔ Ordered vs Delivered vs Pending quantities</li>
<li>✔ Pending quantity highlighted clearly</li>
<li>✔ Pending amount calculation</li>
</ul>

<hr/>

<h2>🔎 Filter by Customer or Product</h2>

<p>
Quickly filter the report using the built-in search panel to focus on specific customers or products.
</p>

<img src="/open_sales_order_by_product/static/description/screen_02.png" style="width:100%; border-radius:10px;"/>

<ul>
<li>✔ Filter by customer</li>
<li>✔ Filter by product</li>
<li>✔ Instant recalculation of totals</li>
</ul>

<hr/>

<h2>📄 From Sales Orders to Actionable Report</h2>

<p>
Instead of reviewing Sales Orders one by one, this module consolidates all pending delivery lines into a single report.
</p>

<img src="/open_sales_order_by_product/static/description/screen_03.png" style="width:100%; border-radius:10px;"/>

<ul>
<li>✔ Identify what still needs to be delivered</li>
<li>✔ Understand customer commitments</li>
<li>✔ Improve follow-up and delivery planning</li>
</ul>

<hr/>

<h2>📈 Analysis & Reporting</h2>

<p>
Use list, pivot, and graph views to analyze open quantities by product or customer.
</p>

<ul>
<li>✔ Group by product</li>
<li>✔ Group by customer</li>
<li>✔ Identify high pending volumes</li>
</ul>

<hr/>

<h2>⚙️ Technical Details</h2>

<ul>
<li>✔ Read-only SQL-based report</li>
<li>✔ Includes confirmed Sales Orders only</li>
<li>✔ Excludes down payments and non-product lines</li>
<li>✔ Shows only lines with pending delivery quantity</li>
</ul>
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
