/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

function planningLegendBarEl() {
    const wrap = document.createElement("div");
    wrap.className =
        "o_planning_drag_legend_bar border-top bg-view px-3 py-2 text-muted o_planning_drag_legend_compact";
    wrap.setAttribute("role", "note");

    const items = document.createElement("div");
    items.className = "d-flex flex-wrap gap-2 align-items-center o_planning_drag_legend_items";

    const rows = [
        ["o_planning_drag_wc_pending", "●", _t("Pending")],
        ["o_planning_drag_wc_progress", "◐", _t("On going")],
        ["o_planning_drag_wc_done", "✓", _t("Completed")],
        ["o_planning_drag_wc_cancelled", "×", _t("Cancelled")],
        ["o_planning_drag_wc_na", "—", _t("NA")],
    ];
    for (const [extraClass, symbol, label] of rows) {
        const row = document.createElement("span");
        row.className = "d-inline-flex align-items-center gap-1";
        const pill = document.createElement("span");
        pill.className = `o_planning_drag_wc_sig ${extraClass}`;
        pill.textContent = symbol;
        const lab = document.createElement("span");
        lab.className = "text-body o_planning_drag_legend_label";
        lab.textContent = label;
        row.appendChild(pill);
        row.appendChild(lab);
        items.appendChild(row);
    }

    wrap.appendChild(items);
    return wrap;
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        const list = this.props.list;
        if (!list || list.resModel !== "mrp.planning.order" || this.isX2Many) {
            return;
        }
        const attachLegend = () => {
            const root = this.rootRef?.el;
            if (!root || root.querySelector(".o_planning_drag_legend_bar")) {
                return;
            }
            const legend = planningLegendBarEl();
            const table = root.querySelector("table");
            if (table) {
                table.after(legend);
            } else {
                root.appendChild(legend);
            }
        };
        onMounted(attachLegend);
        onPatched(attachLegend);
    },
});
