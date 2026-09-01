# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    # Aligns shop-floor lists with planning / micro-apply order without changing BoM operation
    # sequence. Updated whenever global or micro schedule runs.
    planning_drag_seq = fields.Integer(
        string="Planning queue",
        default=0,
        copy=False,
        index=True,
        help="Ordering hint from Manufacturing Planning Drag; lower runs first in default views.",
    )

    _order = "planning_drag_seq asc, sequence asc, date_start asc, leave_id asc, id asc"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["mrp.planning.order"].sudo()._invalidate_planning_display_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self and any(
            k in vals
            for k in (
                "state",
                "workcenter_id",
                "production_id",
                "date_start",
                "date_finished",
                "name",
                "qty_produced",
                "qty_producing",
                "qty_production",
            )
        ):
            self.env["mrp.planning.order"].sudo()._invalidate_planning_display_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["mrp.planning.order"].sudo()._invalidate_planning_display_cache()
        return res
