# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpPlanningReport(models.Model):
    _name = "mrp.planning.report"
    _description = "Manufacturing Planning Report"
    _order = "report_date desc, completion_pct desc, workcenter_id asc, id desc"

    report_datetime = fields.Datetime(required=True, index=True, default=fields.Datetime.now)
    report_date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    planning_order_id = fields.Many2one("mrp.planning.order", ondelete="set null", index=True)
    root_production_id = fields.Many2one("mrp.production", ondelete="set null", index=True)
    product_id = fields.Many2one("product.product", index=True)
    workcenter_id = fields.Many2one("mrp.workcenter", required=True, index=True)
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        index=True,
    )
    pending_wo_count = fields.Integer(default=0)
    done_wo_count = fields.Integer(default=0)
    total_wo_count = fields.Integer(default=0)
    next_planned_datetime = fields.Datetime()
    planning_order_count = fields.Integer(default=0, string="Orders")
    planned_qty = fields.Float(default=0.0, string="Planned Qty Today")
    produced_qty = fields.Float(default=0.0, string="Produced Qty Today")
    completion_pct = fields.Float(default=0.0, string="Completion %")
    completion_label = fields.Char(compute="_compute_completion_label", store=False)
    progress_state = fields.Selection(
        [
            ("danger", "Low"),
            ("warning", "Medium"),
            ("success", "High"),
        ],
        default="danger",
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

    @api.model
    def _wo_qty_field(self):
        wo_fields = self.env["mrp.workorder"]._fields
        if "qty_production" in wo_fields:
            return "qty_production"
        if "qty_producing" in wo_fields:
            return "qty_producing"
        return False

    @api.depends("completion_pct")
    def _compute_completion_label(self):
        for rec in self:
            rec.completion_label = "%.1f%%" % float(rec.completion_pct or 0.0)

    @api.model
    def refresh_from_live_data(self):
        """Rebuild today's report snapshot aggregated by workcenter."""
        self.search([]).unlink()
        lines = self.env["mrp.planning.wc.line"].sudo().search(
            [
                ("planning_order_id.active", "=", True),
                ("planning_order_id.planning_manual_completed", "=", False),
            ],
            order="workcenter_id asc, sequence asc, id asc",
        )
        now_dt = fields.Datetime.now()
        today_date = fields.Date.context_today(self)
        start_dt = fields.Datetime.to_datetime("%s 00:00:00" % today_date)
        end_dt = fields.Datetime.to_datetime("%s 23:59:59" % today_date)
        wo_model = self.env["mrp.workorder"].sudo()
        schedule_field = self._wo_schedule_field()
        qty_field = self._wo_qty_field()
        open_states = list(self.env["mrp.planning.order"]._planning_wo_open_states_exclude())
        by_wc = {}

        for line in lines:
            wc = line.workcenter_id
            if not wc:
                continue
            bucket = by_wc.setdefault(
                wc.id,
                {
                    "workcenter_id": wc.id,
                    "planning_order_ids": set(),
                    "pending_wo_count": 0,
                    "done_wo_count": 0,
                    "total_wo_count": 0,
                    "next_planned_datetime": False,
                    "planned_qty": 0.0,
                    "produced_qty": 0.0,
                    "orders": [],
                },
            )
            bucket["planning_order_ids"].add(line.planning_order_id.id)

            mos = line.planning_order_id._related_mos()
            if not mos:
                continue
            domain = [
                ("production_id", "in", mos.ids),
                ("workcenter_id", "=", wc.id),
            ]
            if schedule_field:
                domain.extend([(schedule_field, ">=", start_dt), (schedule_field, "<=", end_dt)])
            todays_wos = wo_model.search(domain, order="id asc")
            if not todays_wos:
                continue

            pending = todays_wos.filtered(lambda w: w.state not in open_states)
            done = todays_wos.filtered(lambda w: w.state == "done")
            bucket["pending_wo_count"] += len(pending)
            bucket["done_wo_count"] += len(done)
            bucket["total_wo_count"] += len(todays_wos)

            if schedule_field:
                next_dt = min((getattr(w, schedule_field) for w in todays_wos if getattr(w, schedule_field)), default=False)
                if next_dt and (not bucket["next_planned_datetime"] or next_dt < bucket["next_planned_datetime"]):
                    bucket["next_planned_datetime"] = next_dt

            order_name = line.root_production_id.name or line.planning_order_id.display_name or "-"
            planned = 0.0
            produced = 0.0
            for wo in todays_wos:
                if qty_field:
                    planned += float(getattr(wo, qty_field) or 0.0)
                else:
                    planned += float(getattr(wo.production_id, "product_qty", 0.0) or 0.0)
                produced += float(getattr(wo, "qty_produced", 0.0) or 0.0)
            bucket["planned_qty"] += planned
            bucket["produced_qty"] += produced
            bucket["orders"].append("%s | %.2f / %.2f" % (order_name, produced, planned))

        vals_list = []
        for agg in by_wc.values():
            planned_qty = float(agg["planned_qty"] or 0.0)
            produced_qty = float(agg["produced_qty"] or 0.0)
            pct = (produced_qty / planned_qty * 100.0) if planned_qty > 0 else 0.0
            if pct >= 90.0:
                state = "success"
            elif pct >= 60.0:
                state = "warning"
            else:
                state = "danger"
            if agg["done_wo_count"] and not agg["pending_wo_count"]:
                status = "done"
            elif agg["pending_wo_count"] and agg["done_wo_count"]:
                status = "progress"
            elif agg["pending_wo_count"]:
                status = "pending"
            else:
                status = "cancelled"
            vals_list.append(
                {
                    "report_datetime": now_dt,
                    "report_date": today_date,
                    "workcenter_id": agg["workcenter_id"],
                    "status": status,
                    "pending_wo_count": int(agg["pending_wo_count"] or 0),
                    "done_wo_count": int(agg["done_wo_count"] or 0),
                    "total_wo_count": int(agg["total_wo_count"] or 0),
                    "next_planned_datetime": agg["next_planned_datetime"],
                    "planning_order_count": len(agg["planning_order_ids"]),
                    "planned_qty": planned_qty,
                    "produced_qty": produced_qty,
                    "completion_pct": pct,
                    "progress_state": state,
                    "order_lines_text": "\n".join(agg["orders"][:20]),
                }
            )
        if vals_list:
            self.create(vals_list)
        return True
