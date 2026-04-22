# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpPlanningWorkcenterLine(models.Model):
    _name = "mrp.planning.wc.line"
    _description = "Manufacturing Planning by Workcenter"
    _order = "workcenter_id asc, sequence asc, id asc"

    @api.model
    def search(self, args=None, offset=0, limit=None, order=None):
        """Ensure MRP → planning rows are synced before listing workcenter lines (standalone menu)."""
        if not self.env.context.get("planning_drag_skip_wc_search_sync"):
            self.env["mrp.planning.order"].sudo().with_context(
                planning_generic_synced=True,
                planning_drag_skip_wc_search_sync=True,
            )._sync_from_mrp()
        return super(MrpPlanningWorkcenterLine, self).search(
            args or [], offset=offset, limit=limit, order=order
        )

    active = fields.Boolean(default=True, index=True)
    sequence = fields.Integer(default=10, index=True)
    planning_order_id = fields.Many2one("mrp.planning.order", required=True, ondelete="cascade", index=True)
    planning_is_rush = fields.Boolean(
        string="Rush",
        related="planning_order_id.planning_is_rush",
        store=True,
        readonly=True,
        index=True,
    )
    planning_rush_icon = fields.Char(string="Rush", compute="_compute_planning_rush_icon", store=False)

    @api.depends("planning_is_rush")
    def _compute_planning_rush_icon(self):
        for rec in self:
            rec.planning_rush_icon = "⚡" if rec.planning_is_rush else ""
    root_production_id = fields.Many2one(
        "mrp.production",
        related="planning_order_id.root_production_id",
        store=True,
        index=True,
        readonly=True,
    )
    root_product_id = fields.Many2one(
        "product.product",
        related="planning_order_id.product_id",
        string="Root MO product",
        readonly=True,
        help="Finished product on the root manufacturing order (planning row).",
    )
    planning_product_id = fields.Many2one(
        "product.product",
        string="Product (MO at step)",
        compute="_compute_metrics",
        store=False,
        help="Product of the MO that owns the next pending work order at this workcenter "
        "(often a child/semi-finished MO in multi-level manufacturing).",
    )
    pending_step_name = fields.Char(
        string="Operation (WO)",
        compute="_compute_metrics",
        store=False,
        help="Name of the next open work order at this workcenter (usually matches the routing step).",
    )
    step_production_id = fields.Many2one(
        "mrp.production",
        string="Manufacturing order (step)",
        compute="_compute_metrics",
        store=False,
        help="MO that owns the next pending work order at this workcenter (e.g. WH/MO/00017 in a 00014→…→00017 chain).",
    )
    workcenter_id = fields.Many2one("mrp.workcenter", required=True, index=True)

    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_metrics",
        store=False,
        search="_search_status",
    )
    status_icon = fields.Char(compute="_compute_metrics", store=False)
    pending_wo_count = fields.Integer(compute="_compute_metrics", store=False)
    done_wo_count = fields.Integer(compute="_compute_metrics", store=False)
    total_wo_count = fields.Integer(compute="_compute_metrics", store=False)
    next_planned_datetime = fields.Datetime(compute="_compute_metrics", store=False)

    _sql_constraints = [
        (
            "planning_wc_unique",
            "unique(planning_order_id, workcenter_id)",
            "One workcenter line per planning order is allowed.",
        ),
    ]

    @api.depends("planning_order_id", "workcenter_id", "sequence")
    def _compute_metrics(self):
        wo_model = self.env["mrp.workorder"].sudo()
        for rec in self:
            rec.status = "pending"
            rec.status_icon = "•"
            rec.pending_wo_count = 0
            rec.done_wo_count = 0
            rec.total_wo_count = 0
            rec.next_planned_datetime = False
            rec.pending_step_name = ""
            rec.planning_product_id = (
                rec.planning_order_id.product_id if rec.planning_order_id else False
            )
            rec.step_production_id = (
                rec.planning_order_id.root_production_id if rec.planning_order_id else False
            )

            if not rec.planning_order_id or not rec.workcenter_id:
                continue

            mos = rec.planning_order_id._related_mos()
            if not mos:
                continue

            wos = wo_model.search(
                [("production_id", "in", mos.ids), ("workcenter_id", "=", rec.workcenter_id.id)],
                order=rec.planning_order_id._wo_order_expr(),
            )
            rec.total_wo_count = len(wos)
            if not wos:
                rec.status = "done"
                rec.status_icon = "✓"
                continue

            Order = self.env["mrp.planning.order"].sudo()
            pending = wos.filtered(lambda w: Order._planning_wo_is_open(w.state))
            done = wos.filtered(lambda w: Order._planning_wo_is_done(w.state))
            cancelled = wos.filtered(lambda w: Order._planning_wo_is_cancelled(w.state))
            rec.pending_wo_count = len(pending)
            rec.done_wo_count = len(done)

            if pending and done:
                rec.status = "progress"
                rec.status_icon = "◐"
            elif pending:
                rec.status = "pending"
                rec.status_icon = "•"
            elif cancelled:
                rec.status = "cancelled"
                rec.status_icon = "×"
            elif done:
                rec.status = "done"
                rec.status_icon = "✓"
            else:
                rec.status = "pending"
                rec.status_icon = "•"

            next_wo = pending[:1]
            if next_wo:
                wo0 = next_wo[0]
                rec.pending_step_name = wo0.name or ""
                rec.step_production_id = wo0.production_id
                if wo0.production_id.product_id:
                    rec.planning_product_id = wo0.production_id.product_id
                schedule_field = rec.planning_order_id._wo_schedule_field()
                rec.next_planned_datetime = schedule_field and next_wo[schedule_field] or False

    @api.model
    def _sync_from_planning_orders(self, planning_orders):
        planning_orders = planning_orders.sudo()
        wo_model = self.env["mrp.workorder"].sudo()
        for order in planning_orders:
            mos = order._related_mos()
            if not mos:
                continue
            # Only workcenters that still have *pending* work: avoids ghost rows when all WOs are done.
            open_excl = list(self.env["mrp.planning.order"]._planning_wo_open_states_exclude())
            wc_records = wo_model.search(
                [
                    ("production_id", "in", mos.ids),
                    ("workcenter_id", "!=", False),
                    ("state", "not in", open_excl),
                ]
            ).mapped("workcenter_id")
            wc_records = wc_records.sorted(key=lambda w: (getattr(w, "sequence", 0), w.name or "", w.id))
            wc_ids = wc_records.ids
            existing = self.search([("planning_order_id", "=", order.id)])
            existing_map = {line.workcenter_id.id: line for line in existing}

            # Keep per-workcenter queue aligned with global planning order.
            # When planning sequence changes, Apply schedule now calls sync and this updates queue order.
            seq = int(order.sequence or 0) or 10
            for wc_id in wc_ids:
                line = existing_map.get(wc_id)
                if not line:
                    self.create(
                        {
                            "planning_order_id": order.id,
                            "workcenter_id": wc_id,
                            "sequence": seq,
                        }
                    )
                elif line.sequence != seq:
                    line.write({"sequence": seq})

            to_remove = existing.filtered(lambda l: l.workcenter_id.id not in wc_ids)
            if to_remove:
                to_remove.unlink()

        # Drop any stale line where this WC no longer has pending work (e.g. WO finished since last sync).
        line_model = self.env["mrp.planning.wc.line"].sudo()
        open_excl_lines = list(self.env["mrp.planning.order"]._planning_wo_open_states_exclude())
        for order in planning_orders:
            for line in line_model.search([("planning_order_id", "=", order.id)]):
                mos = order._related_mos()
                pending = wo_model.search_count(
                    [
                        ("production_id", "in", mos.ids),
                        ("workcenter_id", "=", line.workcenter_id.id),
                        ("state", "not in", open_excl_lines),
                    ]
                )
                if not pending:
                    line.unlink()

    @api.model
    def _search_status(self, operator, value):
        """Search helper for non-stored `status` field used in search filters."""
        if operator not in ("=", "==", "!=", "<>") or value not in (
            "pending",
            "progress",
            "done",
            "cancelled",
        ):
            return [("id", "=", 0)]

        rows = self.with_context(planning_drag_skip_wc_search_sync=True).search([])
        matching_ids = rows.filtered(lambda r: r.status == value).ids

        if operator in ("=", "=="):
            return [("id", "in", matching_ids or [0])]
        return [("id", "not in", matching_ids or [0])]

    def action_apply_workcenter_schedule(self):
        """Apply micro sequence for each selected workcenter queue."""
        if not self:
            return True

        now_dt = fields.Datetime.now()
        by_wc = {}
        for line in self:
            by_wc.setdefault(line.workcenter_id.id, self.browse())
            by_wc[line.workcenter_id.id] |= line

        seq_counter = self.env["mrp.planning.order"]._next_planning_drag_seq_after_max()

        for _wc_id, lines in by_wc.items():
            cursor_dt = now_dt
            ordered_lines = lines.sorted(
                key=lambda l: (
                    not bool(l.planning_order_id.planning_is_rush),
                    l.sequence,
                    l.planning_order_id.sequence,
                    l.id,
                )
            )
            for line in ordered_lines:
                mos = line.planning_order_id._related_mos()
                if not mos:
                    continue
                pending_wos = self.env["mrp.workorder"].sudo().search(
                    [
                        ("production_id", "in", mos.ids),
                        ("workcenter_id", "=", line.workcenter_id.id),
                        ("state", "not in", list(self.env["mrp.planning.order"]._planning_wo_open_states_exclude())),
                    ],
                    order=line.planning_order_id._wo_order_expr(),
                )
                if not pending_wos:
                    continue
                schedule_field = line.planning_order_id._wo_schedule_field()
                if not schedule_field:
                    continue
                # Apply to all pending WOs in this project/workcenter block.
                for wo in pending_wos:
                    plan = self.env["mrp.planning.order"]
                    wo_start = plan._planning_align_start_with_calendar(wo, cursor_dt)
                    wo_end = plan._planning_next_end_dt(wo, wo_start)
                    wvals = plan._wo_schedule_write_vals(wo, wo_start, schedule_field)
                    if schedule_field == "date_start":
                        wvals["date_finished"] = wo_end
                    wvals["planning_drag_seq"] = seq_counter
                    wo.write(wvals)
                    seq_counter += 10
                    cursor_dt = wo_end
        return True
