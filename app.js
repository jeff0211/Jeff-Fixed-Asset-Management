// Phase 1-4 — static client app for Fixed Asset Register.
// Reads/writes Supabase using the public anon key (RLS protects writes).
// Phase 4 adds the year-end Excel report generator (ExcelJS).

// ===== Top-level constants =====
const PAGE_SIZE = 10;
const RESIDUAL_VALUE = 1.0;
const COMPANY_NAME = 'MEGA JUTAMAS SDN BHD (663951-U)';
const MONTHS = [
  [1, 'Jan'], [2, 'Feb'], [3, 'Mar'], [4, 'Apr'], [5, 'May'], [6, 'Jun'],
  [7, 'Jul'], [8, 'Aug'], [9, 'Sep'], [10, 'Oct'], [11, 'Nov'], [12, 'Dec'],
];

// ===== Small helpers =====
const todayISO = () => new Date().toISOString().split('T')[0];
const yearFromISO = (s) => {
  if (!s) return new Date().getFullYear();
  const y = parseInt(String(s).substring(0, 4), 10);
  return isNaN(y) ? new Date().getFullYear() : y;
};
const formatMoney = (n) =>
  `RM ${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// ===== Report math helpers =====
function resolvePY(a) {
  if (a.purchase_year !== null && a.purchase_year !== undefined && a.purchase_year !== '') {
    const y = parseInt(a.purchase_year, 10);
    if (!isNaN(y)) return y;
  }
  if (a.purchase_date) {
    const y = parseInt(String(a.purchase_date).substring(0, 4), 10);
    if (!isNaN(y)) return y;
  }
  return null;
}
function dispMonth(d) {
  if (d.disposal_date) {
    const parts = String(d.disposal_date).split('-');
    if (parts.length >= 2) {
      const m = parseInt(parts[1], 10);
      if (!isNaN(m)) return m;
    }
  }
  return 12;
}
function dispYear(d) {
  if (d.disposal_year) {
    const y = parseInt(d.disposal_year, 10);
    if (!isNaN(y)) return y;
  }
  return null;
}
function disposalAccDepAt(d, originalCost, rate, py) {
  if (!originalCost || !py) return 0.0;
  const dispCost = Number(d.total_disposal_cost || 0);
  const dy = dispYear(d) ?? py;
  const dm = dispMonth(d);
  const monthsAtDisposal = Math.max(0, (dy - py) * 12 + dm);
  const monthly = (originalCost * rate) / 12.0;
  const share = dispCost / originalCost;
  return Math.min(monthly * share * monthsAtDisposal, dispCost);
}
function parentFullDispYM(parentDisposals, originalCost) {
  if (!parentDisposals?.length || !originalCost || originalCost <= 0) return [null, null];
  const sorted = [...parentDisposals].sort((a, b) => {
    const da = a.disposal_date || '9999-12-31';
    const db = b.disposal_date || '9999-12-31';
    return String(da).localeCompare(String(db));
  });
  let cum = 0;
  for (const d of sorted) {
    cum += Number(d.total_disposal_cost || 0);
    if (cum >= originalCost - 0.01) return [dispYear(d), dispMonth(d)];
  }
  return [null, null];
}

function buildAdditionRow(add, parentA, year, month, parentDispY, parentDispM) {
  const addCost = Number(add.addition_cost || 0);
  const rate = Number(add.depreciation_rate || 0) / 100.0;

  const py = resolvePY(add);
  if (py === null || py > year) return null;

  const additionInYear = py === year;
  const parentDisposedPast = parentDispY !== null && parentDispY < year;
  const parentDisposedInPeriod = (
    parentDispY !== null && parentDispY === year &&
    parentDispM !== null && parentDispM <= month
  );

  let costBf, costAddition, costDisposal, costCf;
  if (parentDisposedPast) {
    costBf = costAddition = costDisposal = costCf = 0;
  } else if (parentDisposedInPeriod) {
    costBf = additionInYear ? 0 : addCost;
    costAddition = additionInYear ? addCost : 0;
    costDisposal = addCost;
    costCf = 0;
  } else {
    costBf = additionInYear ? 0 : addCost;
    costAddition = additionInYear ? addCost : 0;
    costDisposal = 0;
    costCf = addCost;
  }

  const monthlyChargeFull = (addCost * rate) / 12.0;
  let monthsDepBF = py >= year ? 0 : (year - py) * 12;
  let monthsDepPeriodEnd = py <= year ? (year - py) * 12 + month : 0;

  if (parentDispY !== null) {
    const maxMonthsAtDisposal = Math.max(0, (parentDispY - py) * 12 + (parentDispM ?? 12));
    monthsDepBF = Math.min(monthsDepBF, maxMonthsAtDisposal);
    monthsDepPeriodEnd = Math.min(monthsDepPeriodEnd, maxMonthsAtDisposal);
  }

  // Cap accumulated dep at (cost − residual) so NBV bottoms at RESIDUAL_VALUE
  // for in-service additions. When the parent is fully disposed in the period,
  // the disposal column carries the dep out cleanly to NBV = 0.
  const accDepCap = Math.max(addCost - RESIDUAL_VALUE, 0);
  const accDepFullBF = Math.min(monthlyChargeFull * monthsDepBF, accDepCap);
  const accDepFullAtPeriod = Math.min(monthlyChargeFull * monthsDepPeriodEnd, accDepCap);

  let accDepBf, accDepDisposal, currentCharge, accDepCf;
  if (parentDisposedPast) {
    accDepBf = accDepDisposal = currentCharge = accDepCf = 0;
  } else if (parentDisposedInPeriod) {
    accDepBf = accDepFullBF;
    currentCharge = Math.max(accDepFullAtPeriod - accDepBf, 0);
    accDepDisposal = accDepBf + currentCharge;
    accDepCf = 0;
  } else {
    accDepBf = accDepFullBF;
    accDepDisposal = 0;
    currentCharge = Math.max(accDepFullAtPeriod - accDepBf, 0);
    const residual = costCf > 0 ? RESIDUAL_VALUE : 0;
    currentCharge = Math.min(currentCharge, Math.max(costCf - accDepBf - residual, 0));
    accDepCf = accDepBf + currentCharge;
  }

  const nbvCurrent = costCf - accDepCf;
  const nbvPrior = ((additionInYear || parentDisposedPast) ? 0 : addCost) - accDepBf;

  const desc = add.description || 'Addition';
  return {
    category: parentA.categories?.name || 'Uncategorized',
    location: parentA.locations?.name || 'No location',
    description: `+ ${desc}`,
    reference: '',
    unit: add.quantity || 0,
    depreciation_rate: rate,
    year_of_purchase: py,
    cost_bf: costBf,
    cost_addition: costAddition,
    cost_disposal: costDisposal,
    cost_transfer_in: 0,
    cost_transfer_inout: 0,
    cost_cf: costCf,
    acc_dep_bf: accDepBf,
    acc_dep_disposal: accDepDisposal,
    acc_dep_transfer_in: 0,
    acc_dep_transfer_inout: 0,
    current_charge: currentCharge,
    monthly_charge: monthlyChargeFull,
    acc_dep_cf: accDepCf,
    nbv_current: nbvCurrent,
    nbv_prior: nbvPrior,
    remarks: add.remarks || '',
    _is_addition: true,
    _parent_id: add.parent_asset_id,
  };
}

// ===== Excel builder =====
const SUM_FIELDS = [
  'cost_bf', 'cost_addition', 'cost_disposal', 'cost_transfer_in', 'cost_transfer_inout',
  'cost_cf', 'acc_dep_bf', 'acc_dep_disposal', 'acc_dep_transfer_in', 'acc_dep_transfer_inout',
  'current_charge', 'monthly_charge', 'acc_dep_cf', 'nbv_current', 'nbv_prior',
];
const FIELD_TO_COL = {
  cost_bf: 7, cost_addition: 8, cost_disposal: 9, cost_transfer_in: 10,
  cost_transfer_inout: 11, cost_cf: 12, acc_dep_bf: 13, acc_dep_disposal: 14,
  acc_dep_transfer_in: 15, acc_dep_transfer_inout: 16, current_charge: 17,
  monthly_charge: 18, acc_dep_cf: 19, nbv_current: 20, nbv_prior: 21,
};
const LAST_COL = 22; // V (REMARKS)

const MONEY_FMT = '#,##0.00;-#,##0.00;-';
const RATE_FMT  = '0.0%';

async function buildPeriodWorkbook(rows, year, month) {
  const wb = new ExcelJS.Workbook();
  const monthShort = (MONTHS.find(m => m[0] === month)?.[1] || '').toUpperCase();
  const ws = wb.addWorksheet(`${monthShort} ${year}`);

  const lastDay = new Date(year, month, 0).getDate();
  const periodStr = `${String(lastDay).padStart(2, '0')}.${String(month).padStart(2, '0')}.${year}`;
  const bfStr = `01.01.${year}`;
  const priorStr = `31.12.${year - 1}`;

  const thin = { style: 'thin', color: { argb: 'FF000000' } };
  const borderFull = { top: thin, bottom: thin, left: thin, right: thin };
  const borderVertical = { left: thin, right: thin };
  const headerFill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF2F2F2' } };

  function applyBorder(rowIdx, full = false) {
    const b = full ? borderFull : borderVertical;
    for (let c = 1; c <= LAST_COL; c++) {
      ws.getCell(rowIdx, c).border = b;
    }
  }

  // Title rows
  const titleCell = ws.getCell('A1');
  titleCell.value = COMPANY_NAME;
  titleCell.font = { bold: true, size: 12 };

  const subTitle = ws.getCell('A3');
  subTitle.value = `FIXED ASSET REGISTERED AS AT ${periodStr}`;
  subTitle.font = { bold: true, size: 11 };

  // Header rows (5 = top, 6 = sub)
  const headersTop = [
    ['A5', 'DESCRIPTIONS'], ['B5', 'REFERENCE'], ['C5', 'UNIT'], ['D5', 'LOCATION'],
    ['E5', 'DEPRECIATION RATE'], ['F5', 'YEAR OF PURCHASE'],
    ['G5', 'COST'], ['M5', 'ACCUMULATED DEPRECIATION'], ['T5', 'NET BOOK VALUE'],
    ['V5', 'REMARKS'],
  ];
  const headersSub = [
    ['G6', `B/F AS AT\n${bfStr}\nRM`],
    ['H6', 'ADDITION'], ['I6', 'DISPOSAL'],
    ['J6', 'TRANSFER IN'], ['K6', 'TRANSFER IN/(OUT)'],
    ['L6', `C/F AS AT\n${periodStr}\nRM`],
    ['M6', `B/F AS AT\n${bfStr}\nRM`],
    ['N6', 'DISPOSAL'], ['O6', 'TRANSFER IN'], ['P6', 'TRANSFER IN/(OUT)'],
    ['Q6', 'CURRENT CHARGE'], ['R6', 'MONTHLY CHARGE'],
    ['S6', `C/F AS AT\n${periodStr}\nRM`],
    ['T6', `AS AT\n${periodStr}\nRM`],
    ['U6', `AS AT\n${priorStr}\nRM`],
  ];
  for (const [addr, val] of [...headersTop, ...headersSub]) {
    const c = ws.getCell(addr);
    c.value = val;
    c.font = { bold: true };
    c.alignment = { horizontal: 'center', vertical: 'center', wrapText: true };
    c.fill = headerFill;
  }

  // Merges
  ws.mergeCells('G5:L5');
  ws.mergeCells('M5:S5');
  ws.mergeCells('T5:U5');
  ws.mergeCells('V5:V6');
  for (const col of ['A', 'B', 'C', 'D', 'E', 'F']) {
    ws.mergeCells(`${col}5:${col}6`);
  }

  applyBorder(5, true);
  applyBorder(6, true);
  applyBorder(7);              // bridge blank row
  ws.getRow(6).height = 50;

  // Group rows
  const grouped = {};            // category → location → [parentId,...]
  const parentLookup = {};
  const additionBuckets = {};
  for (const r of rows) {
    if (r._is_addition) {
      (additionBuckets[r._parent_id] ||= []).push(r);
    } else {
      parentLookup[r._parent_id] = r;
      (grouped[r.category] ||= {});
      (grouped[r.category][r.location] ||= []).push(r._parent_id);
    }
  }

  function writeDataRow(rowIdx, r, indent = 0) {
    const descCell = ws.getCell(rowIdx, 1);
    descCell.value = r.description;
    if (indent) {
      descCell.alignment = { indent, vertical: 'top', wrapText: true };
      descCell.font = { italic: true };
    }
    ws.getCell(rowIdx, 2).value = r.reference;
    ws.getCell(rowIdx, 3).value = r.unit;
    // Column 4 (LOCATION) is intentionally left blank for now — will hold
    // per-asset location detail (e.g. "Shelf B-3") added in a later iteration.
    const rateCell = ws.getCell(rowIdx, 5);
    rateCell.value = r.depreciation_rate;
    rateCell.numFmt = RATE_FMT;
    ws.getCell(rowIdx, 6).value = r.year_of_purchase;
    for (const [f, col] of Object.entries(FIELD_TO_COL)) {
      const cell = ws.getCell(rowIdx, col);
      cell.value = Math.round(r[f] * 100) / 100;
      cell.numFmt = MONEY_FMT;
      if (indent) cell.font = { italic: true };
    }
    // Remarks (V)
    const remCell = ws.getCell(rowIdx, 22);
    remCell.value = r.remarks || '';
    remCell.alignment = { indent, vertical: 'top', wrapText: true, horizontal: 'left' };
    if (indent) remCell.font = { italic: true };

    applyBorder(rowIdx);
  }

  function writeSubtotalRow(rowIdx, label, totals, font = { bold: true, italic: true }) {
    const labelCell = ws.getCell(rowIdx, 1);
    labelCell.value = label;
    labelCell.font = font;
    for (const [f, col] of Object.entries(FIELD_TO_COL)) {
      const cell = ws.getCell(rowIdx, col);
      cell.value = Math.round(totals[f] * 100) / 100;
      cell.font = font;
      cell.numFmt = MONEY_FMT;
    }
    applyBorder(rowIdx);
  }

  const grandTotals = Object.fromEntries(SUM_FIELDS.map(f => [f, 0]));
  let curRow = 8;

  const categories = Object.keys(grouped).sort();
  for (const category of categories) {
    const catCell = ws.getCell(curRow, 1);
    catCell.value = category;
    catCell.font = { bold: true };
    applyBorder(curRow);
    curRow++;

    const catTotals = Object.fromEntries(SUM_FIELDS.map(f => [f, 0]));

    const locations = Object.keys(grouped[category]).sort();
    for (const location of locations) {
      // Blank separator row before every location header
      applyBorder(curRow);
      curRow++;

      const locCell = ws.getCell(curRow, 1);   // column A — sits above the asset list
      locCell.value = location;
      locCell.font = { bold: true };
      applyBorder(curRow);
      curRow++;

      const locTotals = Object.fromEntries(SUM_FIELDS.map(f => [f, 0]));

      for (const parentId of grouped[category][location]) {
        const parentRow = parentLookup[parentId];
        const additions = additionBuckets[parentId] || [];

        writeDataRow(curRow, parentRow);
        for (const f of SUM_FIELDS) locTotals[f] += parentRow[f];
        curRow++;

        for (const addRow of additions) {
          writeDataRow(curRow, addRow, 2);
          for (const f of SUM_FIELDS) locTotals[f] += addRow[f];
          curRow++;
        }

        if (additions.length > 0) {
          const psub = Object.fromEntries(
            SUM_FIELDS.map(f => [f, parentRow[f] + additions.reduce((s, a) => s + a[f], 0)])
          );
          writeSubtotalRow(curRow, `Subtotal — ${parentRow.description}`, psub, { italic: true });
          curRow++;
        }
      }

      writeSubtotalRow(curRow, `Subtotal — ${location}`, locTotals, { italic: true });
      for (const f of SUM_FIELDS) catTotals[f] += locTotals[f];
      curRow++;
      // (removed post-location blank — next iteration's pre-location blank handles spacing)
    }

    // Blank row before the category total
    applyBorder(curRow);
    curRow++;

    writeSubtotalRow(curRow, `TOTAL ${category}`, catTotals, { bold: true });
    for (const f of SUM_FIELDS) grandTotals[f] += catTotals[f];
    curRow++;
    applyBorder(curRow);
    curRow++;
  }

  writeSubtotalRow(curRow, 'GRAND TOTAL', grandTotals, { bold: true });

  // Freeze panes
  ws.views = [{ state: 'frozen', xSplit: 1, ySplit: 7 }];

  // Column widths
  const widths = { A: 50, B: 12, C: 6, D: 22, E: 10, F: 8,
                   G: 14, H: 12, I: 12, J: 12, K: 14, L: 14,
                   M: 14, N: 12, O: 12, P: 14, Q: 14, R: 14, S: 14,
                   T: 14, U: 14, V: 36 };
  for (const [col, w] of Object.entries(widths)) {
    ws.getColumn(col).width = w;
  }

  return await wb.xlsx.writeBuffer();
}

// ===== Alpine app =====
document.addEventListener('alpine:init', () => {
  Alpine.data('appState', () => ({
    // ===== UI state =====
    tabs: [
      { id: 'dashboard',   label: 'Dashboard' },
      { id: 'addition',    label: 'Addition' },
      { id: 'disposal',    label: 'Disposal' },
      { id: 'reports',     label: 'Reports' },
      { id: 'maintenance', label: 'Maintenance' },
    ],
    activeTab: 'dashboard',
    configMissing: !!window.__configMissing || !window.SUPABASE_URL || !window.SUPABASE_KEY,

    MONTHS,

    // ===== Data =====
    supabase: null,
    loading: false,
    loadingAdds: false,

    assets: [],
    searchQuery: '',
    page: 1,

    additions: [],
    additionsSearchQuery: '',
    additionsPage: 1,

    cats: [],
    locs: [],
    rates: [],
    activeAssets: [],

    // asset_id → total quantity_disposed (across all disposal records)
    disposalsByAsset: {},

    // ===== Forms (Add tab) =====
    newAsset: {
      name: '', categoryId: null, locationId: null,
      qty: 1, unitCost: 0, depRate: null, status: 'Active',
      purchaseDate: todayISO(), remarks: '',
    },
    newAssetSaving: false,

    newAddition: {
      parentId: null, description: '',
      qty: 1, unitCost: 0, depRate: null,
      purchaseDate: todayISO(), remarks: '',
    },
    additionSaving: false,

    // ===== Disposal form =====
    availableAssets: [],   // active assets with qty > 0
    disposalForm: {
      assetId: null,
      qty: 1, unitCost: 0,
      salesProceed: 0,
      date: todayISO(),
      remarks: '',
    },
    disposalSaving: false,

    // ===== Maintenance state =====
    newCatName: '',
    newLocName: '',
    newRateName: '',
    newRatePct: 10.0,
    editingCat: null,           // { id, name }
    deletingCat: null,
    editingLoc: null,
    deletingLoc: null,
    editingRate: null,          // { id, rate_name, percentage }
    deletingRate: null,

    // ===== Edit / Delete modals =====
    editingAsset: null,
    deletingAsset: null,
    editingAssetSaving: false,

    editingAddition: null,
    deletingAddition: null,
    editingAdditionSaving: false,

    // ===== Reports controls =====
    report: {
      year: new Date().getFullYear(),
      month: new Date().getMonth() + 1,
      generating: false,
    },

    // ===== Toasts =====
    toasts: [],

    // ===== Lifecycle =====
    async init() {
      if (this.configMissing) return;
      try {
        this.supabase = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_KEY);
      } catch (err) {
        console.error('Failed to create Supabase client:', err);
        this.configMissing = true;
        return;
      }
      // Load disposal aggregates first so shapeAsset can attach qty_disposed
      await this.loadDisposalAggregates();
      await Promise.all([
        this.loadAssets(),
        this.loadAdditions(),
        this.loadDropdowns(),
        this.loadActiveAssets(),
        this.loadAvailableAssets(),
      ]);
    },

    async loadDisposalAggregates() {
      try {
        const { data, error } = await this.supabase
          .from('disposals')
          .select('asset_id, quantity_disposed');
        if (error) throw error;
        const agg = {};
        for (const d of data || []) {
          if (!d.asset_id) continue;
          agg[d.asset_id] = (agg[d.asset_id] || 0) + (Number(d.quantity_disposed) || 0);
        }
        this.disposalsByAsset = agg;
      } catch (err) {
        console.error('loadDisposalAggregates:', err);
      }
    },

    // ===== Toasts =====
    notify(message, type = 'info') {
      const id = Date.now() + Math.random();
      this.toasts.push({ id, message, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== id);
      }, 3500);
    },

    // ===== Computed (form derived) =====
    get newAssetTotal()    { return Number(this.newAsset.qty || 0) * Number(this.newAsset.unitCost || 0); },
    get newAssetYear()     { return yearFromISO(this.newAsset.purchaseDate); },
    get newAdditionTotal() { return Number(this.newAddition.qty || 0) * Number(this.newAddition.unitCost || 0); },
    get newAdditionYear()  { return yearFromISO(this.newAddition.purchaseDate); },
    get selectedParent()   { return this.activeAssets.find(a => a.id === this.newAddition.parentId) || null; },

    get editAssetTotal()    { return this.editingAsset ? Number(this.editingAsset.qty || 0) * Number(this.editingAsset.unitCost || 0) : 0; },
    get editAssetYear()     { return this.editingAsset ? yearFromISO(this.editingAsset.purchaseDate) : ''; },
    get editAdditionTotal() { return this.editingAddition ? Number(this.editingAddition.qty || 0) * Number(this.editingAddition.unitCost || 0) : 0; },
    get editAdditionYear()  { return this.editingAddition ? yearFromISO(this.editingAddition.purchaseDate) : ''; },

    // ===== Data loaders =====
    async loadDropdowns() {
      try {
        const [c, l, r] = await Promise.all([
          this.supabase.from('categories').select('*').order('id'),
          this.supabase.from('locations').select('*').order('id'),
          this.supabase.from('depreciation_rates').select('*').order('id'),
        ]);
        if (c.error) throw c.error;
        if (l.error) throw l.error;
        if (r.error) throw r.error;
        this.cats = c.data || [];
        this.locs = l.data || [];
        this.rates = r.data || [];
      } catch (err) {
        console.error('loadDropdowns:', err);
        this.notify(`Could not load dropdowns: ${err.message || err}`, 'negative');
      }
    },

    async loadActiveAssets() {
      try {
        const { data, error } = await this.supabase
          .from('assets')
          .select('id, name, purchase_cost, depreciation_rate, category_id, location_id, categories(name), locations(name)')
          .eq('status', 'Active')
          .order('name');
        if (error) throw error;
        this.activeAssets = (data || []).map(r => ({
          id: r.id,
          name: r.name || '',
          purchase_cost: Number(r.purchase_cost) || 0,
          depreciation_rate: r.depreciation_rate,
          category: r.categories?.name || '',
          location: r.locations?.name || '',
        }));
      } catch (err) {
        console.error('loadActiveAssets:', err);
        this.notify(`Could not load active assets: ${err.message || err}`, 'negative');
      }
    },

    async loadAssets() {
      this.loading = true;
      try {
        const { data, error } = await this.supabase
          .from('assets')
          .select('*, categories(name), locations(name)')
          .order('id', { ascending: false });
        if (error) throw error;
        this.assets = data.map(r => this.shapeAsset(r));
      } catch (err) {
        console.error('loadAssets:', err);
        this.notify(`Could not load assets: ${err.message || err}`, 'negative');
      } finally {
        this.loading = false;
      }
    },

    async loadAdditions() {
      this.loadingAdds = true;
      try {
        const { data, error } = await this.supabase
          .from('asset_additions')
          .select('*, assets(name)')
          .order('id', { ascending: false });
        if (error) throw error;
        this.additions = (data || []).map(r => this.shapeAddition(r));
      } catch (err) {
        console.error('loadAdditions:', err);
        this.notify(`Could not load additions: ${err.message || err}`, 'negative');
      } finally {
        this.loadingAdds = false;
      }
    },

    shapeAsset(r) {
      const cost = Number(r.purchase_cost) || 0;
      const qty = r.quantity || 0;
      const qtyDisposed = this.disposalsByAsset[r.id] || 0;
      const item = {
        id: r.id,
        name: r.name || '',
        category_id: r.category_id || null,
        location_id: r.location_id || null,
        category: r.categories?.name || 'N/A',
        location: r.locations?.name || 'No location',
        status: r.status || 'Active',
        purchase_cost: cost,
        priceFormatted: formatMoney(cost),
        quantity: qty,
        qty_disposed: qtyDisposed,
        qty_original: qty + qtyDisposed,
        unit_cost: Number(r.unit_cost) || 0,
        depreciation_rate: r.depreciation_rate !== null && r.depreciation_rate !== undefined ? Number(r.depreciation_rate) : null,
        purchase_year: r.purchase_year,
        purchase_date: r.purchase_date,
        remarks: r.remarks || '',
      };
      item._search = this.buildAssetSearchBlob(item);
      return item;
    },

    shapeAddition(r) {
      const cost = Number(r.addition_cost) || 0;
      const item = {
        id: r.id,
        parent_asset_id: r.parent_asset_id,
        parent_name: r.assets?.name || '—',
        description: r.description || '',
        quantity: r.quantity || 0,
        unit_cost: Number(r.unit_cost) || 0,
        addition_cost: cost,
        additionCostFmt: formatMoney(cost),
        depreciation_rate: r.depreciation_rate !== null && r.depreciation_rate !== undefined ? Number(r.depreciation_rate) : null,
        purchase_date: r.purchase_date || '',
        purchase_year: r.purchase_year,
        remarks: r.remarks || '',
      };
      item._search = this.buildAdditionSearchBlob(item);
      return item;
    },

    buildAssetSearchBlob(a) {
      return [
        a.name, a.category, a.location, a.status,
        a.priceFormatted, a.purchase_cost.toFixed(2),
        a.purchase_year || '', a.purchase_date || '',
        a.depreciation_rate ?? '', `qty ${a.quantity}`,
        a.qty_disposed > 0 ? `${a.qty_disposed} disposed` : '',
        a.remarks,
      ].filter(p => p !== '' && p !== null && p !== undefined).join(' ').toLowerCase();
    },

    buildAdditionSearchBlob(a) {
      return [
        a.parent_name, a.description, a.remarks,
        a.additionCostFmt, a.addition_cost.toFixed(2),
        a.unit_cost.toFixed(2),
        a.purchase_year || '', a.purchase_date || '',
        a.depreciation_rate ?? '', `qty ${a.quantity}`,
      ].filter(p => p !== '' && p !== null && p !== undefined).join(' ').toLowerCase();
    },

    // ===== Sync helpers =====
    async syncDropdowns() {
      await this.loadDropdowns();
      this.notify('Dropdowns synced with master data', 'info');
    },
    async refreshAdditionLists() {
      await Promise.all([this.loadActiveAssets(), this.loadDropdowns()]);
      this.notify('Lists refreshed', 'info');
    },

    // ===== Save: New Asset =====
    async saveNewAsset() {
      const a = this.newAsset;
      if (!a.name || a.qty === null || a.qty === '' || a.unitCost === null || a.unitCost === '') {
        this.notify('Please fill in Description, Qty, and Unit Cost.', 'warning');
        return;
      }
      this.newAssetSaving = true;
      try {
        const { error } = await this.supabase.from('assets').insert({
          name: a.name,
          remarks: a.remarks || null,
          category_id: a.categoryId || null,
          location_id: a.locationId || null,
          quantity: parseInt(a.qty, 10) || 1,
          unit_cost: Number(a.unitCost) || 0,
          purchase_cost: this.newAssetTotal,
          depreciation_rate: a.depRate !== null ? Number(a.depRate) : null,
          purchase_date: a.purchaseDate || todayISO(),
          purchase_year: yearFromISO(a.purchaseDate),
          status: a.status || 'Active',
        });
        if (error) throw error;
        this.notify('Asset recorded successfully', 'positive');
        this.resetNewAssetForm();
        await Promise.all([this.loadAssets(), this.loadActiveAssets()]);
      } catch (err) {
        console.error('saveNewAsset:', err);
        this.notify(`Database error: ${err.message || err}`, 'negative');
      } finally {
        this.newAssetSaving = false;
      }
    },
    resetNewAssetForm() {
      this.newAsset = {
        name: '', categoryId: null, locationId: null,
        qty: 1, unitCost: 0, depRate: null, status: 'Active',
        purchaseDate: todayISO(), remarks: '',
      };
    },

    // ===== Save: New Addition =====
    async saveNewAddition() {
      const a = this.newAddition;
      if (!a.parentId) { this.notify('Please select a parent asset.', 'warning'); return; }
      if (!a.description || a.qty === null || a.qty === '' || a.unitCost === null || a.unitCost === '') {
        this.notify('Please fill in Description, Qty, and Unit Cost.', 'warning'); return;
      }
      this.additionSaving = true;
      try {
        const { error } = await this.supabase.from('asset_additions').insert({
          parent_asset_id: a.parentId,
          description: a.description,
          remarks: a.remarks || null,
          quantity: parseInt(a.qty, 10) || 1,
          unit_cost: Number(a.unitCost) || 0,
          addition_cost: this.newAdditionTotal,
          depreciation_rate: a.depRate !== null ? Number(a.depRate) : null,
          purchase_date: a.purchaseDate || todayISO(),
          purchase_year: yearFromISO(a.purchaseDate),
        });
        if (error) throw error;
        this.notify('Addition recorded successfully', 'positive');
        this.resetAdditionForm();
        await this.loadAdditions();
      } catch (err) {
        console.error('saveNewAddition:', err);
        this.notify(`Database error: ${err.message || err}`, 'negative');
      } finally {
        this.additionSaving = false;
      }
    },
    resetAdditionForm() {
      this.newAddition = {
        parentId: null, description: '',
        qty: 1, unitCost: 0, depRate: null,
        purchaseDate: todayISO(), remarks: '',
      };
    },
    onParentSelected() {
      const p = this.selectedParent;
      if (p && p.depreciation_rate !== null && p.depreciation_rate !== undefined) {
        const match = this.rates.find(r => Number(r.percentage) === Number(p.depreciation_rate));
        if (match) this.newAddition.depRate = Number(match.percentage);
      }
    },

    // ===== Disposal =====
    async loadAvailableAssets() {
      try {
        const { data, error } = await this.supabase
          .from('assets')
          .select('id, name, quantity, unit_cost, purchase_cost, category_id, location_id, categories(name), locations(name)')
          .eq('status', 'Active')
          .gt('quantity', 0)
          .order('name');
        if (error) throw error;
        this.availableAssets = (data || []).map(r => ({
          id: r.id,
          name: r.name || '',
          quantity: r.quantity || 0,
          unit_cost: Number(r.unit_cost) || 0,
          purchase_cost: Number(r.purchase_cost) || 0,
          category_id: r.category_id,
          location_id: r.location_id,
          category: r.categories?.name || '',
          location: r.locations?.name || '',
        }));
      } catch (err) {
        console.error('loadAvailableAssets:', err);
        this.notify(`Could not load available assets: ${err.message || err}`, 'negative');
      }
    },
    get selectedDisposalAsset() {
      return this.availableAssets.find(a => a.id === this.disposalForm.assetId) || null;
    },
    get disposalTotalCost() {
      return Number(this.disposalForm.qty || 0) * Number(this.disposalForm.unitCost || 0);
    },
    get disposalYearFromDate() {
      return yearFromISO(this.disposalForm.date);
    },
    onDisposalAssetSelected() {
      const a = this.selectedDisposalAsset;
      if (a) {
        // default disposal unit cost to the asset's recorded unit cost
        this.disposalForm.unitCost = a.unit_cost || 0;
        // cap qty at available
        if (this.disposalForm.qty > a.quantity) this.disposalForm.qty = a.quantity;
      }
    },
    async refreshDisposalList() {
      await this.loadAvailableAssets();
      this.notify('Asset list refreshed', 'info');
    },
    async saveDisposal() {
      const f = this.disposalForm;
      const a = this.selectedDisposalAsset;
      if (!a) { this.notify('Please select an asset to dispose.', 'warning'); return; }
      const qtyD = parseInt(f.qty, 10) || 0;
      if (qtyD < 1) { this.notify('Quantity disposed must be at least 1.', 'warning'); return; }
      if (qtyD > a.quantity) { this.notify(`Cannot dispose ${qtyD} — only ${a.quantity} available.`, 'warning'); return; }

      this.disposalSaving = true;
      try {
        const totalCost = this.disposalTotalCost;
        // 1. insert disposal record
        const ins = await this.supabase.from('disposals').insert({
          asset_id: a.id,
          name: a.name,
          remarks: f.remarks || null,
          category_id: a.category_id,
          location_id: a.location_id,
          sales_proceed: Number(f.salesProceed) || 0,
          quantity_disposed: qtyD,
          unit_cost: Number(f.unitCost) || 0,
          total_disposal_cost: totalCost,
          disposal_date: f.date || todayISO(),
          disposal_year: yearFromISO(f.date),
          status: 'Disposed',
        });
        if (ins.error) throw ins.error;

        // 2. decrement source asset
        const newQty = a.quantity - qtyD;
        const newPurchaseCost = Math.max(a.purchase_cost - totalCost, 0);
        const payload = { quantity: newQty, purchase_cost: newPurchaseCost };
        if (newQty <= 0) payload.status = 'Disposed';
        const upd = await this.supabase.from('assets').update(payload).eq('id', a.id);
        if (upd.error) throw upd.error;

        if (newQty <= 0) {
          this.notify('Asset fully disposed — status set to Disposed.', 'positive');
        } else {
          this.notify(`Disposal recorded. Remaining quantity: ${newQty}.`, 'positive');
        }

        // 3. clear form + refresh lists (aggregates first so shapeAsset sees them)
        this.resetDisposalForm();
        await this.loadDisposalAggregates();
        await Promise.all([
          this.loadAssets(),
          this.loadActiveAssets(),
          this.loadAvailableAssets(),
          this.loadAdditions(),
        ]);
      } catch (err) {
        console.error('saveDisposal:', err);
        this.notify(`Database error: ${err.message || err}`, 'negative');
      } finally {
        this.disposalSaving = false;
      }
    },
    resetDisposalForm() {
      this.disposalForm = {
        assetId: null,
        qty: 1, unitCost: 0,
        salesProceed: 0,
        date: todayISO(),
        remarks: '',
      };
    },

    // ===== Maintenance: Categories =====
    async addCategory() {
      if (!this.newCatName?.trim()) return;
      try {
        const { error } = await this.supabase.from('categories').insert({ name: this.newCatName.trim() });
        if (error) throw error;
        this.newCatName = '';
        this.notify('Category added', 'positive');
        await this.loadDropdowns();
      } catch (err) { this.notify(`Add error: ${err.message || err}`, 'negative'); }
    },
    openEditCategory(c) { this.editingCat = { id: c.id, name: c.name }; },
    async saveCategoryEdit() {
      const c = this.editingCat;
      if (!c?.name?.trim()) return;
      try {
        const { error } = await this.supabase.from('categories').update({ name: c.name.trim() }).eq('id', c.id);
        if (error) throw error;
        this.editingCat = null;
        this.notify('Category saved', 'positive');
        await Promise.all([this.loadDropdowns(), this.loadAssets(), this.loadActiveAssets(), this.loadAvailableAssets()]);
      } catch (err) { this.notify(`Save error: ${err.message || err}`, 'negative'); }
    },
    confirmDeleteCategory(c) { this.deletingCat = { id: c.id, name: c.name }; },
    async deleteCategory() {
      if (!this.deletingCat) return;
      try {
        const { error } = await this.supabase.from('categories').delete().eq('id', this.deletingCat.id);
        if (error) throw error;
        this.deletingCat = null;
        this.notify('Category deleted', 'warning');
        await Promise.all([this.loadDropdowns(), this.loadAssets(), this.loadActiveAssets(), this.loadAvailableAssets()]);
      } catch (err) { this.notify(`Delete error: ${err.message || err}`, 'negative'); }
    },

    // ===== Maintenance: Locations =====
    async addLocation() {
      if (!this.newLocName?.trim()) return;
      try {
        const { error } = await this.supabase.from('locations').insert({ name: this.newLocName.trim() });
        if (error) throw error;
        this.newLocName = '';
        this.notify('Location added', 'positive');
        await this.loadDropdowns();
      } catch (err) { this.notify(`Add error: ${err.message || err}`, 'negative'); }
    },
    openEditLocation(l) { this.editingLoc = { id: l.id, name: l.name }; },
    async saveLocationEdit() {
      const l = this.editingLoc;
      if (!l?.name?.trim()) return;
      try {
        const { error } = await this.supabase.from('locations').update({ name: l.name.trim() }).eq('id', l.id);
        if (error) throw error;
        this.editingLoc = null;
        this.notify('Location saved', 'positive');
        await Promise.all([this.loadDropdowns(), this.loadAssets(), this.loadActiveAssets(), this.loadAvailableAssets()]);
      } catch (err) { this.notify(`Save error: ${err.message || err}`, 'negative'); }
    },
    confirmDeleteLocation(l) { this.deletingLoc = { id: l.id, name: l.name }; },
    async deleteLocation() {
      if (!this.deletingLoc) return;
      try {
        const { error } = await this.supabase.from('locations').delete().eq('id', this.deletingLoc.id);
        if (error) throw error;
        this.deletingLoc = null;
        this.notify('Location deleted', 'warning');
        await Promise.all([this.loadDropdowns(), this.loadAssets(), this.loadActiveAssets(), this.loadAvailableAssets()]);
      } catch (err) { this.notify(`Delete error: ${err.message || err}`, 'negative'); }
    },

    // ===== Maintenance: Depreciation Rates =====
    async addRate() {
      const pct = Number(this.newRatePct);
      if (this.newRatePct === null || this.newRatePct === '' || isNaN(pct)) return;
      try {
        const { error } = await this.supabase.from('depreciation_rates').insert({
          rate_name: `${pct}%`,           // schema requires NOT NULL — auto-derive from %
          percentage: pct,
        });
        if (error) throw error;
        this.newRatePct = 10.0;
        this.notify('Rate added', 'positive');
        await this.loadDropdowns();
      } catch (err) { this.notify(`Add error: ${err.message || err}`, 'negative'); }
    },
    openEditRate(r) { this.editingRate = { id: r.id, percentage: r.percentage }; },
    async saveRateEdit() {
      const r = this.editingRate;
      const pct = Number(r?.percentage);
      if (!r || isNaN(pct)) return;
      try {
        const { error } = await this.supabase.from('depreciation_rates').update({
          rate_name: `${pct}%`,
          percentage: pct,
        }).eq('id', r.id);
        if (error) throw error;
        this.editingRate = null;
        this.notify('Rate saved', 'positive');
        await this.loadDropdowns();
      } catch (err) { this.notify(`Save error: ${err.message || err}`, 'negative'); }
    },
    confirmDeleteRate(r) { this.deletingRate = { id: r.id, percentage: r.percentage }; },
    async deleteRate() {
      if (!this.deletingRate) return;
      try {
        const { error } = await this.supabase.from('depreciation_rates').delete().eq('id', this.deletingRate.id);
        if (error) throw error;
        this.deletingRate = null;
        this.notify('Rate deleted', 'warning');
        await this.loadDropdowns();
      } catch (err) { this.notify(`Delete error: ${err.message || err}`, 'negative'); }
    },

    // ===== Edit Asset =====
    openEditAsset(row) {
      this.editingAsset = {
        id: row.id,
        name: row.name,
        categoryId: row.category_id ?? null,
        locationId: row.location_id ?? null,
        qty: row.quantity || 1,
        unitCost: row.unit_cost || 0,
        depRate: row.depreciation_rate ?? null,
        status: row.status || 'Active',
        purchaseDate: row.purchase_date || todayISO(),
        remarks: row.remarks || '',
      };
    },

    async saveEditAsset() {
      const a = this.editingAsset;
      if (!a) return;
      if (!a.name || a.qty === null || a.qty === '' || a.unitCost === null || a.unitCost === '') {
        this.notify('Please fill in Description, Qty, and Unit Cost.', 'warning');
        return;
      }
      this.editingAssetSaving = true;
      try {
        const { error } = await this.supabase.from('assets').update({
          name: a.name,
          remarks: a.remarks || null,
          category_id: a.categoryId || null,
          location_id: a.locationId || null,
          quantity: parseInt(a.qty, 10) || 1,
          unit_cost: Number(a.unitCost) || 0,
          purchase_cost: this.editAssetTotal,
          depreciation_rate: a.depRate !== null ? Number(a.depRate) : null,
          purchase_date: a.purchaseDate || todayISO(),
          purchase_year: yearFromISO(a.purchaseDate),
          status: a.status || 'Active',
        }).eq('id', a.id);
        if (error) throw error;
        this.notify('Asset updated successfully', 'positive');
        this.editingAsset = null;
        await Promise.all([this.loadAssets(), this.loadActiveAssets(), this.loadAdditions()]);
      } catch (err) {
        console.error('saveEditAsset:', err);
        this.notify(`Database error: ${err.message || err}`, 'negative');
      } finally {
        this.editingAssetSaving = false;
      }
    },

    confirmDeleteAsset(row) { this.deletingAsset = { id: row.id, name: row.name }; },
    confirmDeleteAssetFromEdit() {
      if (!this.editingAsset) return;
      this.deletingAsset = { id: this.editingAsset.id, name: this.editingAsset.name };
    },
    async deleteAsset() {
      if (!this.deletingAsset) return;
      try {
        const { error } = await this.supabase.from('assets').delete().eq('id', this.deletingAsset.id);
        if (error) throw error;
        this.notify('Record deleted successfully', 'positive');
        this.deletingAsset = null;
        this.editingAsset = null;
        await Promise.all([this.loadAssets(), this.loadActiveAssets(), this.loadAdditions()]);
      } catch (err) {
        console.error('deleteAsset:', err);
        this.notify(`Delete error: ${err.message || err}`, 'negative');
      }
    },

    // ===== Edit Addition =====
    openEditAddition(row) {
      this.editingAddition = {
        id: row.id,
        parentId: row.parent_asset_id ?? null,
        description: row.description || '',
        qty: row.quantity || 1,
        unitCost: row.unit_cost || 0,
        depRate: row.depreciation_rate ?? null,
        purchaseDate: row.purchase_date || todayISO(),
        remarks: row.remarks || '',
      };
    },

    async saveEditAddition() {
      const a = this.editingAddition;
      if (!a) return;
      if (!a.parentId) { this.notify('Please select a parent asset.', 'warning'); return; }
      if (!a.description || a.qty === null || a.qty === '' || a.unitCost === null || a.unitCost === '') {
        this.notify('Please fill in Description, Qty, and Unit Cost.', 'warning'); return;
      }
      this.editingAdditionSaving = true;
      try {
        const { error } = await this.supabase.from('asset_additions').update({
          parent_asset_id: a.parentId,
          description: a.description,
          remarks: a.remarks || null,
          quantity: parseInt(a.qty, 10) || 1,
          unit_cost: Number(a.unitCost) || 0,
          addition_cost: this.editAdditionTotal,
          depreciation_rate: a.depRate !== null ? Number(a.depRate) : null,
          purchase_date: a.purchaseDate || todayISO(),
          purchase_year: yearFromISO(a.purchaseDate),
        }).eq('id', a.id);
        if (error) throw error;
        this.notify('Addition updated', 'positive');
        this.editingAddition = null;
        await this.loadAdditions();
      } catch (err) {
        console.error('saveEditAddition:', err);
        this.notify(`Database error: ${err.message || err}`, 'negative');
      } finally {
        this.editingAdditionSaving = false;
      }
    },

    confirmDeleteAddition(row) {
      this.deletingAddition = { id: row.id, description: row.description, parent_name: row.parent_name };
    },
    confirmDeleteAdditionFromEdit() {
      if (!this.editingAddition) return;
      const parent = this.activeAssets.find(a => a.id === this.editingAddition.parentId);
      this.deletingAddition = {
        id: this.editingAddition.id,
        description: this.editingAddition.description,
        parent_name: parent?.name || '—',
      };
    },
    async deleteAddition() {
      if (!this.deletingAddition) return;
      try {
        const { error } = await this.supabase.from('asset_additions').delete().eq('id', this.deletingAddition.id);
        if (error) throw error;
        this.notify('Addition deleted', 'positive');
        this.deletingAddition = null;
        this.editingAddition = null;     // close edit modal if delete came from there
        await this.loadAdditions();
      } catch (err) {
        console.error('deleteAddition:', err);
        this.notify(`Delete error: ${err.message || err}`, 'negative');
      }
    },

    // ===== Generate Excel report =====
    async generateReport() {
      if (typeof ExcelJS === 'undefined') {
        this.notify('Excel library not loaded. Refresh the page and try again.', 'negative');
        return;
      }
      this.report.generating = true;
      try {
        const rows = await this.computePeriodRows(this.report.year, this.report.month);
        const buffer = await buildPeriodWorkbook(rows, this.report.year, this.report.month);
        const blob = new Blob([buffer], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
        const url = URL.createObjectURL(blob);
        const m = String(this.report.month).padStart(2, '0');
        const fname = `Fixed_Asset_Register_${this.report.year}_${m}.xlsx`;
        const a = document.createElement('a');
        a.href = url;
        a.download = fname;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        const lastDay = new Date(this.report.year, this.report.month, 0).getDate();
        this.notify(`Report as at ${String(lastDay).padStart(2,'0')}.${m}.${this.report.year} ready`, 'positive');
      } catch (err) {
        console.error('generateReport:', err);
        this.notify(`Could not build report: ${err.message || err}`, 'negative');
      } finally {
        this.report.generating = false;
      }
    },

    async computePeriodRows(year, month) {
      const [assetsRes, disposalsRes, additionsRes] = await Promise.all([
        this.supabase.from('assets').select(
          'id, name, quantity, unit_cost, purchase_cost, depreciation_rate, ' +
          'purchase_year, purchase_date, status, category_id, location_id, ' +
          'remarks, categories(name), locations(name)'
        ),
        this.supabase.from('disposals').select('*'),
        this.supabase.from('asset_additions').select('*'),
      ]);
      if (assetsRes.error) throw assetsRes.error;
      if (disposalsRes.error) throw disposalsRes.error;
      if (additionsRes.error) throw additionsRes.error;

      const assets = assetsRes.data || [];
      const disposals = disposalsRes.data || [];
      const additions = additionsRes.data || [];

      const dispByAsset = {};
      for (const d of disposals) {
        if (d.asset_id) (dispByAsset[d.asset_id] ||= []).push(d);
      }
      const addByAsset = {};
      for (const a of additions) {
        if (a.parent_asset_id) (addByAsset[a.parent_asset_id] ||= []).push(a);
      }

      const isPast = (d) => {
        const dy = dispYear(d);
        return dy !== null && dy < year;
      };
      const isInPeriod = (d) => {
        const dy = dispYear(d);
        if (dy === null || dy !== year) return false;
        return dispMonth(d) <= month;
      };

      const rows = [];
      for (const a of assets) {
        const py = resolvePY(a);
        if (py === null || py > year) continue;

        const rate = Number(a.depreciation_rate || 0) / 100.0;
        const currentCost = Number(a.purchase_cost || 0);

        const allDisposals = dispByAsset[a.id] || [];
        const allDisposedCost = allDisposals.reduce((s, d) => s + Number(d.total_disposal_cost || 0), 0);
        const originalCost = currentCost + allDisposedCost;

        const pastDisposals = allDisposals.filter(isPast);
        const periodDisposals = allDisposals.filter(isInPeriod);
        const pastDisposedCost = pastDisposals.reduce((s, d) => s + Number(d.total_disposal_cost || 0), 0);
        const periodDisposedCost = periodDisposals.reduce((s, d) => s + Number(d.total_disposal_cost || 0), 0);

        let costBf, costAddition;
        if (py === year) {
          costBf = 0;
          costAddition = originalCost;
        } else {
          costBf = originalCost - pastDisposedCost;
          costAddition = 0;
        }
        const costDisposal = periodDisposedCost;
        const costCf = costBf + costAddition - costDisposal;

        const monthlyChargeFull = (originalCost * rate) / 12.0;
        const monthsDepBF = py >= year ? 0 : (year - py) * 12;
        const monthsDepPeriodEnd = py <= year ? (year - py) * 12 + month : 0;
        // Cap accumulated dep at (cost − residual) so NBV bottoms at
        // RESIDUAL_VALUE for in-service assets; disposal column handles the
        // fully-disposed case independently (cost_cf = 0 → NBV = 0).
        const accDepCap = Math.max(originalCost - RESIDUAL_VALUE, 0);
        const accDepFullBF = Math.min(monthlyChargeFull * monthsDepBF, accDepCap);
        const accDepFullAtPeriod = Math.min(monthlyChargeFull * monthsDepPeriodEnd, accDepCap);

        const pastDispAccDep = pastDisposals.reduce((s, d) => s + disposalAccDepAt(d, originalCost, rate, py), 0);
        const periodDispAccDep = periodDisposals.reduce((s, d) => s + disposalAccDepAt(d, originalCost, rate, py), 0);

        const accDepBf = Math.max(accDepFullBF - pastDispAccDep, 0);
        const accDepDisposal = Math.min(periodDispAccDep, accDepFullAtPeriod);
        let currentCharge = Math.max(
          accDepFullAtPeriod - pastDispAccDep - periodDispAccDep - accDepBf, 0
        );
        const residual = costCf > 0 ? RESIDUAL_VALUE : 0;
        currentCharge = Math.min(currentCharge, Math.max(costCf - (accDepBf - accDepDisposal) - residual, 0));
        const accDepCf = accDepBf - accDepDisposal + currentCharge;

        const nbvCurrent = costCf - accDepCf;
        const nbvPrior = costBf - accDepBf;

        rows.push({
          category: a.categories?.name || 'Uncategorized',
          location: a.locations?.name || 'No location',
          description: a.name || '',
          reference: '',
          unit: a.quantity || 0,
          depreciation_rate: rate,
          year_of_purchase: py,
          cost_bf: costBf,
          cost_addition: costAddition,
          cost_disposal: costDisposal,
          cost_transfer_in: 0,
          cost_transfer_inout: 0,
          cost_cf: costCf,
          acc_dep_bf: accDepBf,
          acc_dep_disposal: accDepDisposal,
          acc_dep_transfer_in: 0,
          acc_dep_transfer_inout: 0,
          current_charge: currentCharge,
          monthly_charge: monthlyChargeFull,
          acc_dep_cf: accDepCf,
          nbv_current: nbvCurrent,
          nbv_prior: nbvPrior,
          remarks: a.remarks || '',
          _is_addition: false,
          _parent_id: a.id,
        });

        const [pdy, pdm] = parentFullDispYM(allDisposals, originalCost);
        for (const add of (addByAsset[a.id] || [])) {
          const addRow = buildAdditionRow(add, a, year, month, pdy, pdm);
          if (addRow !== null) rows.push(addRow);
        }
      }
      return rows;
    },

    // ===== Derived (tables) =====
    // ===== Dashboard KPIs =====
    get kpiActiveCount()  { return this.assets.filter(a => a.status === 'Active').length; },
    get kpiActiveValue()  { return this.assets.filter(a => a.status === 'Active').reduce((s, a) => s + (a.purchase_cost || 0), 0); },
    get kpiDisposedCount(){ return this.assets.filter(a => a.status === 'Disposed').length; },
    get kpiAdditionsCount(){ return this.additions.length; },
    get kpiAdditionsValue(){ return this.additions.reduce((s, a) => s + (a.addition_cost || 0), 0); },

    get filteredAssets() {
      const q = (this.searchQuery || '').toLowerCase().trim();
      if (!q) return this.assets;
      const words = q.split(/\s+/).filter(Boolean);
      return this.assets.filter(a => words.every(w => a._search.includes(w)));
    },
    get totalPages() { return Math.max(1, Math.ceil(this.filteredAssets.length / PAGE_SIZE)); },
    get pagedAssets() {
      if (this.page > this.totalPages) this.page = this.totalPages;
      const start = (this.page - 1) * PAGE_SIZE;
      return this.filteredAssets.slice(start, start + PAGE_SIZE);
    },

    get filteredAdditions() {
      const q = (this.additionsSearchQuery || '').toLowerCase().trim();
      if (!q) return this.additions;
      const words = q.split(/\s+/).filter(Boolean);
      return this.additions.filter(a => words.every(w => a._search.includes(w)));
    },
    get additionsTotalPages() { return Math.max(1, Math.ceil(this.filteredAdditions.length / PAGE_SIZE)); },
    get pagedAdditions() {
      if (this.additionsPage > this.additionsTotalPages) this.additionsPage = this.additionsTotalPages;
      const start = (this.additionsPage - 1) * PAGE_SIZE;
      return this.filteredAdditions.slice(start, start + PAGE_SIZE);
    },
  }));
});
