# -*- coding: utf-8 -*-
{
    "name": "Open Sales Order Lines by Product",
    "version": "19.0.1.1.1",
    "category": "Sales/Reporting",
    "summary": "Open Sales Order Lines by Product: pending quantities from confirmed orders, with filters by product and customer.",
    "description": """
<section class="oe_container">
    <div class="oe_row oe_spaced">
        <h2 class="oe_slogan" style="color:#714B67;">Open Sales Order Lines by Product</h2>
        <h3 class="oe_slogan">Pending delivery from confirmed sales orders</h3>
        <div class="oe_span12 text-justify oe_mt32">
            <p>
                Read-only report of sales order lines in state <strong>Sale</strong> where
                <strong>ordered quantity minus delivered quantity</strong> is still greater than zero.
                Use it to see what remains to ship, by product and customer, without opening each order.
            </p>
        </div>
    </div>
</section>
<section class="oe_container oe_dark">
    <div class="oe_row oe_spaced">
        <h3>What you get</h3>
        <ul>
            <li>List, pivot, graph, and form views on one SQL-backed model (fast on large data).</li>
            <li>Columns for order date, sales order, customer, product, ordered / delivered / pending qty, unit price, pending amount, currency, UoM.</li>
            <li>Search panel by customer and product (list, pivot, graph).</li>
            <li>Group by day, week, month, year, product, or customer.</li>
        </ul>
    </div>
</section>
<section class="oe_container">
    <div class="oe_row oe_spaced">
        <h3>Technical notes</h3>
        <ul>
            <li>Read-only; no stock moves are created from this screen.</li>
            <li>Confirmed orders only; excludes down payments, section/note lines, and lines without a product.</li>
            <li>Requires <strong>Sales</strong> and <strong>Inventory</strong> (stock user group for the menu).</li>
        </ul>
    </div>
</section>
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
