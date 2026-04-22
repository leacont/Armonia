# -*- coding: utf-8 -*-
from odoo import _, fields, models


class MrpPlanningWcMicroWizard(models.TransientModel):
    _name = "mrp.planning.wc.micro.wizard"
    _description = "Micro planning by workcenter"

    workcenter_id = fields.Many2one(
        "mrp.workcenter",
        string="Work Center",
        required=True,
        index=True,
    )

    def action_open_micro_planner(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "planning_drag_generic_19.action_mrp_planning_wc_line"
        )
        action = dict(action)
        action["name"] = _("Micro planning: %s") % (self.workcenter_id.display_name,)
        action["domain"] = [
            ("workcenter_id", "=", self.workcenter_id.id),
            ("planning_order_id.active", "=", True),
            ("planning_order_id.planning_manual_completed", "=", False),
        ]
        action["context"] = dict(
            self.env.context or {},
            default_workcenter_id=self.workcenter_id.id,
        )
        return action
