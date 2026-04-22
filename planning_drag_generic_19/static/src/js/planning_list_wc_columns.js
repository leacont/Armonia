/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

const WC_COL_RE = /^wc_col_(\d+)$/;

/**
 * Standalone list views cannot use record fields in column_invisible (only list.evalContext).
 * Hide wc_col_N columns in the JS layer using planning_wc_slots_used on each row (same value).
 */
patch(ListRenderer.prototype, {
    getActiveColumns(listArg) {
        const cols = super.getActiveColumns(...arguments);
        const list = listArg || this.props?.list;
        if (!list || list.resModel !== "mrp.planning.order" || list.isGrouped) {
            return cols;
        }
        let slotCount = null;
        const first = list.records?.[0];
        if (first?.data && typeof first.data.planning_wc_slots_used === "number") {
            slotCount = first.data.planning_wc_slots_used;
        }
        if (slotCount === null || slotCount === undefined) {
            return cols;
        }
        return cols.filter((col) => {
            if (col.type !== "field" || !col.name) {
                return true;
            }
            const m = WC_COL_RE.exec(col.name);
            if (!m) {
                return true;
            }
            return parseInt(m[1], 10) <= slotCount;
        });
    },
});
