# gws_eln v2 (LabFlow) — Resolved Design Decisions

**Date:** 2026-05-29
**Status:** Decisions locked via grilling session. Source brainstorm: [specs.md](specs.md).
**Supersedes:** v1 unified model in [../global/](../global/) — v1 backend is treated as a *throwaway prototype* (plumbing kept, model rebuilt — see §7).

This document records the decisions that resolve the ambiguities in the v2 brainstorm
(`specs.md`). It is the source of truth for the v2 data model and rules. The brainstorm
remains the raw feature wishlist; this file is what we actually build.

---

## 1. Terminology (v1 → v2 rename)

| v1 (built prototype) | v2 (LabFlow) | Meaning |
|----------------------|--------------|---------|
| `Material` | **Item Sheet** | Catalog definition — *what a thing is* (name, consumable flag, default unit, files, tags, notes). Does NOT carry quantity/location. |
| `Material_Batch` | **Item** | The physical thing in the lab — carries a unique `code`, a free `label`, quantity, unit, location, expiry, status, optional serial number. **Everything (consume/split/move/use) acts on an Item.** |
| — (new) | **Reception** | The event that brings items into the lab. Holds supplier, `external_batch`, date, type. |
| — (new) | **Batch** | The reception's `external_batch` value (§9). NOT its own table — a field on Reception that, when set, is mirrored as a propagable `batch:<value>` tag on each received item (§14). |
| `Activity` (+ inputs/outputs) | **Activity** | One event taking 0..N input items → 0..N output items (§12). It is the audit log AND the source of provenance/lineage — lineage is *derived* from inputs/outputs, there is no separate lineage table. |

---

## 2. Core data model

```
ItemSheet (catalog)
  ├─ name, description, is_consumable
  ├─ code            ← exactly 4 chars [A-Z0-9], UNIQUE, IMMUTABLE; frontend auto-from-name, editable before save (§9)
  ├─ unit_type ENUM(volume,mass,length,count)  ← THE dimension; authoritative.
  │            ⚠️ IMMUTABLE once any Item references this sheet (see §13)
  ├─ storage_conditions  ← default for items (see §19)
  ├─ files, tags, notes
  └─ default_supplier (optional FK)
        │ 1:N
Item (THE physical entity)
  ├─ item_sheet_id (FK, NOT NULL)        ← every item has a sheet (see §3)
  ├─ code   = "{sheet.code}-{year}-{incr}"  e.g. ETHA-2026-0007  ← UNIQUE, IMMUTABLE, backend-gen; barcode/scan key (§9)
  ├─ label  (free text, editable, NOT unique, optional)  ← human name (§9)
  ├─ quantity                             ← stored in BASE unit; null/1 for serialized units
  ├─ unit_type                            ← write-once copy of sheet's dimension (see §13)
  ├─ concentration, concentration_unit    ← nullable; identity-defining (see §17)
  ├─ storage_conditions (nullable)        ← overrides sheet default (see §19)
  ├─ location_id (FK, NOT NULL)
  ├─ expiry_date
  ├─ serial_number (nullable)             ← non-consumable units (see §6); UNIQUE across all items (null-exempt, lab-wide)
  ├─ status: ACTIVE | EXHAUSTED | DISCARDED   ← STORED column, recomputed on every save (see §4)
  ├─ reception_id (FK, NULLABLE)          ← null for transform outputs (see §8)
  └─ tags → ItemTag rows, propagable through activities (see §14)
  NOTE: no parent_batch FK. Provenance lives in Activity inputs/outputs (§12).
  NOTE: identity is `code`; "which delivery/batch" is reception_id (§8) + the propagable `batch:` tag (§14).

Reception (entry event)
  ├─ type: RECEIVED | INTERNAL            (see §8)
  ├─ supplier_id    (required if RECEIVED, null if INTERNAL)
  ├─ external_batch (required if RECEIVED, optional if INTERNAL; NOT unique)
  │                 ← when set, mirrored as a propagable `batch:<value>` tag on each received item (§14)
  └─ created_at + audit
        │ 1:N
       Item

Activity (the event — see §12 for the full activity model)
  ├─ activity_type, description, note_id, from/to_location, reason, notes
  ├─ initial_concentration, final_concentration, concentration_unit, dilution_factor  ← nullable; dilute/concentrate only (§17)
  ├── activity_inputs   (item_id, role: INGREDIENT|INSTRUMENT, quantity_contributed, unit)  0..N
  └── activity_outputs  (item_id, quantity, unit_type)                                       0..N

  NOTE: there is no separate lineage table. Lineage IS a query over
  activity_inputs (role=INGREDIENT) × activity_outputs, joined by activity_id.

Supplier, Location  ← KEPT from v1 (CRUD + tests reused)
utils/units.py      ← KEPT from v1; ADD concentration unit family (store-only)
```

**Why provenance lives in the Activity, not a parent FK:** Combine (A + B → C) needs *many* parents
per child, which a single parent FK on the Item can't hold. A dedicated provenance table would also
just *duplicate* what the activity's inputs/outputs already record (a parent→child link is exactly
`input → output` for one activity). So lineage is **derived** from the Activity input/output
junctions — one source of truth, no drift. See §12.

---

## 3. Combine output identity — Option A (locked)

When a transform creates a NEW item (combine especially), that item MUST reference an Item Sheet
(the FK is non-null and load-bearing across every query/DTO).

- **Rule:** Combine (and any transform that mints a new identity) **requires the caller to pass
  `output_item_sheet_id`.** The user picks an existing sheet or creates one *before* the transform.
- The spec §6 "popup to create an item sheet for C" is a **frontend pre-step**, not a service concern.
  The service receives a valid sheet id; no auto-creation, no nullable sheet.

Rejected: auto-creating a "Mixture A+B" placeholder sheet (pollutes catalog); nullable sheet on Item
(breaks integrity everywhere).

---

## 4. Item lifecycle / status (locked)

Status enum: **`ACTIVE` / `EXHAUSTED` / `DISCARDED`** (extends the built `BatchStatus`, which had only
ACTIVE/DISCARDED).

`status` is a **real, persisted column** on Item (so lists/pickers filter/sort with a plain
`WHERE status = …`, no quantity math in queries — this is why it is stored, not computed-on-read).

**Recomputed on every save** from quantity, in one centralized guard (`item.recompute_status()`,
called before persist — §11b "centralize behavior"):

- `quantity > 0  ⇒ ACTIVE`
- `quantity == 0 ⇒ EXHAUSTED` — used up.
- **`DISCARDED` is user-set, terminal, and EXCLUDED from the recompute** — once a user discards an
  item it stays DISCARDED regardless of quantity. (Full discard latches it; partial discard leaves it
  ACTIVE because it was not fully discarded — see §10/§12.)

`ACTIVE ⇄ EXHAUSTED` is therefore **non-terminal**: if quantity ever returns above 0, the next save
flips EXHAUSTED back to ACTIVE automatically.

> ⚠️ **No v2 trigger raises an existing item's quantity** — every v2 transform only *decreases* an
> item's quantity (adding stock = a new `receive` item or a `combine` output, never a top-up). So the
> EXHAUSTED→ACTIVE reversal is **correct and future-proof but dormant in v2**: no v2 user action will
> actually fire it. The operation that would (inventory correction / `adjust`) is **deferred** — see
> Open Decisions.

"Used up" (EXHAUSTED) vs "thrown away" (DISCARDED) stays distinguishable for traceability (§12 rule 6).

---

## 5. Quantity & concentration enforcement (locked)

**Philosophy: trust the operator, but never let stock become physically impossible.**

- **ENFORCE (only):** consume / split / combine-from cannot pull more out of an item than it holds.
  Reuses the existing `validate_sufficient_quantity()`. No negative stock, ever.
- **ENFORCE: an activity input (either role, INGREDIENT or INSTRUMENT) cannot reference a `DISCARDED`
  item.** You can't consume from / use equipment that's been thrown away. (EXHAUSTED needs no separate
  gate — a qty-0 item already fails the non-negative check.) One cheap status guard on input resolution.
- **STORE, do NOT enforce:** concentration (initial/final/factor), combine output totals, declared loss,
  dilution math, whether outputs "sum correctly," unit compatibility across a transform.
- **Concentration** — store-only, identity-defining; full rules in **§17** (columns on Item, allowed on
  all unit types for now, change → new item). No C₁V₁=C₂V₂ checking. Concentration unit family added to
  `utils/units.py` for display only.

---

## 6. Serial-numbered non-consumables (locked)

- **One Item per physical serialized unit.** `serial_number` is a nullable field on Item.
- **`serial_number` is UNIQUE across all items, lab-wide** — a serial identifies one physical unit
  globally (not per-sheet). Constraint is **null-exempt** (partial unique index): consumables all carry
  `serial_number = null` and coexist freely; uniqueness applies only to non-null values.
- Consumable reagent: one Item, quantity in mL/g, `serial_number` null.
- Non-consumable instrument: one Item per unit, `quantity` null/1, `serial_number` set, status per unit.
- `use` activity references *a specific instrument unit* (the Item), not a pool.
- **UI affordance:** receiving N serialized units must support "create N items" in one action
  (not N manual forms) — **the bulk form collects the per-unit `serial_number` for each of the N items**.
  This is UI, not a model change.

---

## 7. What is kept vs. rebuilt from v1 (locked: "keep plumbing, rebuild model")

**KEEP (model-independent, already tested):**
- `utils/units.py` (unit conversion) — extend with concentration units.
- `Supplier` + `Location` entities and their CRUD services + tests.
- Audit-field pattern, `ModelWithUser`, gws_project structural patterns.

**REBUILD (entity layer + services touching it):**
- ItemSheet (was Material), Item (was Material_Batch), Reception (new), <- no new Reception, we use additional Activity columns
  Activity + activity_inputs + activity_outputs (reshaped — §12).
- All services that operate on those entities.

v1 docs in `../global/` describe the prototype model and are now historical reference, not the build target.

---

## 8. Reception type & transform-output origin (locked)

- **Reception is an ENTITY, not just an activity type.** A reception is a *container of items*
  (a delivery brings in N items sharing supplier/external_batch/date) — that is 1:N,
  whereas an Activity is 1:1 with the entity it acts on. Items point at one `reception_id`; shared
  delivery data lives once on the Reception, not duplicated across N rows.
- **Dual pattern:** Reception is *both* an entity (the structure — "what was this delivery and what
  came in it") *and* emits **one `receive` Activity per reception** (the timeline event — so receipts
  appear in the same chronological log as consume/move/split). That single receive activity has
  **0 inputs and 1..N outputs** (one output per created item — §12) and points back at the reception.
  - ⚠️ `receive` is the **only** activity type whose timeline row is not 1:1 with a single item — it
    represents the whole delivery. Every other activity is one item-centric event. This is fine: the
    Reception entity already carries the "these N belong together" grouping.
- **Reception.type:**
  - `RECEIVED` — from a supplier: `supplier_id` **required**, `external_batch` **required**.
  - `INTERNAL` — lab-made fresh stock: `supplier_id` null, `external_batch` optional.
- **Transform outputs (split/combine/dilute/concentrate) carry NO reception.**
  `Item.reception_id` is **nullable**. A derived item's origin is the **Activity that created it**
  (its input/output rows — §12), not a reception. (Forcing a reception on every transform output would
  create meaningless one-item receptions and blur "received from outside" vs "derived in-lab".)

---

## 9. Identifiers — sheet code, item code, item label, external_batch (locked)

There is **NO "batch label" / "internal batch number"** field on the Item. Grouping-by-delivery
is the `reception_id` FK (§8) plus the propagable `batch:` tag (§14); item identity is the structured
`code` below. The "batch" notion is the Reception's `external_batch` value, nothing more.

### ItemSheet.`code`
- **Exactly 4 characters**, charset `[A–Z0–9]`. **Unique, immutable.**
- Auto-**suggested** on the frontend from the sheet's name at creation (e.g. "Éthanol 99%" → `ETHA`),
  **editable before save**. If the suggestion is taken, the user must pick a different available 4-char
  code (NO 5-char fallback — the length is hard). **Cannot change once the sheet is created.**
- Serves as the prefix for item codes, so it MUST be unique (else item codes collide across sheets).

### Item.`code`
- **Unique, immutable, structured:** `{item_sheet.code}-{year}-{increment}` → e.g. `ETHA-2026-0007`.
- **Increment scoped per (sheet + year)** — `ETHA-2026-0007` = "7th ethanol item of 2026". Human-meaningful.
- **Increment = numeric `MAX(increment) + 1`** over existing items of that (sheet, year) — a *numeric*
  max, not lexical, so `9999 → 10000` is correct.
- **Increment zero-padded to minimum width 4** (`1→0001`, `42→0042`); **overflows naturally to 5+**
  digits past 9999 — only reachable if one sheet gets >9999 items in one year.
- **Generated on the BACKEND** at item creation. The DB unique constraint on `code` is the backstop:
  under concurrency the losing insert simply recomputes `MAX+1` and takes the next number. The
  frontend may show a best-effort preview, but the **backend assigns the authoritative value and the
  user is redirected to the real `code` after creation** (the preview may not match — acceptable).
- **Bulk receive** (§6): the N items are assigned **sequential** `MAX+1, MAX+2, …` within the one action.
- This is the **barcode / scan key** (§ barcodes) — printable as a barcode/QR; scans resolve to one item.

### Item.`label`
- **Free text, editable, NOT unique, optional.** The human note/name (e.g. "my prep for exp 12").
- Display can concatenate: `ETH-2026-0007 — my prep for exp 12`.

### Reception.`external_batch`  (renamed from v1/draft `external_lot`)
- **Required for RECEIVED**, optional for INTERNAL, **NOT enforced unique** — it's the supplier's value;
  suppliers reuse lot numbers and we don't control them. Record, don't police. A real column on
  Reception, not a tag.
- **When non-null, it is mirrored as a propagable `batch:<external_batch>` tag** on each item created by
  the reception (SYSTEM origin → locked; merges on combine) — see §14. Null `external_batch` → no batch
  tag. This is the *only* auto-tag at reception; there is no `reception:<id>` tag.

### Dropped
- The v1 "unique batch_number per material" rule and the entire "internal batch label" idea — superseded
  by `code` (unique by construction) + `reception_id` (grouping) + the `batch:` tag (genealogy). There is
  **no `batch_label` field anywhere** in v2.

---

## 10. Discard / lineage cascade (locked)

- **Discard does NOT cascade.** It soft-marks the target Item and is **quantity-bearing, can be partial**
  (see §12). Descendants are untouched.
  - **Partial** (discarded qty < remaining): `item.quantity` reduced, discarded amount recorded in
    `activity_inputs.quantity_contributed`, **status stays ACTIVE**.
  - **Full** (discarded qty = full remaining): `item.quantity → 0`, **status latches `DISCARDED`**
    (user-set, excluded from the §4 recompute).
  - **Frontend "discard all"** affordance pre-fills the discarded quantity with the full remaining
    amount so the user reaches the full-discard path without hand-typing it. UI convenience; the backend
    just sees a quantity. Keeping discard partial-capable is deliberate — it preserves the
    **partial-consume vs partial-discard** distinction (used productively vs wasted — §12 rule 6).
- **Activities (and their input/output rows) are NEVER deleted** — they are the history/audit and the
  source of lineage. A discarded item keeps appearing in past activities.
- **No "block discard if has children" rule** — soft-discard is safe; descendants keep their
  provenance via the preserved Activity records.
- Rationale: discarding a parent container doesn't make its aliquots vanish in real life; and with
  multi-parent Combine, cascading would destroy mixtures that still physically exist.
- ⚠️ Migration note: the built prototype's `Material_Batch` has a `parent_batch` self-FK with
  `on_delete="CASCADE"`. The v2 `Item` has **no parent FK at all** — provenance moves to Activity
  inputs/outputs (§12). Discard is soft-delete only, never a row cascade.

---

## 11b. Consumable & non-consumable share one table (locked)

- **One `Item` table and one `ItemSheet` table** for both consumables and non-consumables.
  `is_consumable` lives on the **Item Sheet** (intrinsic to *what the thing is*); items inherit it.
- **Why unified, not split:** the binding constraints are *relationships*, not fields —
  (1) a single Activity can reference both a consumed reagent and a `use`d instrument in the same
  experiment; (2) a Reception bundles reagents + instruments together; (3) the hierarchical inventory
  list shows everything in one tree. Splitting into two item tables would force polymorphic FKs on
  activities/receptions/lineage — exactly the pain v1's unification removed.
- **But the split is ENFORCED, not an informal flag:**
  - Centralize behavior in guard methods (`item.assert_can_consume()` / `assert_can_use()`),
    not scattered `if is_consumable` checks.
  - Validate field-coupling on save: consumable ⇒ quantity+unit required, serial null, can reach
    EXHAUSTED; non-consumable ⇒ serial-or-pool, quantity null/1, never EXHAUSTED.

### Deferred: instrument maintenance & calibration (planned post-v2)

Long-term, instruments will need maintenance/calibration: planned maintenance date, "check every N
months" recurrence, calibration records, certificates. This is a **recurring, future-dated, dated-history**
concern — a *different lifecycle* from inventory activities (which are always past/done).

- **It does NOT change the core table decision.** Instruments stay unified Items.
- It will be added additively, with **zero migration of the core model**, as:
  - a `maintenance_record` table (`item_id` FK, type CALIBRATION/MAINTENANCE/CHECK, due_date,
    performed_date, performed_by, result, certificate_file, recurrence),
  - optional maintenance attributes on the Item Sheet (calibration interval, requires_calibration),
  - optional `next_maintenance_due` on Item.
- **Do NOT fold maintenance into the Activity table** — maintenance has future/recurring/"due-vs-done"
  semantics that inventory activities lack.
- **Not in the first v2 release** — brainstorm not yet fleshed out (frequencies, notifications, overdue
  handling). Recorded here so the v2 model stays compatible with it.

---

## 11. Transforms in scope for first v2 release (locked)

All of: **Consume, Move, Relabel, Split, Dilute, Concentrate, Combine** (+ Receive, Use, Discard).
- Consume / Move / Relabel — mutate existing Item (inputs only, 0 outputs).
- Split / Dilute / Concentrate — 1 ingredient → new output item(s); Dilute/Concentrate record
  store-only concentration on the output.
- Combine — many ingredients → 1 new output; requires `output_item_sheet_id` (§3).

(Note: "aliquot" from v1 is just a `split` with one output in the v2 model — no separate type.)

---

## 12. Activity model — single N-to-N event (locked) ⭐

An Activity is one event that takes **0..N input items** and produces **0..N output items**.
Lineage/provenance is **derived** from these inputs/outputs — there is no separate lineage table.

### Tables

```
activities
├─ id (PK)
├─ activity_type ENUM(receive, consume, use, move, relabel, discard,
│                     split, combine, dilute, concentrate)
├─ description    TEXT, null
├─ note_id        VARCHAR, null      ← Constellab Note link
├─ from_location_id FK→locations, null  ← move only
├─ to_location_id   FK→locations, null  ← move only
├─ reason         TEXT, null         ← discard (why thrown away)
├─ notes          TEXT, null
├─ initial_concentration DECIMAL, null  ┐
├─ final_concentration   DECIMAL, null  │ ← dilute/concentrate ONLY; store-only audit (§17).
├─ concentration_unit    VARCHAR, null  │   NOT derivable (unlike loss), so stored explicitly.
├─ dilution_factor       DECIMAL, null  ┘
└─ + audit (created_by_id, last_modified_by_id, created_at, last_modified_at)
   NO reception_id (Item.reception_id is the link — §8).
   NO loss_quantity/loss_unit — loss is DERIVED: Σ(input qty) − Σ(output qty).
   (The concentration columns ABOVE are the one exception to "derive don't store" — see §17.)

activity_inputs            (things the activity took from)
├─ id (PK)
├─ activity_id  FK→activities
├─ item_id      FK→items
├─ role         ENUM(INGREDIENT, INSTRUMENT)
├─ quantity_contributed  DECIMAL, null   ← null for INSTRUMENT & for move/relabel
├─ unit_type    ENUM, null
└─ + audit

activity_outputs           (NEW items the activity created)
├─ id (PK)
├─ activity_id  FK→activities
├─ item_id      FK→items
├─ quantity     DECIMAL, null   ← snapshot at creation (audit; item.quantity = source of truth)
├─ unit_type    ENUM, null
└─ + audit
```

### Per-type cardinality (enforced in SERVICE layer, not schema)

| type | inputs (role) | outputs | quantity effect |
|------|---------------|---------|-----------------|
| `receive` | 0 | 1..N | creates items (Item.reception_id set); ONE activity per reception (§8) |
| `consume` | 1 INGREDIENT | 0 | item.qty −= input; status recompute → EXHAUSTED if 0 (used productively) |
| `use` | 1..N INSTRUMENT | 0 | none (reference only) |
| `move` | 1 INGREDIENT | 0 | none; from/to location on activity |
| `relabel` | 1 INGREDIENT | 0 | none |
| `discard` | 1 INGREDIENT | 0 | item.qty −= input (partial or full); latches DISCARDED if 0 (wasted); `reason` set |
| `split` | 1 INGREDIENT | 1..N | parent −= Σ outputs (mutate in place); → EXHAUSTED iff remainder=0 (§18) |
| `combine` | 2..N INGREDIENT (+0..N INSTRUMENT) | 1 | each input reduced by its contribution (→EXHAUSTED if 0); output created; needs output_item_sheet_id |
| `dilute` | 2 INGREDIENT (target+diluent) (+INSTRUMENT) | 1 | BOTH inputs reduced (target + diluent); output created w/ concentration |
| `concentrate` | 1 INGREDIENT (+INSTRUMENT) | 1 | input reduced; output created |

> **Input quantity rule (combine/dilute/concentrate):** each INGREDIENT input's `quantity_contributed`
> is decremented from that item, bounded by the §5 non-negative check (cannot contribute more than it
> holds). An input fully consumed → qty 0 → EXHAUSTED via the §4 recompute (same as `consume`). All input
> decrements + output creation happen in one atomic transaction.

> **Output item fields (split / combine / dilute / concentrate create new items):**
> `location_id` and `expiry_date` are **user-entered per output**; the frontend **pre-fills both from the
> source item** for split/dilute/concentrate (editable) and leaves them **blank for combine**.
> `storage_conditions` follows §19 off the **output's own sheet** (no transform-specific rule).
> `reception_id` is **null** for every transform output (§8) — including split children; delivery
> provenance survives as the propagated `batch:` tag (§14), not the FK. Outputs must be created with
> **qty > 0** (a 0-qty output is rejected) so EXHAUSTED only ever arises from reducing an existing item.

### Locked rules

1. **Lineage = derived query**, NOT a stored table:
   `parents(item) = activity_inputs WHERE role=INGREDIENT for activities that output item`;
   `children(item) = activity_outputs for activities where item is an INGREDIENT input`.
   No separate lineage table → no drift.
2. **No phantom items** (Grill 1): in-place actions (consume/move/relabel/use/discard) create
   **0 outputs**. A reduced/surviving input is just the mutated input — it does NOT also appear as
   an output. Only receive/split/combine/dilute/concentrate create `activity_outputs`.
3. **`role` separates ingredients from instruments** (Grill 3): INSTRUMENT inputs are recorded for
   traceability (`quantity_contributed=null`, item unchanged) but are **excluded from lineage** —
   a centrifuge is not a "parent" of the sample.
4. **item.quantity = source of truth** (Grill 2): junction `quantity` columns are an immutable
   per-event audit copy. NOT event-sourcing — current stock is read off the item, not replayed.
   Both written in one atomic transaction.
5. **Loss is derived, not stored**: process loss in combine/concentrate = `Σ(inputs) − Σ(outputs)`,
   computed for display. No loss columns.
6. **consume vs discard distinction**: both reduce quantity, separated by `activity_type` and the
   status reaching 0 drives (consume → recompute sets EXHAUSTED = used productively; discard → latches
   DISCARDED = wasted). Whole-item discard is just the case where discarded qty = full qty. Status is
   the **stored, recomputed-on-save** column (§4) — EXHAUSTED is recomputed from quantity, DISCARDED is
   the user-set latch excluded from recompute.
6b. **An activity input (either role) cannot reference a `DISCARDED` item** (§5) — no consuming from /
   using thrown-away stock. Validated on input resolution.
7. **`use` is not special machinery — it's the INSTRUMENT-input mechanism, degenerate case**:
   - **Standalone `use`** ("I used the centrifuge today") = an activity with 1..N INSTRUMENT inputs,
     **0 INGREDIENT inputs, 0 outputs, no quantity effect** (instruments never decrement).
   - The **same** INSTRUMENT inputs can also ride on any transform ("track the instrument I used while
     combining") — consume/split/combine/dilute/concentrate may carry INSTRUMENT inputs alongside their
     INGREDIENT inputs.
   - So `use` is just "an activity whose only inputs are instruments." It stays a first-class
     `activity_type` (selectable standalone and in a Note) but needs no special code path.
   - **A `use` requires ≥1 INSTRUMENT input** (0-instrument `use` is rejected at the service layer).
     More generally, an activity with **0 inputs AND 0 outputs is rejected** — except `receive`, which is
     0-input by design (it creates outputs).
   - **INSTRUMENT inputs are NON-CONSUMABLE only** (validation: an INSTRUMENT-role input must reference
     a non-consumable item). A consumable that gets used is a `consume` *with a quantity*, never a `use`
     — this keeps the line clean: `use` = non-consumable reference, `consume` = consumable depletion.

---

## 13. Units — dimension locked, scale free (locked)

The user may change a quantity's **scale** within a dimension (mL ↔ L ↔ µL) but **never** its
**dimension** (volume → mass is forbidden). This is enforced **by construction**, not runtime checks:

- **`unit_type` (the dimension: volume/mass/length/count) lives on the Item Sheet and is authoritative.**
  It is the definition of *what the thing is measured in*.
- **`unit_type` is also stored on the Item as a write-once copy** of the sheet's dimension, set at item
  creation, never independently editable. *Why duplicated:* avoids a join to the sheet on every
  quantity query/list. Safe because it is immutable and fully derived from the sheet (no drift).
- **An Item Sheet's `unit_type` is IMMUTABLE once any Item references it.** You cannot turn a volume
  reagent into a mass reagent once physical items exist. This is the rule that keeps the item's cached
  copy from ever drifting.
- **Quantities are stored in the BASE unit** of the dimension (L, kg, m, count) — unchanged from v1.
  Changing the displayed scale (mL→L) never changes the stored number.
- **No `display_unit` is stored.** The frontend auto-formats to a human-readable scale (50 µL, not
  0.00005 L) via `units.py` `format_value`. The user's chosen scale is computed each time, not
  persisted per item.

Net effect — "can't change L to g" is impossible because:
(1) the item's `unit_type` is write-once from the sheet, and (2) the sheet's `unit_type` is frozen
once items exist. Scale changes are frontend-only and touch no schema.

---

## 14. Tags — gws_eln-local, propagable, origin-tracked (locked)

Tags are modeled on gws_core's `EntityTag`/`Tag`/`TagOrigins` system, but **gws_eln defines its own
tables and value classes** because gws_eln and gws_core live in **separate databases** — gws_core's
`EntityTag` has a DB-level FK to `gws_tag_value`, which cannot cross databases, and ELN items aren't
in core's `TagEntityType`. So we **reuse the design, not the tables**.

### Storage (own table, own DB)

```
ItemTag  (gws_eln DB — modeled on gws_core EntityTag)
├─ item_id       FK → items   (same DB — real FK works)
├─ tag_key       CharField
├─ tag_value     CharField
├─ value_format  ENUM
├─ origins       JSONField    ← SAME JSON shape as gws_core TagOrigins (see "aggregate later")
├─ is_propagable Boolean
└─ + audit
   NO is_removable column — removability is DERIVED from origin (see below).
```

### Value classes — duplicate, don't import (for now)

- **Duplicate** `TagOrigin` / `TagOrigins` (the multi-origin merge engine — `merge_origins`,
  `is_user_origin`, etc.) and the used parts of `Tag` (validate/parse/value-format) into gws_eln.
- **CRITICAL:** keep the serialized JSON shape **byte-for-byte identical** to gws_core's, so
  "aggregate later" is a delete-and-import, not a data migration. (Tech-debt item below.)
- **Write fresh** an ELN-specific origin enum — do NOT reuse core's `TagOriginType` (its values
  TASK/S3/SCENARIO_PROPAGATED… are meaningless here):

  ```
  ItemTagOriginType:
    USER    → origin_id = user id    (a person added/typed this tag)
    ITEM    → origin_id = item id    (propagated from this source item — genealogy)
    SYSTEM  → origin_id = sys user   (auto-generated, no human; e.g. batch tag)
  ```
  Events (activities, receptions) are NOT origins — the *event* that created a tag is recoverable
  from the §12 Activity graph and the `reception_id` column. Origin = *source of the tag*, never the
  mechanism.

### Propagation — LIVE downward, mirroring gws_core (the A+B→D genealogy case)

Propagation behaves **exactly like gws_core's tag propagation/origin engine** (`TagOrigins`:
`add_origin`/`merge_origins`/`remove_origins`, `is_user_origin`). gws_eln reuses the *design* (its own
DB tables, §14) but the propagation semantics are gws_core's, verbatim.

- **Downward only, never upward.** A propagable tag flows to **descendants** (INGREDIENT-input lineage);
  it **never affects parents**. Non-propagable tags do NOT flow. INSTRUMENT inputs never propagate
  (they're not lineage parents).
- **LIVE, two triggers:**
  1. **At derivation** — on any activity with outputs (split / combine / dilute / concentrate), each
     `is_propagable` tag on each INGREDIENT input propagates to each output.
  2. **On tag add/remove** — adding or removing a propagable tag on an item **re-walks that item's
     existing descendants** and applies the change. So tagging an item that *already* has children
     pushes the tag down to them; untagging pulls it back. **Synchronous, one transaction,
     descendants-only.** (This is the cost OD#1 once flagged — explicitly accepted: live downward
     propagation, not a point-in-time snapshot.)
- **Origin on the descendant = the IMMEDIATE source item** (ITEM origin, not the whole chain). Full
  genealogy is reconstructed by walking the chain + the §12 Activity graph.
- **Same key:value landing twice → merge origins** (union, `TagOrigins.merge_origins`). Example: A
  `batch:T` (origin ITEM:A) and B `batch:T` (origin ITEM:B) combined into D → D has ONE `batch:T` tag
  with origins {ITEM:A, ITEM:B}. (`batch:T` collides legitimately because `external_batch` is not
  unique — §9.)
- **Merge-aware removal** (`TagOrigins.remove_origins`): removing the tag at source A removes **A's
  origin** from each descendant (`remove_origin(ITEM, A)`). The tag **survives** on a descendant while
  ≥1 origin remains (e.g. D keeps `batch:T` via {ITEM:B}); it is **deleted from the descendant only when
  its origin set becomes empty** (`is_empty()`).

### Removability — derived from origin (no flag); delete only at the root

- A tag is **removable IFF its origins are user-only** (`TagOrigins.is_user_origin()`) — i.e. **only at
  its root**, the item where a user added it. SYSTEM and ITEM origins → **locked** (not removable).
  Enforced in one place: `ItemTagService.remove_tag()` raises if `not origins.is_user_origin()`.
- You **cannot delete an inherited (ITEM-origin) tag directly on a descendant**; it is removed
  **transitively** by deleting it at the root (which triggers the merge-aware removal above and pulls
  the origin out of every descendant).
- gws_core's **override rule** holds: `add_origin` **replaces a user origin when an automatic origin is
  added**, and refuses to add a user origin once origins are automatic. So a tag is effectively *either*
  user-originated *or* automatic — the removable/locked split is clean.

### Batch-provenance tag (the ONLY auto-tag at reception)

- At reception, **when `external_batch` is non-null**, a **propagable `SYSTEM`-origin `batch:<external_batch>`
  tag** is auto-created on each received item → therefore **non-removable** by the derived rule above.
  Null `external_batch` (only possible for INTERNAL) → no batch tag. **There is no `reception:<id>` tag** —
  this `batch:` tag is the single auto-tag.
- The tag's value is the supplier's `external_batch`, which **legitimately collides** across receptions
  (suppliers reuse lot numbers; not unique — §9). That is exactly why the merge example above
  (`batch:T` from A + B → merged origins) works: two items sharing a batch value combine into one merged
  `batch:` tag with both ITEM origins.
- The **`Reception` entity (§8) and `Item.reception_id` remain authoritative** for "which delivery did
  this item come from." The *tag* is the genealogy mirror that **propagates through activities** and
  accumulates ITEM origins on combine — so a derived item D made from items of two batches carries both
  batch tags (or one merged tag if the batch values are equal). Entity/FK = "where it came from";
  tag = "trace that provenance across the lineage."
- (There is no `batch_label` column anywhere — see §9.)

### Consequence (intended)

- Propagation can **lock a previously-removable tag on a descendant**: a USER tag on A (removable on A)
  becomes an ITEM-origin tag on D after combine/split (locked on D). Removable at the source, traced
  at the descendant. This is intended — on D it is inherited genealogy, not a free annotation.
- **With LIVE propagation this lock-flip can now happen after the fact**, not only at derivation: if a
  user adds a tag directly on D (USER, removable) and the *same* tag later propagates into D from a
  parent, gws_core's override rule replaces D's user origin with the incoming ITEM origin — D's tag
  **silently becomes locked**. This is gws_core's literal behavior and we mirror it without divergence.

---

## 15. Notes integration (locked)

The prototype is already **Note-aware**: a `notes/` module, `ElnNoteService`, a Reflex
`/notes/[note_id]` page, and `RichTextBlockMaterialActivity` let activities be created from inside a
Note block. v2 keeps and extends this.

### Any transform can originate in a Note — and it's free in the model

- **A Note is just a *source* of an activity, never a different kind of activity.** Creating a
  combine/dilute/split/consume from a Note block is the **same §12 service call** as doing it in the
  standalone app — the *only* difference is `Activity.note_id` is set. No "note activity" type, no
  separate logic. The locked §12 model already supports every transform from a Note with zero change.
- **One shared form component per transform**, launched in BOTH hosts (standalone app + from a note).
  Do not build two combine/dilute forms — they would drift. (Frontend-architecture rule for Phase 2.)
- **Form = shared modal/dialog; note block = reference-only renderer.** The prototype's
  `RichTextBlockMaterialActivity` already stores **only `activity_id`** — the activity is created via the
  §12 service/API **before** the block is inserted. So in the note host the transform form is a **modal
  launched from the note** (toolbar / slash-command), not embedded in the block; it calls the **same §12
  service** as the standalone app, the only difference being `note_id` is passed. The block then holds
  the resulting `activity_id` and renders it. This is what makes §15's "deleting a block only unlinks"
  true — the block never owned the form or the activity.
- `Activity.note_id` nullable: set when the action originated in a Note, null when done in the app.

### Note block = a view onto an activity, NOT its owner

- **Deleting or undoing (Ctrl+Z) a note block UNLINKS the activity** (clears `note_id` / removes the
  block's display). It **NEVER** mutates or reverses inventory. Consistent with §10/§12 (activities are
  immutable history; outputs may already have descendants).
- **Reversing a real transform = a compensating activity** (e.g. discard the bad output), not history
  deletion.
- ✅ This resolves the TODO.md bug ("Ctrl+Z can't restore a deleted activity"): the activity is never
  deleted on block removal — only unlinked.

### Block renderer must render N inputs → M outputs (rebuild required)

- The prototype's `RichTextBlockMaterialActivity.to_html()` / `to_markdown()` render the **v1 model** —
  they read a single `activity.batch` (`activity.batch.material.name`, `activity.batch.batch_number`,
  `activity.get_pretty_quantity()`). **This breaks under §12**, where an activity has **0..N inputs and
  0..N outputs** and no single `batch`.
- **v2 rebuild:** the renderer reads `activity_inputs` / `activity_outputs` (§12) and renders
  **`{inputs} → {outputs}`** — e.g. `Combine — Ethanol (ETHA-2026-0007, 5 mL) + Buffer (BUFF-2026-0003,
  5 mL) → Mixture (MIX-2026-0001, 10 mL)`. Degenerate cases render cleanly: in-place actions
  (consume/move/relabel/use/discard) have 0 outputs → render inputs + effect; `receive` has 0 inputs →
  render outputs. INSTRUMENT inputs shown distinctly from INGREDIENT inputs.
- This is the TODO.md item "Improve Activity block to_html to look like the JS component" — now a
  **model-driven rebuild**, not a cosmetic tweak.

### Tags stay split by entity database (confirms §14)

- **Note** tags = gws_core `EntityTag` (Notes live in gws_core's DB — the prototype already tags them
  via `EntityTagList(TagEntityType.NOTE, ...)`).
- **Item** tags = gws_eln `ItemTag` (§14, gws_eln's DB).
- The activity↔note link is the **`note_id` column** on the activity — never a shared tag. We never try
  to unify item-tags and note-tags across the two databases.

---

## 16. Hierarchical / lineage display (locked)

### Main inventory list — flat table

- The primary item list is a **flat table** — NO nesting.
- Item code, label, location, quantity, expiry, status are **sortable/filterable columns**.
- **No reception / external-lot column.** Delivery provenance is shown via **tags** (the `batch:` tag,
  §14, plus any others) — which avoids the "empty for derived items" inconsistency (transform outputs
  have `reception_id = null` but carry the propagated `batch:` tag). Provenance is uniform across
  received and derived items because it lives in the tag, not a column.
- Grouping/hierarchy is *not* the spine of the list; you filter (including by tag), you don't expand.

### Lineage detail — interactive DAG graph, focused on the current item

- The item detail view shows lineage as an **interactive node-and-edge graph centered on the current
  item**, ancestors and descendants both visible.
- **It is a DAG, not a tree** — and the graph renders that honestly:
  - **Up (ancestors):** Combine outputs converge — a node can have multiple parents (D made from A1 + B).
  - **Down (descendants):** Combine also *merges going down* — an output M can be made from the current
    item D *and* another item E, so M is a merge node in D's descendant view too.
  - A graph shows both merges and splits as real converging/diverging edges — no "tree + annotation"
    hacks needed. This is why we chose a graph over indented trees: the data is a DAG and a graph is the
    only representation that shows merges/splits truthfully.
- **Central feature with budget** — traceability is a headline goal of the ELN, so the graph gets real
  frontend investment.
- **No depth limit** — lineage depth stays small in practice.
- Leaves of the ancestors direction = received/internal items (show the reception + `batch:` tag);
  leaves of the descendants direction = items not yet used further.

### Backend: schema unchanged, but a new traversal route is required

- **The data model / schema is unchanged** — no lineage table, no new columns. Lineage is **derived**
  from the §12 Activity junctions. *But this is NOT "purely a frontend concern":* the frontend cannot
  recurse the DAG without N round-trips, so a **new read-only backend route returns the graph**
  (nodes + edges for a focus item, both ancestors and descendants) in one call. Schema unchanged;
  **service/route added.**
- Both directions are derived from the **§12 Activity graph** by recursion:
  - ancestors(X) = INGREDIENT inputs of activities that output X, recursed;
  - descendants(X) = outputs of activities where X is an INGREDIENT input, recursed.
- Cycles are impossible (time-ordered), so recursion terminates. **A visited-set is mandatory** to
  dedup diamond merges (A→B, A→C, B→D, C→D must visit D once, not twice) — without it a diamond DAG
  double-counts nodes/edges.
- **Shared traversal:** the descendant walk is the SAME walk live tag propagation needs (§14). Factor
  the ancestor/descendant traversal into **one shared service** (cycle-safe, visited-set) used by both
  the lineage-graph route and `ItemTagService` propagation — one implementation, no drift.
- **No hard depth limit** (depth stays small in practice — §16), but breadth is unbounded (combine
  fans in, split fans out); the visited-set keeps a busy subgraph from being re-walked.

### Deferred to its own epic (LAST epic)

- Graph library choice, layout, pan/zoom, node styling, click-to-navigate, and lazy-expand are decided
  **at implementation time**, in a dedicated lineage-graph epic at the end of v2. This decisions doc
  fixes *what* the view is (interactive DAG, current-item-focused, no depth limit); the *how* is the
  epic's job.

---

## 17. Concentration — identity-defining, stored on Item (locked)

### Storage

- **`concentration` + `concentration_unit` are nullable columns on Item** — the item's *current*
  concentration, readable directly in lists/pickers/detail (no walking activity history).
- Null for items with no concentration (instruments, solids, tip boxes, …).
- **Allowed on ALL unit types for now** (no dimensional restriction — a mass item *may* carry a
  concentration). May revisit if it causes confusion. Still **store-only** (§5) — never computed/enforced.
- The concentration unit family (M, mM, µM, ng/µL, µg/mL, U/µL, cells/mL, …) is added to `units.py`
  as a **display/recording list only — NO conversion** in v2. `concentration_unit` is a single string
  column; there is **no `concentration_unit_type`** (no molar/mass-vol/activity/count-vol kind recorded)
  and no mM↔µM or molar↔mass interconversion. (Molar↔mass needs molecular weight — out of scope.)
  Defer a richer concentration-unit model if heavy filtering/conversion is later needed (additive).

### Concentration is IDENTITY-DEFINING (the key principle)

An item's concentration is **immutable for that item's lifetime.** Changing concentration does **not**
mutate the item — it **creates a new item** (the output of a dilute/concentrate activity, linked by the
§12 graph). This is *why* dilute/concentrate create outputs while consume mutates in place:

| Property | Mutable in place? | Change creates a new item? |
|----------|-------------------|----------------------------|
| quantity | ✅ yes (consume/split reduce it) | no |
| location | ✅ yes (move) | no |
| label    | ✅ yes (relabel) | no |
| **concentration** | ❌ **no** | ✅ **yes — via an activity output** |

So dilute/concentrate are not "edit the concentration" ops — they are "consume volume from the input,
create a new output item at the new concentration."

### Per-activity behavior

- **Dilute:** has **TWO** INGREDIENT inputs — the **target** and the **diluent** — and **both are
  reduced in place** (the target loses the volume drawn off, the diluent loses the volume added; each
  bounded by the §5 non-negative check; either may hit 0 → EXHAUSTED via §4). Neither input's
  concentration changes (concentration is identity-defining, §17). A **new output item** is created at
  the user-entered (store-only) new concentration; its **quantity is user-entered, never computed** by
  summing target+diluent (§5). The diluent's dimension is **not enforced** (deliberate — §5/§23). The
  activity records `initial_concentration` → `final_concentration` + `dilution_factor` as immutable
  store-only audit columns (§12) — these are NOT derivable, so they are stored explicitly.
- **Concentrate:** one INGREDIENT input, reduced in place; a new output item created at the user-entered
  new (higher) concentration, user-entered quantity. Same store-only `initial/final_concentration` +
  `dilution_factor` audit columns on the activity (§12).
- **Split / aliquot:** output **inherits the parent's concentration unchanged** (concentration is
  intensive — splitting volume doesn't change it). Copy the column.
- **Combine:** output concentration is **user-entered or null** — never computed (no C₁V₁=C₂V₂ math, §5).
- **Consume / move / relabel / discard:** concentration untouched.

---

## 18. Split remainder — source mutated in place, no "mode" (locked)

When splitting 100 mL into 30 + 30, the leftover 40 mL stays in the **source item, reduced** — it is
NOT a new item.

- A split only moves **quantity** around; it does not change concentration (children inherit it, §17).
  By the §17 identity rule, a pure quantity change **mutates in place** — so the source survives reduced,
  same identity / lineage / tags / location. Outputs are only the genuinely-new aliquots.
- The spec's "configurable full vs partial split" is **NOT two modes** — it collapses to one mechanism:
  - **partial** (Σ outputs < source): source survives reduced.
  - **"full"** (Σ outputs = source): source quantity hits 0 → status recompute sets **EXHAUSTED** (§4).
    No special "close-and-replace" path; "full split" is just the remainder-is-zero case.
- Making the 40 mL leftover a "new item" is rejected — it would mint an item for a pure quantity change
  (violating §17) and orphan an EXHAUSTED parent for no identity reason.

---

## 19. Locations flat; Storage Conditions is an item attribute (locked)

- **Locations stay FLAT** in v2 (name + description), as in the built prototype. No nesting.
  - To imply nesting, encode it in the name ("Freezer-80 / Shelf A1") — pragmatic, zero rebuild.
  - **Hierarchy deferred to post-v2** — additive `parent_location_id` on Location when needed; does NOT
    touch items. (Already in v1's Phase-2 list as "richer location hierarchies.")
- **Storage Conditions is NOT a location level — it's a separate item attribute.** "-20°C" is a
  *property* (how it's kept), not a *place* (where it is) — the same condition can exist in many
  freezers. Conflating them is the trap we avoid.
  - Stored as a **simple string/enum field**, **default on the Item Sheet, overridable on the Item**.
    Not a new entity, not forced through tags. (Can graduate to a controlled list later if heavy
    filtering-by-condition emerges — additive.)

---

## 20. Files / attachments (locked)

Files attach to **Item Sheets** ("Files"), **Receptions** (Certificate of Analysis), and **Items** —
all three are in v2 scope. The prototype models none. Design reuses gws_core's filestore *mechanism* but
keeps records in the gws_eln DB (consistent with the cross-DB rule used for tags §14).

### Storage split

- **gws_eln registers its OWN `LocalFileStore` instance** (dedicated to ELN), created once at brick
  init / migration. `LocalFileStore` is itself a gws_core-DB model (`gws_file_store` table) whose bytes
  live at `<file_store_dir>/<store_id>/…` — so a dedicated store keyed by its own id **segregates ELN
  bytes** from task/resource files automatically. The ELN store's **id is recorded in ELN config** so
  the file service knows which store to use.
- **Use the store's BYTE operations only** (`add_from_temp_file` / `add_node_from_path` /
  `delete_node_path`) — **do NOT persist `FsNodeModel` rows.** The `ElnAttachment` row (gws_eln DB) is
  the **sole record**; gws_core tracks nothing about ELN files beyond the store row + the bytes on disk.
- **No DB-level cross-DB FK.** The attachment→bytes link is a **logical** reference (two plain columns,
  below) resolved through the gws_core filestore **API**, never a Peewee FK or join. The entity→attachment
  link is a real same-DB FK (both in gws_eln).

### One table — `ElnAttachment` (gws_eln DB)

```
ElnAttachment
├─ id
├─ entity_type   ENUM(item_sheet, reception, item)   ← polymorphic, attach to anything
├─ entity_id     FK → that entity (same DB — real FK)
├─ filestore_id  ← plain id of the ELN LocalFileStore (NOT an FK — store lives in gws_core's DB)
├─ path          ← node path of the bytes within that store
├─ filename, size, content_type
├─ label         (e.g. "Certificate of Analysis")
└─ + audit
```

- **One table, not two.** No separate `ElnFile` — the file/link split is only justified by sharing one
  file across many attachments, which we DON'T need. One row = one file attached to one entity.
- **No file sharing / refcounting.** Re-attaching the same document = re-upload. Simplest lifecycle.

### Lifecycle — gws_eln owns the bytes

- Because bytes live in our own filestore (not `FsNodeModel`), **gws_eln's file service owns full
  lifecycle**: deleting an `ElnAttachment` row **also deletes the bytes** (`store.delete_node_path(path)`);
  deleting an entity cascades to its attachments → bytes. (Skipping this = orphaned files leaking on disk.)
- **Two-resource ordering (not a single DB transaction):** the record is in gws_eln's DB, the bytes are
  on disk in gws_core's store — they **cannot** be one atomic transaction. Order: **delete the DB row
  inside the gws_eln transaction, then delete the bytes after commit.** A crash between the two leaves
  **orphaned bytes, never a dangling record** — the safe failure direction (a record pointing at missing
  bytes would error on read; orphaned bytes are merely disk waste). `delete_node_path` is **idempotent**
  (it no-ops if the path is already gone), so a retry/cleanup sweep is safe. (A periodic orphan-bytes
  sweep is a possible post-v2 nicety — not required for v2.)

---

## 21. Roles / permissions — narrative only (locked)

- The role names in `specs.md` ("Quality Team member", "Lab Technician") are **narrative** — they
  describe *whose workflow* a feature serves. v2 enforces **NO in-app RBAC.**
- **Any authenticated Constellab user can perform any action** (as the prototype already does via
  `CurrentUserService`). Coarse "can you reach this app at all" is left to Constellab's existing auth.
- **Accountability, not authorization:** the audit fields (`created_by_id` / `last_modified_by_id` on
  every table) record *who did what* — you'll know the Technician received the batch; you just won't
  *prevent* a non-Technician from doing it.
- **Real RBAC deferred to post-v2** — additive permission-check layer over the services; **no data-model
  impact**, so deferring is free. (Already in v1's Phase-2 list.)

---

## 22. Migration / existing data — none (locked)

- **No prototype data must survive.** The old `material` / `material_batch` / `activity` tables and their
  rows are **dropped**; v2 builds a **greenfield schema**.
- **No migration script, no old→new mapping.** "Throwaway v1" (§7) is literal end-to-end: code *and*
  data. This is safe because the prototype DB holds only dev/test data nobody depends on.
- Confirms §7 fully: keep the plumbing (units.py, Supplier/Location, patterns), rebuild the model on a
  clean database.

---

## 23. Cross-dimension transforms — not enforced (locked)

The spec's "Combine must not be allowed across incompatible units" assumed combine *sums* inputs. Our
model never sums across inputs (§5 store-only), so the constraint dissolves. Dimension rules are
per-transform, and mostly moot:

- **Combine:** inputs **may be any dimension** (dissolve 5 g powder into 10 mL buffer is valid). Each
  input is consumed in its own unit (non-negative check only, §5); the output is a new item whose
  dimension/quantity come from its declared item sheet (§3, §13) and user input — never computed by
  summing inputs. **No same-dimension enforcement.**
- **Split:** children **inherit the parent's dimension** — automatic/structural, since a split child
  inherits the parent's item sheet → its `unit_type` (§13). Not a runtime check.
- **Dilute / Concentrate:** **no dimension enforcement** — store-only, trust the operator, consistent
  with §17 (concentration allowed on all unit types). We do NOT restrict these to volume-only.
- **Consume / Move / Relabel / Use:** single item, no second dimension in play.

Net: the only dimension "rule" is the structural fact that split children inherit their parent's
dimension. Everything else is unconstrained — matching the §5 "enforce only physically-impossible
(negative stock), store everything else" philosophy.

---

## Open Decisions (deferred — recorded so they're not lost)

1. **Tag inheritance — RESOLVED by §14 (live downward propagation).** Propagation rule, origins, merge,
   removability all locked, mirroring gws_core's engine. **The back-propagation question is now
   answered YES (reversing the earlier recommendation):** propagation is **live**, not point-in-time —
   adding/removing a propagable tag on an item re-walks its existing descendants synchronously. Tagging
   an item that already has children pushes the tag down; untagging pulls it back (merge-aware: survives
   while ≥1 origin remains). The full-descendant-walk cost on every tag edit is explicitly accepted.

   **Tech debt (§14):** `TagOrigin`/`TagOrigins`/`Tag` are DUPLICATED from gws_core into gws_eln with
   identical JSON shape. Aggregate later (delete the copy, import from core) once a cross-DB-safe shared
   package exists. Keep the JSON shape identical until then so aggregation stays a code move, not a
   data migration.

2. **Refresh / concurrency (Phase 2 NFR — invariants locked, mechanism deferred).** Detail & list views
   must reload data on focus or after any action. The *mechanism* is the Reflex state layer (Phase 2),
   but the locked **invariants** (because the model now mutates rows beyond the one acted on) are:
   - **Re-fetch from the backend after any mutating action — never patch view state optimistically from
     the form's local values.** The backend is authoritative for the assigned `code` (§9 MAX+1, may
     differ from the frontend preview), the recomputed `status` (§4), propagated tags (§14), and derived
     loss/lineage (§12).
   - **A single action can change rows the view did NOT directly act on:** live tag propagation re-walks
     descendants (§14); multi-input/output transforms (combine/split/dilute) touch several items at once
     (§12); a consume/split to 0 flips `status` and must drop the item from `status=ACTIVE` pickers (§4).
     So views **re-fetch the affected set wholesale** (simplest correct default: re-run the current
     list/detail query after any action), not just the one acted-on row.
   - **On focus / navigation, re-fetch** — this covers *other users'/tabs'* changes (the concurrency
     already accepted in §9). This is the concrete fix for the TODO.md bug "create activity on a batch,
     open its detail page, not refreshed."
   - (The Ctrl+Z/undo half is RESOLVED — see §15: note-block deletion unlinks, never deletes the
     activity or reverses inventory.)

3. ~~Default unit per item sheet vs. per item.~~ **RESOLVED — see §13.** Dimension is owned by the
   sheet (immutable once items exist) and cached write-once on the item; scale is a frontend-only
   concern; no display unit stored.

4. **Inventory quantity correction / `adjust` op — DEFERRED to post-v2.** v2 has **no operation that
   raises (or directly sets) an existing item's quantity** — every transform only decreases it (adding
   stock = a new `receive` item or a `combine` output). Consequence (§4): the `EXHAUSTED → ACTIVE`
   reversal is specified and future-proof but **dormant in v2** — no v2 action can fire it. A future
   `adjust` activity (1 INGREDIENT input, 0 outputs, sets a new absolute quantity up or down → status
   recompute) is the realistic home for stock recounts/corrections and would activate the reversal. Not
   in v2 (not yet fleshed out: who may adjust, reason codes, audit expectations). Recorded so the
   non-terminal status rule isn't mistaken for a missing trigger.

5. ~~`use` with zero instrument inputs / empty activities.~~ **RESOLVED — see §12 rule 7.** A `use`
   requires **≥1 INSTRUMENT input**; any activity with **0 inputs AND 0 outputs is rejected** at the
   service layer (except `receive`, 0-input by design). Enforced in the §12 service-layer cardinality
   checks.
