# -*- coding: utf-8 -*-
from odoo import api, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["mrp.planning.order"].sudo()._planning_refresh_after_workcenter_change()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals:
            self.env["mrp.planning.order"].sudo()._planning_refresh_after_workcenter_change()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["mrp.planning.order"].sudo()._planning_refresh_after_workcenter_change()
        return res

    def action_open_micro_planning(self):
        self.ensure_one()
        action = self.env.ref("planning_drag_generic_19.action_mrp_planning_wc_line").read()[0]
        action["domain"] = [
            ("workcenter_id", "=", self.id),
            ("planning_order_id.active", "=", True),
            ("planning_order_id.planning_manual_completed", "=", False),
        ]
        action["context"] = {"default_workcenter_id": self.id}
        return action

    def action_apply_micro_planning(self):
        lines = self.env["mrp.planning.wc.line"].sudo().search(
            [
                ("workcenter_id", "in", self.ids),
                ("planning_order_id.active", "=", True),
                ("planning_order_id.planning_manual_completed", "=", False),
            ],
            order="sequence asc, id asc",
        )
        if lines:
            lines.action_apply_workcenter_schedule()
        return True
