from odoo import models, fields, tools


class OpenSalesReport(models.Model):
    _name = "open.sales.report"
    _description = "Open Sales Order Lines by Product"
    _auto = False
    _order = "date_order desc, id"

    sale_order_id = fields.Many2one("sale.order", string="Sales Order")
    partner_id = fields.Many2one("res.partner", string="Customer")
    product_id = fields.Many2one("product.product", string="Product")
    product_uom_id = fields.Many2one("uom.uom", string="UoM")
    product_uom_qty = fields.Float(string="Ordered Qty")
    qty_delivered = fields.Float(string="Delivered Qty")
    qty_pending = fields.Float(string="Pending Qty")
    date_order = fields.Datetime(string="Order Date")

    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    amount_pending = fields.Monetary(
        string="Amount Pending",
        currency_field="currency_id",
        readonly=True,
    )
    price_unit = fields.Monetary(
        string="Unit Price",
        currency_field="currency_id",
        readonly=True,
    )

    # Placeholders (always NULL in SQL): custom/Studio list views may still reference these names.
    x_studio_customer_po = fields.Char(string="Customer PO")
    x_studio_tag = fields.Char(string="Tag")
    x_studio_udc = fields.Char(string="UDC")
    type_of_product = fields.Selection(
        [
            ("Sales", "Sales"),
            ("Sample", "Sample"),
            ("Marketing Sample", "Marketing Sample"),
            ("Test", "Test"),
        ],
        string="Type of Product",
    )
    type_of_product_order = fields.Integer(string="Type of Product Order")
    card_brand = fields.Selection(
        [
            ("Master Card", "Master Card"),
            ("Visa", "Visa"),
            ("Other", "Other"),
        ],
        string="Card Brand",
    )
    amatech = fields.Boolean(string="Amatech")

    def init(self):
        # Odoo 19: sale_order_line column is product_uom_id (not product_uom).
        tools.drop_view_if_exists(self.env.cr, "open_sales_report")
        self.env.cr.execute(
            """
            CREATE VIEW open_sales_report AS (
                SELECT
                    sol.id AS id,
                    so.id AS sale_order_id,
                    so.partner_id AS partner_id,
                    sol.product_id AS product_id,
                    sol.product_uom_id AS product_uom_id,
                    sol.product_uom_qty AS product_uom_qty,
                    sol.qty_delivered AS qty_delivered,
                    (sol.product_uom_qty - sol.qty_delivered) AS qty_pending,
                    so.currency_id AS currency_id,
                    sol.price_unit AS price_unit,
                    (sol.product_uom_qty - sol.qty_delivered) * COALESCE(sol.price_unit, 0) AS amount_pending,
                    so.date_order AS date_order,
                    NULL::character varying AS x_studio_customer_po,
                    NULL::character varying AS x_studio_tag,
                    NULL::character varying AS x_studio_udc,
                    NULL::character varying AS type_of_product,
                    NULL::integer AS type_of_product_order,
                    NULL::character varying AS card_brand,
                    NULL::boolean AS amatech
                FROM sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                WHERE so.state = 'sale'
                  AND sol.display_type IS NULL
                  AND (sol.is_downpayment IS NOT TRUE)
                  AND sol.product_id IS NOT NULL
                  AND (sol.product_uom_qty - sol.qty_delivered) > 0
            )
            """
        )
