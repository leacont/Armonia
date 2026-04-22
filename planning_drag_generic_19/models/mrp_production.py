# -*- coding: utf-8 -*-
from odoo import api, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def write(self, vals):
        res = super().write(vals)
        if self and any(k in vals for k in ("state", "product_qty", "name", "origin")):
            self.env["mrp.planning.order"].sudo()._invalidate_planning_display_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["mrp.planning.order"].sudo()._invalidate_planning_display_cache()
        return res
