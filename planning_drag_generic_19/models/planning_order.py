# -*- coding: utf-8 -*-
from datetime import timedelta
from xml.etree import ElementTree as ET

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _planning_xml_local_tag(elem):
    if not isinstance(elem.tag, str):
        return ""
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


def _planning_xml_attrib_get(elem, local_name):
    """Read attribute by local name (Odoo arch often uses namespaced attribute keys)."""
    for key, val in elem.attrib.items():
        loc = key.split("}")[-1] if "}" in key else key
        if loc == local_name:
            return val
    return None


def _planning_xml_attrib_set(elem, local_name, value):
    """Write attribute by local name, preserving an existing namespace prefix if any."""
    for key in list(elem.attrib):
        loc = key.split("}")[-1] if "}" in key else key
        if loc == local_name:
            elem.attrib[key] = value
            return
    elem.set(local_name, value)


# Global workcenter columns on planning lists (Manufacturing > Work Centers order, by sequence).
PLANNING_WC_SLOT_COUNT = 16


class MrpPlanningOrder(models.Model):
    _name = "mrp.planning.order"
    _description = "Manufacturing Planning Order (Generic)"
    # Rush is reflected by lowering ``sequence`` when Rush is toggled on, so list drag/resequence works.
    _order = "sequence asc, id asc"
    _rec_name = "display_name"

    active = fields.Boolean(default=True, index=True)
    sequence = fields.Integer(default=10, index=True)
    planning_is_rush = fields.Boolean(
        string="Rush",
        default=False,
        index=True,
        copy=False,
        help="Only one open planning row should be Rush: it is scheduled first and marked in lists.",
    )
    planning_rush_icon = fields.Char(
        string="Rush",
        compute="_compute_planning_rush_icon",
        store=False,
    )
    planning_manual_completed = fields.Boolean(
        string="Transferred to Completed",
        default=False,
        index=True,
        help="When set, this planning row appears only under the Completed menu. "
        "Set manually after manufacturing is 100% finished.",
    )
    planning_wc_slots_used = fields.Integer(
        string="Work center columns used",
        compute="_compute_planning_wc_slots_used",
        store=False,
        help="How many global work center columns are shown (same for every row; used by the list UI).",
    )
    root_production_id = fields.Many2one(
        "mrp.production",
        required=True,
        index=True,
        ondelete="cascade",
        string="Manufacturing Order",
    )
    production_date = fields.Datetime(string="Planning Date", index=True)

    display_name = fields.Char(compute="_compute_display_name", store=False)
    product_id = fields.Many2one("product.product", compute="_compute_info", store=False)
    planned_qty = fields.Float(string="Planned Qty", compute="_compute_info", store=False)
    pending_wo_count = fields.Integer(string="Pending WOs", compute="_compute_info", store=False)
    is_closed = fields.Boolean(string="Closed", compute="_compute_info", store=False, search="_search_is_closed")
    current_workcenter_id = fields.Many2one(
        "mrp.workcenter",
        compute="_compute_info",
        store=False,
        string="Current Workcenter",
    )
    workcenter_count = fields.Integer(string="Workcenters", compute="_compute_info", store=False)
    workcenter_summary = fields.Char(string="Detected Workcenters", compute="_compute_info", store=False)
    workcenter_status_summary = fields.Char(string="WC Status", compute="_compute_info", store=False)
    wc_col_1 = fields.Html(string="WC 1", compute="_compute_info", store=False, sanitize=False)
    wc_col_2 = fields.Html(string="WC 2", compute="_compute_info", store=False, sanitize=False)
    wc_col_3 = fields.Html(string="WC 3", compute="_compute_info", store=False, sanitize=False)
    wc_col_4 = fields.Html(string="WC 4", compute="_compute_info", store=False, sanitize=False)
    wc_col_5 = fields.Html(string="WC 5", compute="_compute_info", store=False, sanitize=False)
    wc_col_6 = fields.Html(string="WC 6", compute="_compute_info", store=False, sanitize=False)
    wc_col_7 = fields.Html(string="WC 7", compute="_compute_info", store=False, sanitize=False)
    wc_col_8 = fields.Html(string="WC 8", compute="_compute_info", store=False, sanitize=False)
    wc_col_9 = fields.Html(string="WC 9", compute="_compute_info", store=False, sanitize=False)
    wc_col_10 = fields.Html(string="WC 10", compute="_compute_info", store=False, sanitize=False)
    wc_col_11 = fields.Html(string="WC 11", compute="_compute_info", store=False, sanitize=False)
    wc_col_12 = fields.Html(string="WC 12", compute="_compute_info", store=False, sanitize=False)
    wc_col_13 = fields.Html(string="WC 13", compute="_compute_info", store=False, sanitize=False)
    wc_col_14 = fields.Html(string="WC 14", compute="_compute_info", store=False, sanitize=False)
    wc_col_15 = fields.Html(string="WC 15", compute="_compute_info", store=False, sanitize=False)
    wc_col_16 = fields.Html(string="WC 16", compute="_compute_info", store=False, sanitize=False)
    workcenter_line_ids = fields.One2many("mrp.planning.wc.line", "planning_order_id", string="Workcenter Lines")
    planning_rank = fields.Integer(
        string="#",
        compute="_compute_planning_rank",
        store=False,
        help="Position in the current planning list (1…n by sequence within open or completed rows).",
    )

    _sql_constraints = [
        ("root_production_unique", "unique(root_production_id)", "Each root MO can only have one planning row."),
    ]

    @api.model
    def _planning_wo_open_states_exclude(self):
        """WO states that are not open (done + all cancel spellings used in domains)."""
        return ("done", "cancel", "cancelled", "canceled")

    @api.model
    def _planning_wo_is_cancelled(self, state):
        if state in (False, None):
            return False
        return str(state).lower() in frozenset({"cancel", "cancelled", "canceled"})

    @api.model
    def _planning_wo_is_done(self, state):
        return state == "done"

    @api.model
    def _planning_wo_is_open(self, state):
        return not self._planning_wo_is_done(state) and not self._planning_wo_is_cancelled(state)

    @api.model
    def _planning_info_compute_field_names(self):
        return (
            [
                "product_id",
                "planned_qty",
                "pending_wo_count",
                "is_closed",
                "current_workcenter_id",
                "workcenter_count",
                "workcenter_summary",
                "workcenter_status_summary",
            ]
            + ["wc_col_%s" % i for i in range(1, PLANNING_WC_SLOT_COUNT + 1)]
            + ["planning_rank", "planning_rush_icon"]
        )

    @api.model
    def _planning_wcline_compute_field_names(self):
        return [
            "planning_product_id",
            "pending_step_name",
            "step_production_id",
            "status",
            "status_icon",
            "pending_wo_count",
            "done_wo_count",
            "total_wo_count",
            "next_planned_datetime",
            "planning_rush_icon",
        ]

    @api.model
    def _invalidate_planning_display_cache(self):
        """Recompute planning list cells when MRP work orders / MOs change (incl. child MOs)."""
        Planning = self.env["mrp.planning.order"].sudo().with_context(active_test=False)
        Planning.search([]).invalidate_recordset(self._planning_info_compute_field_names())
        WLine = self.env["mrp.planning.wc.line"].sudo().with_context(active_test=False)
        WLine.search([]).invalidate_recordset(self._planning_wcline_compute_field_names())

    def _wc_marker_html(self, marker):
        """Colored pill HTML for one configured workcenter column (list view, sanitize=False)."""
        cls = "o_planning_drag_wc_sig"
        if marker == "-":
            return Markup(
                '<span class="%s o_planning_drag_wc_na" title="%s">—</span>'
                % (cls, escape(_("NA")))
            )
        if marker == "•":
            return Markup(
                '<span class="%s o_planning_drag_wc_pending" title="%s">●</span>'
                % (cls, escape(_("Pending")))
            )
        if marker == "◐":
            return Markup(
                '<span class="%s o_planning_drag_wc_progress" title="%s">◐</span>'
                % (cls, escape(_("On going")))
            )
        if marker == "✓":
            return Markup(
                '<span class="%s o_planning_drag_wc_done" title="%s">✓</span>'
                % (cls, escape(_("Completed")))
            )
        if marker == "cancel":
            return Markup(
                '<span class="%s o_planning_drag_wc_cancelled" title="%s">×</span>'
                % (cls, escape(_("Cancelled")))
            )
        return Markup(
            '<span class="%s o_planning_drag_wc_na" title="">%s</span>' % (cls, escape(marker or "-"))
        )

    @api.depends(
        "root_production_id",
        "root_production_id.name",
        "root_production_id.product_id",
        "planning_is_rush",
    )
    def _compute_display_name(self):
        """Short label for Many2one widgets; product is shown in its own column on list views."""
        for rec in self:
            if not rec.root_production_id:
                rec.display_name = "Planning"
                continue
            base = rec.root_production_id.name or "MO"
            rec.display_name = ("⚡ " + base) if rec.planning_is_rush else base

    @api.depends("planning_is_rush")
    def _compute_planning_rush_icon(self):
        for rec in self:
            rec.planning_rush_icon = "⚡" if rec.planning_is_rush else ""

    @api.depends(
        "sequence",
        "active",
        "is_closed",
        "planning_manual_completed",
        "root_production_id.write_date",
        "planning_is_rush",
    )
    @api.depends_context("planning_rank_closed")
    def _compute_planning_rank(self):
        """1…n within the same scope as the menu (open vs completed), by sequence then id."""
        Planning = self.env["mrp.planning.order"].sudo()
        want_closed = bool(self.env.context.get("planning_rank_closed"))
        # Avoid domain on is_closed here: it would call _search_is_closed → _sync_from_mrp (re-entry / loops).
        candidates = Planning.with_context(planning_generic_synced=True).search(
            [("active", "=", True)], order="sequence asc, id asc"
        )
        if want_closed:
            ordered = candidates.filtered(
                lambda r: r.planning_manual_completed and r._planning_mrp_fully_closed()
            )
        else:
            ordered = candidates.filtered(lambda r: not r.planning_manual_completed)
        rank_by_id = {row.id: pos for pos, row in enumerate(ordered, start=1)}
        for rec in self:
            rec.planning_rank = rank_by_id.get(rec.id, 0)

    def _invalidate_planning_rank_cache(self):
        self.env["mrp.planning.order"].sudo().with_context(
            planning_generic_synced=True, active_test=False
        ).search([]).invalidate_recordset(["planning_rank"])

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        rush_new = records.filtered(
            lambda r: r.planning_is_rush and r.active and not r.planning_manual_completed
        )
        if len(rush_new) > 1:
            rush_new[1:].write({"planning_is_rush": False})
            rush_new = rush_new[:1]
        if rush_new:
            others = self.env["mrp.planning.order"].sudo().search(
                [
                    ("active", "=", True),
                    ("planning_manual_completed", "=", False),
                    ("planning_is_rush", "=", True),
                    ("id", "not in", rush_new.ids),
                ]
            )
            if others:
                others.write({"planning_is_rush": False})
            head = rush_new[:1]
            open_others = self.env["mrp.planning.order"].sudo().search(
                [
                    ("active", "=", True),
                    ("planning_manual_completed", "=", False),
                    ("id", "!=", head.id),
                ]
            )
            if open_others:
                new_seq = min(open_others.mapped("sequence")) - 10
            else:
                new_seq = 0
            super(MrpPlanningOrder, head).write({"sequence": new_seq})
        records._invalidate_planning_rank_cache()
        return records

    def write(self, vals):
        rush_cleared_order_ids = []
        vals = dict(vals)
        if vals.get("planning_is_rush"):
            if len(self) > 1:
                raise UserError(_("Only one row can be Rush at a time. Select a single planning line."))
            others = (
                self.env["mrp.planning.order"]
                .sudo()
                .search(
                    [
                        ("active", "=", True),
                        ("planning_manual_completed", "=", False),
                        ("planning_is_rush", "=", True),
                        ("id", "not in", self.ids),
                    ]
                )
            )
            if others:
                rush_cleared_order_ids = others.ids
                others.write({"planning_is_rush": False})
            if vals.get("planning_is_rush") is True:
                rec = self[:1]
                open_others = self.env["mrp.planning.order"].sudo().search(
                    [
                        ("active", "=", True),
                        ("planning_manual_completed", "=", False),
                        ("id", "not in", rec.ids),
                    ]
                )
                if open_others:
                    vals["sequence"] = min(open_others.mapped("sequence")) - 10
                else:
                    vals["sequence"] = 0
        res = super().write(vals)
        if any(
            k in vals
            for k in (
                "sequence",
                "active",
                "production_date",
                "planning_manual_completed",
                "planning_is_rush",
            )
        ):
            self._invalidate_planning_rank_cache()
        if "planning_is_rush" in vals:
            po_ids = list(set(self.ids) | set(rush_cleared_order_ids))
            wlines = self.env["mrp.planning.wc.line"].sudo().search([("planning_order_id", "in", po_ids)])
            if wlines:
                wlines.invalidate_recordset(["planning_rush_icon", "planning_is_rush"])
        if any(k in vals for k in ("sequence", "planning_is_rush")):
            self.env["mrp.planning.wc.line"].sudo().with_context(
                planning_drag_skip_wc_search_sync=True
            )._sync_from_planning_orders(self)
        return res

    def unlink(self):
        res = super().unlink()
        self._invalidate_planning_rank_cache()
        return res

    def _related_mos(self):
        """Return root MO + children whose origin is this MO name (not a substring ilike)."""
        self.ensure_one()
        root = self.root_production_id
        if not root:
            return self.env["mrp.production"]

        mo_model = self.env["mrp.production"].sudo()
        all_mos = root
        frontier_names = {root.name} if root.name else set()
        depth = 0

        while frontier_names and depth < 8:
            depth += 1
            children = mo_model.search([("origin", "in", list(frontier_names))])
            children -= all_mos
            if not children:
                break
            all_mos |= children
            frontier_names = {name for name in children.mapped("name") if name}

        return all_mos

    def _planning_mrp_fully_closed(self, pending_wos=None):
        """True when this planning tree has no open work orders left.

        Shop floor often finishes every WO while the MO stays in progress/to_close
        until someone clicks Mark as Done. Planning treats that as complete.
        """
        self.ensure_one()
        root = self.root_production_id
        if not root:
            return False
        if root.state == "cancel":
            return True
        mos = self._related_mos()
        if not mos:
            return False
        wo_model = self.env["mrp.workorder"].sudo()
        if pending_wos is None:
            has_pending = bool(
                wo_model.search(
                    [
                        ("production_id", "in", mos.ids),
                        ("state", "not in", self._planning_wo_open_states_exclude()),
                    ],
                    limit=1,
                )
            )
        else:
            has_pending = bool(pending_wos)
        return not has_pending

    @api.model
    def _wo_order_expr(self):
        """Pick a valid datetime field to order workorders."""
        wo_fields = self.env["mrp.workorder"]._fields
        # Prefer stored / inverse scheduling fields (Odoo 19 MRP uses date_start + leave).
        if "date_start" in wo_fields:
            return "date_start asc, sequence asc, id asc"
        if "date_planned_start" in wo_fields:
            return "date_planned_start asc, id asc"
        if "production_date" in wo_fields:
            return "production_date asc, id asc"
        return "id asc"

    @api.model
    def _sort_workcenters_like_overview(self, workcenters):
        """Sort workcenters like Manufacturing workcenter lists (sequence, id, name)."""
        if not workcenters:
            return workcenters
        if "sequence" in workcenters._fields:
            return workcenters.sorted(key=lambda w: (w.sequence, w.id, w.name or ""))
        return workcenters.sorted(key=lambda w: (0, w.id, w.name or ""))

    @api.model
    def _configured_workcenters_ordered(self):
        """Active work centers for the current company, same order as Manufacturing > Work Centers."""
        company = self.env.company
        Wc = self.env["mrp.workcenter"].sudo()
        domain = [("active", "=", True)]
        if company:
            domain = [
                ("active", "=", True),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company.id),
            ]
        for order in ("sequence asc, id asc, name asc", "sequence, id, name", "sequence, id"):
            try:
                return Wc.search(domain, order=order)
            except Exception:
                continue
        return self._sort_workcenters_like_overview(Wc.search(domain))

    @api.model
    def _configured_workcenter_labels(self):
        """One label per real WC slot; unused slots get a blank title (columns are hidden in the list)."""
        wcs = self._configured_workcenters_ordered()[:PLANNING_WC_SLOT_COUNT]
        labels = [wc.name or ("Workcenter %s" % idx) for idx, wc in enumerate(wcs, start=1)]
        while len(labels) < PLANNING_WC_SLOT_COUNT:
            labels.append(" ")
        return labels

    @api.depends(
        "root_production_id",
        "root_production_id.write_date",
        "sequence",
        "planning_manual_completed",
    )
    def _compute_planning_wc_slots_used(self):
        n = min(PLANNING_WC_SLOT_COUNT, len(self._configured_workcenters_ordered()))
        for rec in self:
            rec.planning_wc_slots_used = n

    @api.model
    def _patch_wc_column_headers_in_arch(self, arch, labels=None):
        """Return patched arch XML or None if unchanged / invalid.

        Uses namespace-agnostic iteration (default-namespace XML breaks findall('.//field')).
        """
        if not arch or "wc_col_1" not in arch:
            return None
        if labels is None:
            labels = self._configured_workcenter_labels()
        try:
            root = ET.fromstring(arch)
        except Exception:
            return None
        changed = False
        for idx in range(1, PLANNING_WC_SLOT_COUNT + 1):
            fname = "wc_col_%s" % idx
            label = labels[idx - 1]
            for elem in root.iter():
                if _planning_xml_local_tag(elem) != "field":
                    continue
                if _planning_xml_attrib_get(elem, "name") != fname:
                    continue
                if _planning_xml_attrib_get(elem, "string") != label:
                    _planning_xml_attrib_set(elem, "string", label)
                    changed = True
        if not changed:
            return None
        return ET.tostring(root, encoding="unicode")

    @api.model
    def _planning_list_view_arch_source(self, view):
        """Resolve planning list XML arch (DB, combined helper, or computed arch)."""
        arch_db = (view.arch_db or "").strip()
        arch_src = arch_db
        if not arch_src:
            for attr in ("_get_combined_arch", "_get_combined_architecture"):
                getter = getattr(view, attr, None)
                if callable(getter):
                    try:
                        arch_src = (getter() or "").strip()
                    except Exception:
                        arch_src = ""
                    if arch_src:
                        break
        if not arch_src:
            arch_src = (view.arch or "").strip()
        return arch_src or ""

    @api.model
    def _update_wc_column_labels(self):
        """Persist list column titles on the planning list view (Overview workcenter order).

        Also sets ``arch_updated`` so Odoo does not keep serving the module file arch in
        ``--dev=xml`` mode (which ignored our ``arch_db`` writes before).

        When ``arch_db`` is still empty (view never customized), read the combined ``arch``
        (file + inheritance) so the first refresh actually writes real WC names into the DB.
        """
        view = self.env.ref("planning_drag_generic_19.view_mrp_planning_order_list", raise_if_not_found=False)
        if not view:
            return
        arch_src = self._planning_list_view_arch_source(view)
        backup = arch_src
        required = "wc_col_%s" % PLANNING_WC_SLOT_COUNT
        if required not in arch_src and backup.strip():
            # Older DB had flattened arch with fewer WC columns; clear once so module XML is merged again.
            view.sudo().write({"arch_db": False})
            view.invalidate_recordset(["arch_db", "arch_fs"])
            try:
                self.env.flush_all()
            except AttributeError:
                pass
            view = view.browse(view.id)
            arch_src = self._planning_list_view_arch_source(view)
        if not (arch_src or "").strip() and (backup or "").strip():
            view.sudo().write({"arch_db": backup, "arch_updated": True})
            view.invalidate_recordset(["arch_db", "arch_fs"])
            arch_src = backup
        if not (arch_src or "").strip():
            return
        patched = self._patch_wc_column_headers_in_arch(arch_src)
        new_arch = patched if patched is not None else arch_src
        if (view.arch_db or "").strip() != new_arch.strip():
            view.sudo().write({"arch_db": new_arch, "arch_updated": True})
            view.invalidate_recordset(["arch_db", "arch_fs"])

    @api.model
    def _planning_refresh_after_workcenter_change(self):
        """When work centers are created/updated/deleted, refresh list headers and WC slot computes."""
        self._update_wc_column_labels()
        self._invalidate_planning_display_cache()

    @api.model
    def get_views(self, views, options=None):
        """Inject real workcenter names as list column headers (same order as Configuration > Work Centers)."""
        res = super().get_views(views, options=options or {})
        labels = self._configured_workcenter_labels()
        views_payload = res.get("views") or {}
        if isinstance(views_payload, dict):
            iterable = list(views_payload.values())
        else:
            iterable = list(views_payload) if isinstance(views_payload, (list, tuple)) else []
        for vspec in iterable:
            if isinstance(vspec, (list, tuple)) and len(vspec) >= 2 and isinstance(vspec[1], dict):
                vspec = vspec[1]
            if not isinstance(vspec, dict):
                continue
            arch = vspec.get("arch")
            if not isinstance(arch, str) or "wc_col_1" not in arch:
                continue
            new_arch = self._patch_wc_column_headers_in_arch(arch, labels=labels)
            if new_arch:
                vspec["arch"] = new_arch
        return res

    @api.model
    def _wo_schedule_field(self):
        """Pick a valid datetime field to write schedule on workorders."""
        wo_fields = self.env["mrp.workorder"]._fields
        # Never prefer production_date here: it is computed from date_start in standard MRP.
        if "date_start" in wo_fields:
            return "date_start"
        if "date_planned_start" in wo_fields:
            return "date_planned_start"
        if "production_date" in wo_fields:
            return "production_date"
        return False

    @api.model
    def _wo_schedule_write_vals(self, wo, cursor_dt, schedule_field):
        """Vals for WO write so planned start/end stay valid (MRP forbids start after old end).

        Writing only ``date_start`` keeps the previous ``date_finished``; if the new start is
        later than that end (common after reordering planning), Odoo raises UserError.
        """
        if not schedule_field:
            return {}
        vals = {schedule_field: fields.Datetime.to_datetime(cursor_dt)}
        if schedule_field == "date_start":
            date_start = vals["date_start"]
            date_finished = wo._calculate_date_finished(date_start=date_start)
            if not date_finished or date_finished <= date_start:
                date_finished = date_start + timedelta(
                    minutes=max(int(wo.duration_expected or 0), 5)
                )
            vals["date_finished"] = date_finished
        return vals

    @api.model
    def _next_planning_drag_seq_after_max(self):
        """Start micro-scheduling ranks after the current global maximum."""
        wo = (
            self.env["mrp.workorder"]
            .sudo()
            .search(
                [
                    ("state", "not in", list(self._planning_wo_open_states_exclude())),
                    ("production_id.state", "not in", ["done", "cancel"]),
                ],
                order="planning_drag_seq desc",
                limit=1,
            )
        )
        base = int(wo.planning_drag_seq or 0) if wo else 0
        return max(10, base + 10)

    @api.depends(
        "root_production_id",
        "root_production_id.write_date",
        "root_production_id.state",
        "root_production_id.workorder_ids.state",
        "root_production_id.workorder_ids.workcenter_id",
        "sequence",
        "production_date",
        "planning_manual_completed",
    )
    def _compute_info(self):
        wo_model = self.env["mrp.workorder"].sudo()
        configured_wcs = self._configured_workcenters_ordered()
        wc_slots = (configured_wcs.ids + [False] * PLANNING_WC_SLOT_COUNT)[:PLANNING_WC_SLOT_COUNT]
        na_cell = self._wc_marker_html("-")
        for rec in self:
            rec.product_id = False
            rec.planned_qty = 0.0
            rec.pending_wo_count = 0
            rec.is_closed = True
            rec.current_workcenter_id = False
            rec.workcenter_count = 0
            rec.workcenter_summary = ""
            rec.workcenter_status_summary = ""
            for slot in range(1, PLANNING_WC_SLOT_COUNT + 1):
                setattr(rec, "wc_col_%s" % slot, na_cell)

            root = rec.root_production_id
            if not root:
                continue

            rec.product_id = root.product_id
            rec.planned_qty = float(getattr(root, "product_qty", 0.0) or 0.0)

            mos = rec._related_mos()
            if not mos:
                continue

            pending_wos = wo_model.search(
                [
                    ("production_id", "in", mos.ids),
                    ("state", "not in", list(self._planning_wo_open_states_exclude())),
                ],
                order=self._wo_order_expr(),
            )
            rec.pending_wo_count = len(pending_wos)

            if pending_wos:
                rec.current_workcenter_id = pending_wos[0].workcenter_id
            else:
                rec.current_workcenter_id = False
            rec.is_closed = rec._planning_mrp_fully_closed(pending_wos=pending_wos)

            all_wos = wo_model.search([("production_id", "in", mos.ids), ("workcenter_id", "!=", False)])
            workcenters = all_wos.mapped("workcenter_id")
            sorted_workcenters = self._sort_workcenters_like_overview(workcenters)
            rec.workcenter_count = len(sorted_workcenters)
            rec.workcenter_summary = ", ".join(sorted_workcenters.mapped("name")) if sorted_workcenters else ""

            status_parts = []
            status_by_wc_id = {}
            summary_char = {"✓": "✓", "•": "•", "◐": "◐", "cancel": "×", "-": "-"}
            PO = rec.env["mrp.planning.order"].sudo()
            for wc in sorted_workcenters:
                wc_wos = all_wos.filtered(lambda w: w.workcenter_id.id == wc.id)
                pending = wc_wos.filtered(lambda w: PO._planning_wo_is_open(w.state))
                done_wos = wc_wos.filtered(lambda w: PO._planning_wo_is_done(w.state))
                cancel_wos = wc_wos.filtered(lambda w: PO._planning_wo_is_cancelled(w.state))
                if pending:
                    # Only real "done" WOs count toward in-progress; cancelled is not partial completion.
                    marker = "◐" if done_wos else "•"
                elif cancel_wos:
                    # Any cancelled WO at this WC: do not show as completed (green).
                    marker = "cancel"
                elif done_wos:
                    marker = "✓"
                else:
                    marker = "-"
                status_by_wc_id[wc.id] = marker
                status_parts.append("%s %s" % (summary_char.get(marker, marker), wc.name))
            rec.workcenter_status_summary = " | ".join(status_parts)

            # Fixed columns by configured workcenter order (colored HTML pills).
            markers = []
            for wc_id in wc_slots:
                markers.append(status_by_wc_id.get(wc_id, "-") if wc_id else "-")
            html_slots = [self._wc_marker_html(m) for m in markers]
            for slot in range(1, PLANNING_WC_SLOT_COUNT + 1):
                setattr(
                    rec,
                    "wc_col_%s" % slot,
                    html_slots[slot - 1] if slot - 1 < len(html_slots) else na_cell,
                )

    @api.model
    def _search_is_closed(self, operator, value):
        self.with_context(planning_generic_synced=True)._sync_from_mrp()
        Planning = self.env["mrp.planning.order"].sudo()
        rows = Planning.with_context(planning_generic_synced=True).search([])
        # Never use cached ``is_closed`` here: OT/MO state can change without invalidating this row.
        closed_ids = [row.id for row in rows if row._planning_mrp_fully_closed()]
        if (operator in ("=", "==") and value) or (operator in ("!=", "<>") and not value):
            return [("id", "in", closed_ids or [0])]
        return [("id", "not in", closed_ids or [0])]

    @api.model
    def _root_mo_domain(self):
        return [("origin", "=", False)]

    @api.model
    def _sync_from_mrp(self):
        self._update_wc_column_labels()
        root_mos = self.env["mrp.production"].sudo().search(self._root_mo_domain(), order="date_start asc, id asc")
        existing_rows = super(MrpPlanningOrder, self.sudo().with_context(active_test=False)).search([])
        existing = {row.root_production_id.id: row for row in existing_rows}

        next_seq = 10
        for mo in root_mos:
            row = existing.get(mo.id)
            dt = mo.date_start or mo.create_date or fields.Datetime.now()
            if not row:
                self.create(
                    {
                        "sequence": next_seq,
                        "root_production_id": mo.id,
                        "production_date": dt,
                    }
                )
            else:
                values = {}
                if not row.production_date:
                    values["production_date"] = dt
                if values:
                    row.sudo().write(values)
            next_seq += 10
        planning_rows = super(MrpPlanningOrder, self.sudo().with_context(active_test=False)).search([])
        self.env["mrp.planning.wc.line"].sudo().with_context(
            planning_drag_skip_wc_search_sync=True
        )._sync_from_planning_orders(planning_rows)
        self.env["mrp.planning.order"].sudo().with_context(
            planning_generic_synced=True, active_test=False
        ).search([]).invalidate_recordset(["planning_rank"])

    @api.model
    def search(self, args=None, offset=0, limit=None, order=None):
        if not self.env.context.get("planning_generic_synced"):
            self.with_context(planning_generic_synced=True)._sync_from_mrp()
        return super().search(args or [], offset=offset, limit=limit, order=order)

    def action_refresh_from_mrp(self):
        self._sync_from_mrp()
        return True

    def action_move_to_planning_completed(self):
        """Manual move to the Completed menu (when no open work orders remain)."""
        if not self:
            raise UserError(_("Select at least one row to move to Completed."))
        todo = self.filtered(lambda r: r.active and not r.planning_manual_completed)
        if not todo:
            raise UserError(_("The selected row(s) are already in Completed."))
        for rec in todo:
            if not rec._planning_mrp_fully_closed():
                raise UserError(
                    _(
                        "There are still open work orders on %(mo)s. Finish them before moving "
                        "this row to Completed.",
                        mo=rec.root_production_id.display_name or rec.display_name,
                    )
                )
        todo.write({"planning_manual_completed": True, "planning_is_rush": False})
        xmlid = (
            "planning_drag_generic_19.action_mrp_planning_order_closed"
            if self.env.context.get("planning_rank_closed")
            else "planning_drag_generic_19.action_mrp_planning_order"
        )
        try:
            return self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        except ValueError:
            return True

    def action_set_planning_rush(self):
        """Mark this row as the single Rush priority (open planning only)."""
        self.ensure_one()
        if self.planning_manual_completed:
            raise UserError(_("You cannot set Rush on an order that is already in Completed."))
        if not self.active:
            raise UserError(_("Archive the row or activate it before using Rush."))
        self.write({"planning_is_rush": True})
        return True

    def action_clear_planning_rush(self):
        """Remove Rush flag from the selected row(s)."""
        self.write({"planning_is_rush": False})
        return True

    @api.model
    def _planning_report_table_exists(self):
        self.env.cr.execute("SELECT to_regclass('public.mrp_planning_report')")
        row = self.env.cr.fetchone()
        return bool(row and row[0])

    @api.model
    def _scheduling_mode(self):
        mode = self.env["ir.config_parameter"].sudo().get_param(
            "planning_drag_generic_19.scheduling_mode", default="manual"
        )
        return mode if mode in ("manual", "auto") else "manual"

    @api.model
    def _planning_reservation_sync_enabled(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("planning_drag_generic_19.sync_reservation_with_sequence", "True")
            == "True"
        )

    @api.model
    def _planning_reservation_sync_scope(self):
        v = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("planning_drag_generic_19.reservation_sync_scope", "mo_tree")
        )
        return v if v in ("mo_tree", "root_only") else "mo_tree"

    @api.model
    def _planning_reservation_delta_minutes(self):
        try:
            raw = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("planning_drag_generic_19.reservation_rank_delta_minutes", "5")
            )
            return max(1, int(raw))
        except (TypeError, ValueError):
            return 5

    @api.model
    def _planning_reservation_mo_priority_first_enabled(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("planning_drag_generic_19.reservation_mo_priority_first", "True")
            == "True"
        )

    @api.model
    def _planning_use_workcenter_calendar(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("planning_drag_generic_19.use_workcenter_calendar", "True")
            == "True"
        )

    @api.model
    def _planning_cron_replan_today_enabled(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("planning_drag_generic_19.cron_replan_today", "False")
            == "True"
        )

    @api.model
    def _planning_workcenter_calendar(self, wo):
        wc = wo.workcenter_id.sudo()
        if not wc:
            return False, False
        calendar = wc.resource_calendar_id or (wc.resource_id and wc.resource_id.calendar_id) or False
        resource = wc.resource_id if "resource_id" in wc._fields else False
        return calendar, resource

    @api.model
    def _planning_align_start_with_calendar(self, wo, start_dt):
        if not self._planning_use_workcenter_calendar():
            return start_dt
        calendar, resource = self._planning_workcenter_calendar(wo)
        if not calendar:
            return start_dt
        try:
            aligned = calendar.plan_hours(0.0, start_dt, compute_leaves=True, resource=resource)
            return aligned or start_dt
        except Exception:
            return start_dt

    @api.model
    def _planning_next_end_dt(self, wo, start_dt):
        minutes = max(int(wo.duration_expected or 0), 5)
        if not self._planning_use_workcenter_calendar():
            return start_dt + timedelta(minutes=minutes)
        calendar, resource = self._planning_workcenter_calendar(wo)
        if not calendar:
            return start_dt + timedelta(minutes=minutes)
        try:
            end_dt = calendar.plan_hours(
                float(minutes) / 60.0,
                start_dt,
                compute_leaves=True,
                resource=resource,
            )
            return end_dt or (start_dt + timedelta(minutes=minutes))
        except Exception:
            return start_dt + timedelta(minutes=minutes)

    def _productions_for_planning_reservation(self):
        self.ensure_one()
        if self.env["mrp.planning.order"]._planning_reservation_sync_scope() == "root_only":
            return self.root_production_id
        return self._related_mos()

    def _apply_reservation_priority_from_planning(self):
        """Unreserve, rank component move dates by planning order, optional MO priority, re-assign.

        Uses mo_tree or root_only from settings. Only touches MOs returned for each open row.
        """
        if not self.env["mrp.planning.order"]._planning_reservation_sync_enabled():
            return True

        rows = self.filtered(lambda r: r.active).sorted(
            lambda r: (not bool(r.planning_is_rush), r.sequence, r.id)
        )
        ranked = [r for r in rows if not r._planning_mrp_fully_closed()]
        if not ranked:
            return True

        mo_model = self.env["mrp.production"].sudo()
        all_mos = mo_model.browse()
        row_mos_list = []
        for row in ranked:
            mos = row._productions_for_planning_reservation().filtered(lambda m: m.id)
            if not mos:
                continue
            row_mos_list.append(mos)
            all_mos |= mos

        if not all_mos:
            return True

        # Release reservations first (deterministic order by MO id).
        for mo in all_mos.sorted(lambda m: m.id, reverse=True):
            mo.do_unreserve()

        # Reset MO standard priority for touched orders, then stamp move dates by rank.
        delta = timedelta(minutes=self._planning_reservation_delta_minutes())
        anchor = fields.Datetime.now()
        if "priority" in mo_model._fields:
            all_mos.write({"priority": "0"})

        for rank, mos in enumerate(row_mos_list):
            target_dt = anchor + delta * rank
            for mo in mos:
                raw_moves = mo.move_raw_ids.filtered(lambda m: m.state not in ("done", "cancel"))
                if raw_moves:
                    raw_moves.write({"date": target_dt})

        if "priority" in mo_model._fields and self._planning_reservation_mo_priority_first_enabled():
            first_mos = row_mos_list[0]
            if first_mos:
                first_mos.write({"priority": "1"})

        # Re-assign in planning order so earlier rows consume free stock first.
        for mos in row_mos_list:
            for mo in mos.sorted(lambda m: m.id):
                mo.action_assign()

        return True

    def action_apply_schedule_now(self):
        """Global schedule push by planning sequence across all pending workorders.

        Behavior:
        - Syncs planning rows and workcenter lines from MRP (same as the former Refresh button).
        - Respects planning row sequence.
        - For each row, reschedules *all* pending WOs in the related MO tree (when a schedule
          field exists on work orders).
        - Stamps ``planning_drag_seq`` on work orders so default lists match planning priority.
        - Optionally aligns component reservations with the same planning order (settings).
        """
        self._sync_from_mrp()
        rows = self.search([("active", "=", True)], order="sequence asc, id asc")
        rows = rows.sorted(lambda r: (not bool(r.planning_is_rush), r.sequence, r.id))
        if not rows:
            return True

        wo_model = self.env["mrp.workorder"].sudo()
        mo_model = self.env["mrp.production"].sudo()
        scheduling_mos = mo_model.browse()
        for r in rows:
            scheduling_mos |= r._related_mos()

        open_excl = list(self._planning_wo_open_states_exclude())
        pending_in_plan = wo_model.search(
            [
                ("production_id", "in", scheduling_mos.ids),
                ("state", "not in", open_excl),
            ]
        )
        if pending_in_plan:
            pending_in_plan.write({"planning_drag_seq": 0})

        force_today = bool(self.env.context.get("planning_force_today_anchor"))
        now_dt = fields.Datetime.now()
        cursor_dt = now_dt
        schedule_field = self._wo_schedule_field()
        seq_counter = 10

        if schedule_field:
            for row in rows:
                if row._planning_mrp_fully_closed():
                    continue
                mos = row._related_mos()
                if not mos:
                    continue

                pending_wos = wo_model.search(
                    [("production_id", "in", mos.ids), ("state", "not in", open_excl)],
                    order=self._wo_order_expr(),
                )
                if not pending_wos:
                    continue

                row_start_dt = False
                for wo in pending_wos:
                    wo_start = cursor_dt
                    if force_today and wo_start < now_dt:
                        wo_start = now_dt
                    wo_start = self._planning_align_start_with_calendar(wo, wo_start)
                    if not row_start_dt:
                        row_start_dt = wo_start
                    wo_end = self._planning_next_end_dt(wo, wo_start)
                    wvals = self._wo_schedule_write_vals(wo, wo_start, schedule_field)
                    if schedule_field == "date_start":
                        wvals["date_finished"] = wo_end
                    wvals["planning_drag_seq"] = seq_counter
                    wo.write(wvals)
                    seq_counter += 10
                    cursor_dt = wo_end
                row.sudo().write({"production_date": row_start_dt or cursor_dt})

        rows._apply_reservation_priority_from_planning()

        if self._planning_report_table_exists():
            self.env["mrp.planning.report"].sudo().refresh_from_live_data()
        return True

    @api.model
    def cron_auto_apply_schedule(self):
        """Automatic scheduling cron when mode is set to auto."""
        if self._scheduling_mode() != "auto":
            return True
        rows = self.search(
            [("active", "=", True), ("planning_manual_completed", "=", False)],
            order="sequence asc, id asc",
        )
        rows = rows.sorted(lambda r: (not bool(r.planning_is_rush), r.sequence, r.id))
        if rows:
            if self._planning_cron_replan_today_enabled():
                rows.with_context(planning_force_today_anchor=True).action_apply_schedule_now()
            else:
                rows.action_apply_schedule_now()
        elif self._planning_report_table_exists():
            self.env["mrp.planning.report"].sudo().refresh_from_live_data()
        return True
