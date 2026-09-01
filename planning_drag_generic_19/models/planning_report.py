# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpPlanningReport(models.Model):
    _name = "mrp.planning.report"
    _description = "Manufacturing Planning Report"
    _order = "workcenter_sequence asc, workcenter_id asc, id desc"

    report_datetime = fields.Datetime(required=True, index=True, default=fields.Datetime.now)
    report_date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    planning_order_id = fields.Many2one("mrp.planning.order", ondelete="set null", index=True)
    root_production_id = fields.Many2one("mrp.production", ondelete="set null", index=True)
    product_id = fields.Many2one("product.product", index=True)
    workcenter_id = fields.Many2one("mrp.workcenter", required=True, index=True)
    workcenter_sequence = fields.Integer(index=True, default=10)
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("progress", "In Progress"),
            ("done", "Done"),
            ("idle", "Idle"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        index=True,
        default="idle",
    )
    pending_wo_count = fields.Integer(default=0)
    done_wo_count = fields.Integer(default=0)
    total_wo_count = fields.Integer(default=0)
    next_planned_datetime = fields.Datetime()
    planning_order_count = fields.Integer(default=0, string="Orders")
    planned_qty = fields.Float(default=0.0, string="Planned Qty")
    produced_qty = fields.Float(default=0.0, string="Declared")
    pending_qty = fields.Float(default=0.0, string="Pending")
    completion_pct = fields.Float(default=0.0, string="Completion %")
    completion_label = fields.Char(compute="_compute_completion_label", store=False)
    bar_style = fields.Char(compute="_compute_bar_style", store=False)
    progress_state = fields.Selection(
        [
            ("idle", "Idle"),
            ("danger", "Low"),
            ("warning", "Medium"),
            ("success", "High"),
        ],
        default="idle",
        index=True,
    )
    order_lines_text = fields.Text(string="Orders Detail")

    @api.model
    def _wo_schedule_field(self):
        wo_fields = self.env["mrp.workorder"]._fields
        if "date_start" in wo_fields:
            return "date_start"
        if "date_planned_start" in wo_fields:
            return "date_planned_start"
        if "production_date" in wo_fields:
            return "production_date"
        return False

    @api.depends("completion_pct")
    def _compute_completion_label(self):
        for rec in self:
            rec.completion_label = "%s%%" % int(round(float(rec.completion_pct or 0.0)))

    @api.depends("completion_pct")
    def _compute_bar_style(self):
        for rec in self:
            pct = max(0.0, min(100.0, float(rec.completion_pct or 0.0)))
            rec.bar_style = "width: %.1f%%;" % pct

    @api.model
    def _empty_bucket(self, workcenter):
        return {
            "workcenter_id": workcenter.id,
            "workcenter_sequence": int(getattr(workcenter, "sequence", 0) or 10),
            "planning_order_ids": set(),
            "wo_ids": set(),
            "pending_wo_count": 0,
            "done_wo_count": 0,
            "total_wo_count": 0,
            "next_planned_datetime": False,
            "planned_qty": 0.0,
            "produced_qty": 0.0,
            "pending_qty": 0.0,
            "order_qty": {},
        }

    @api.model
    def refresh_from_live_data(self, force=True):
        """Rebuild a snapshot with one row per workcenter (declared vs pending)."""
        Report = self.sudo().with_context(planning_report_skip_refresh=True)
        now_dt = fields.Datetime.now()
        if not force:
            latest = Report.search([], limit=1, order="report_datetime desc")
            if (
                latest
                and latest.report_datetime
                and (now_dt - latest.report_datetime).total_seconds() < 5
            ):
                return True

        Report.search([]).unlink()
        today_date = fields.Date.context_today(self)
        Planning = self.env["mrp.planning.order"].sudo()
        Planning._sync_from_mrp()
        configured = Planning._configured_workcenters_ordered()
        by_wc = {wc.id: self._empty_bucket(wc) for wc in configured}

        orders = Planning.with_context(planning_generic_synced=True).search(
            [
                ("active", "=", True),
                ("planning_manual_completed", "=", False),
            ]
        )
        wo_model = self.env["mrp.workorder"].sudo()
        schedule_field = self._wo_schedule_field()

        for order in orders:
            mos = order._related_mos()
            if not mos:
                continue
            wos = wo_model.search(
                [
                    ("production_id", "in", mos.ids),
                    ("workcenter_id", "!=", False),
                ]
            )
            for wo in wos:
                if Planning._planning_wo_is_cancelled(wo.state):
                    continue
                wc = wo.workcenter_id
                if wc.id not in by_wc:
                    by_wc[wc.id] = self._empty_bucket(wc)
                bucket = by_wc[wc.id]
                if wo.id in bucket["wo_ids"]:
                    continue
                bucket["wo_ids"].add(wo.id)
                bucket["planning_order_ids"].add(order.id)
                bucket["total_wo_count"] += 1

                is_open = Planning._planning_wo_is_open(wo.state)
                is_done = Planning._planning_wo_is_done(wo.state)
                if is_open:
                    bucket["pending_wo_count"] += 1
                elif is_done:
                    bucket["done_wo_count"] += 1

                if schedule_field:
                    next_dt = getattr(wo, schedule_field, False)
                    if is_open and next_dt and (
                        not bucket["next_planned_datetime"]
                        or next_dt < bucket["next_planned_datetime"]
                    ):
                        bucket["next_planned_datetime"] = next_dt

                produced = float(getattr(wo, "qty_produced", 0.0) or 0.0)
                if is_open:
                    pending = float(getattr(wo, "qty_remaining", 0.0) or 0.0)
                    if pending <= 0 and produced <= 0:
                        pending = float(getattr(wo, "qty_production", 0.0) or 0.0)
                else:
                    pending = 0.0
                planned = produced + pending
                if planned <= 0:
                    planned = float(getattr(wo, "qty_production", 0.0) or 0.0)

                bucket["produced_qty"] += produced
                bucket["pending_qty"] += pending
                bucket["planned_qty"] += planned

                order_name = (
                    (wo.production_id and wo.production_id.name)
                    or (order.root_production_id and order.root_production_id.name)
                    or order.display_name
                    or "-"
                )
                produced_so_far, pending_so_far = bucket["order_qty"].get(order_name, (0.0, 0.0))
                bucket["order_qty"][order_name] = (
                    produced_so_far + produced,
                    pending_so_far + pending,
                )

        vals_list = []
        for agg in by_wc.values():
            planned_qty = float(agg["planned_qty"] or 0.0)
            produced_qty = float(agg["produced_qty"] or 0.0)
            pending_qty = float(agg["pending_qty"] or 0.0)
            denom = produced_qty + pending_qty
            pct = (produced_qty / denom * 100.0) if denom > 0 else 0.0
            if pending_qty <= 0 and produced_qty > 0:
                status = "done"
                state = "success"
            elif produced_qty > 0 and pending_qty > 0:
                status = "progress"
                state = "warning" if pct < 90.0 else "success"
            elif pending_qty > 0:
                status = "pending"
                state = "danger"
            else:
                status = "idle"
                state = "idle"
            order_lines = [
                "%s · %.0f declared / %.0f pending" % (name, produced, pending)
                for name, (produced, pending) in agg["order_qty"].items()
            ]
            vals_list.append(
                {
                    "report_datetime": now_dt,
                    "report_date": today_date,
                    "workcenter_id": agg["workcenter_id"],
                    "workcenter_sequence": int(agg["workcenter_sequence"] or 10),
                    "status": status,
                    "pending_wo_count": int(agg["pending_wo_count"] or 0),
                    "done_wo_count": int(agg["done_wo_count"] or 0),
                    "total_wo_count": int(agg["total_wo_count"] or 0),
                    "next_planned_datetime": agg["next_planned_datetime"],
                    "planning_order_count": len(agg["planning_order_ids"]),
                    "planned_qty": planned_qty,
                    "produced_qty": produced_qty,
                    "pending_qty": pending_qty,
                    "completion_pct": pct,
                    "progress_state": state,
                    "order_lines_text": "\n".join(order_lines[:8]),
                }
            )
        if vals_list:
            Report.create(vals_list)
        try:
            return self.env["ir.actions.act_window"]._for_xml_id(
                "planning_drag_generic_19.action_mrp_planning_report"
            )
        except ValueError:
            return True
