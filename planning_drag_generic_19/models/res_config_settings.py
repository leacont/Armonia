# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    planning_drag_scheduling_mode = fields.Selection(
        [
            ("manual", "Manual"),
            ("auto", "Automatic"),
        ],
        string="Planning Scheduling Mode",
        default="manual",
        config_parameter="planning_drag_generic_19.scheduling_mode",
        help="Manual: only applies when the user clicks apply. "
             "Automatic: applies from cron using the planning sequence.",
    )

    planning_drag_sync_reservation = fields.Boolean(
        string="Align component reservations with planning sequence",
        default=True,
        config_parameter="planning_drag_generic_19.sync_reservation_with_sequence",
        help="When applying the schedule, unreserve affected MOs, stamp component move dates "
             "by planning rank, optionally set MO priority for the first row, then re-assign in "
             "planning order so earlier rows claim stock first.",
    )
    planning_drag_reservation_scope = fields.Selection(
        [
            ("mo_tree", "Root MO + linked MOs (recommended)"),
            ("root_only", "Root MO only"),
        ],
        string="Reservation scope",
        default="mo_tree",
        config_parameter="planning_drag_generic_19.reservation_sync_scope",
        help="Which manufacturing orders receive the reservation ranking when a planning row applies.",
    )
    planning_drag_reservation_delta = fields.Integer(
        string="Reservation rank spacing (minutes)",
        default=5,
        config_parameter="planning_drag_generic_19.reservation_rank_delta_minutes",
        help="Extra minutes added per planning row rank for component move scheduled dates "
             "(finer ordering among same MO priority). Minimum 1.",
    )
    planning_drag_reservation_mo_priority = fields.Boolean(
        string="Mark first planning row as Urgent (MO priority)",
        default=True,
        config_parameter="planning_drag_generic_19.reservation_mo_priority_first",
        help="Sets standard MO priority to Urgent for all orders in the first open planning row "
             "(others Normal). Works together with move dates for reservation order.",
    )
    planning_drag_cron_replan_today = fields.Boolean(
        string="Cron always replans from now",
        default=False,
        config_parameter="planning_drag_generic_19.cron_replan_today",
        help="When enabled and scheduling mode is Automatic, each cron run re-anchors scheduling "
             "from current time (today) instead of preserving older planned starts.",
    )
    planning_drag_use_workcenter_calendar = fields.Boolean(
        string="Use workcenter calendar availability",
        default=True,
        config_parameter="planning_drag_generic_19.use_workcenter_calendar",
        help="Compute WO dates with operation durations and each workcenter working calendar "
             "(attendances/leaves).",
    )

    def action_refresh_planning_workcenters(self):
        """Re-apply work center names/order to planning list headers and invalidate WC slot data."""
        self.env["mrp.planning.order"].sudo()._planning_refresh_after_workcenter_change()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Work centers"),
                "message": _(
                    "Planning list headers and work center columns were updated. "
                    "Re-open the Planning Sequencer or refresh the browser (F5) if you still see old names. "
                    "Only active work centers in your company are shown, in work center list order (up to 16)."
                ),
                "type": "success",
                "sticky": False,
            },
        }
