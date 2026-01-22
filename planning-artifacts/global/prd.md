stepsCompleted: ["step-01-init", "step-02-discovery", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish", "step-e-01-discovery", "step-e-02-review", "step-e-03-edit"]
inputDocuments:
	- /lab/user/_bmad-output/planning-artifacts/product-brief-user-2026-01-20.md
workflowType: 'prd'
workflow: 'edit'
project_name: user
user_name: Nour
date: 2026-01-20
lastEdited: 2026-01-21
editHistory:
	- date: 2026-01-21
	  editor: Ben
	  changes: "Major data model refactoring - unified Materials/Instruments into Materialx entity; introduced Materialx_Batch as physical instances; aliquots now multi-level without restriction; added Supplier and Location CRUD; differentiated consumable (decrement) vs non-consumable (usage reference) actions"
documentCounts:
	productBriefs: 1
	research: 0
	brainstorming: 0
	projectDocs: 0
classification:
	projectType: web_app
	domain: scientific
	complexity: medium
	projectContext: greenfield
workflowNotes:
	step-03-success: "Skipped per MVP brief; success criteria retained from product brief."
	step-06-innovation: "Skipped — incremental MVP integration with Constellab Notes."
---

# Product Requirements Document - user

Author: Nour
Date: 2026-01-20

## Terminology Clarifications

### Core Entities

**Material:** Generic material definition (chemical, instrument, consumable, equipment, etc.). Defines what the material is, including a consumable flag to indicate whether it depletes with use.

**Material Batch :** Physical instance of a material with supplier reference, location assignment, and quantity tracking. Represents actual stock in the lab. Each batch must be assigned to a location (default: "labo" if not specified).

**Aliquot:** A Material Batch derived from a parent batch. An aliquot references its parent via parent_batch_id. Multi-level aliquots are supported without depth limit—an aliquot can itself be the parent of another aliquot.

**Consumable vs Non-Consumable:** Determines action behavior:
- **Consumable:** Quantity decrements on usage (e.g., reagents, samples).
- **Non-Consumable:** Usage is recorded as a reference without quantity change (e.g., instruments, equipment). Non-consumable usage references are captured only in Note-linked actions (not in standalone batch management).

**Fournisseur (Supplier):** Supplier entity with full CRUD operations. Optional when creating batchs.

**Emplacement (Location):** Location entity with full CRUD operations. Every batch must be assigned to a location; default location is "labo" if not specified.

## User Journeys

All actions are available to any user in MVP; there are no roles or bulk operations.

### 1. Material & Batch Management (All Users)

**Material Definition:**
- Create material with name, description, and consumable flag
- Edit material metadata
- View material catalog
- Delete unused material definitions

**Batch Operations:**
- Create batch: select material, optional supplier, assign location (default: "labo")
- View batch details (material reference, supplier, location, quantity, parent batch if aliquot)
- Increment batch quantity (receiving additional stock)
- Decrement consumable batch quantity (usage or removal)
- Move batch to different location
- Delete empty or obsolete batchs

**Aliquot Creation (Batch Derivation):**
- Create aliquot from parent batch (creates new batch with parent_batch_id)
- Multi-level aliquots: create aliquot from aliquot without depth restriction
- Aliquot inherits material reference from parent but tracks independent quantity and location

**Supplier & Location Management:**
- CRUD suppliers: create, edit, view list, delete unused
- CRUD locations: create, edit, view list, delete unused
- Default location "labo" assigned if location not specified on batch creation

### 2. Note-Linked Inventory Actions (All Users)

**Within Constellab Notes:**
- Open custom Reflex inventory tool from Note context
- Select batch (not material directly) from available inventory
- Perform action based on consumable flag:
  - **Consumable batch:** Decrement quantity with amount and unit
  - **Non-consumable batch:** Record usage reference without quantity change
- Link action to Note with batch details: material name, batch number, supplier, quantity used, units
- Note captures traceability: material, batch, aliquot parent chain (if applicable), quantities, units

### Journey Requirements Summary

- **Material & Batch Management:** Create materials and batchs separately; increment/decrement/move batchs; create multi-level aliquots; manage suppliers and locations with simple CRUD
- **Note Integration:** Reflex tool embedded in Constellab Notes; batch selection and action (consumption or usage reference); updates inventory and links to Note
- **Roles/Permissions:** None in MVP; anyone can perform actions
- **Constraints:** No bulk actions; no alerts/reporting/compliance in MVP; single lab instance; no lineage visualization in MVP

## Domain-Specific Requirements

### Compliance & Regulatory
- None in MVP; emphasize reproducibility via lineage recorded in Notes: product, batch/batch, aliquot chain, instrument, quantities, units.

### Technical Constraints
- Authentication: Reuse Constellab auth/session.
- Data Model: Three-tier hierarchy: Materialx (generic definitions) → Materialx_Batch (physical instances) → Aliquots (batchs with parent_batch_id). Persist materials, batchs, suppliers, locations; track batch quantities and parent references; support single lab instance.
- Locations: Simple selectable list with CRUD operations; default location "labo" assigned if not specified on batch creation.
- Suppliers: Simple CRUD operations; optional on batch creation.
- Performance: Responsive Reflex pages; fast actions for create/increment/decrement/move/aliquot with minimal blocking.
- Concurrency: Prevent conflicting updates on the same batch (simple conflict check or lock).
- Referential Integrity: Batch → Material, Batch → Supplier (optional), Batch → Location (required), Aliquot Batch → Parent Batch (for aliquots).

### Integration Requirements
- Note Tool: Embed a custom Reflex inventory tool inside Constellab Notes to perform actions and link them to the note.
- Data Contracts: Material IDs, supplier, batch/batch, aliquot lineage, instrument references, quantities, units; updates must reflect in both inventory and note linkages.
- Locations: App maintains a simple selectable location list; no hierarchy in MVP.

### Risk Mitigations
- Inventory drift: Display current stock before decrement; confirmations; lineage links ensure traceability.
- Misassignment: Provide simple move/correction flows with activity recorded and linked to Notes.
- Aliquot complexity: Support multi-level aliquots but avoid bulk operations and mixture entities.

## Web App Specific Requirements

### Project-Type Overview
- Python Reflex SPA embedded within Constellab environment
- Reuse Constellab Note system; add a custom Reflex inventory tool inside Notes
- Internal application; no public SEO or indexing needs

### Technical Architecture Considerations
- Reflex SPA shell with Constellab auth/session
- Persist materials, locations, aliquot hierarchies; decrement stock on actions
- No real-time websockets; refresh inventory views after actions
- Simple concurrency guards to prevent conflicting updates

### Browser Matrix
- Evergreen browsers: latest Chrome, Edge, Firefox; recent Safari
- Reflex provides cross-browser handling; target modern versions

### Responsive Design
- Desktop-first layout; usable on tablets
- No mobile-first requirements for MVP

### Performance Targets
- Responsive page loads and snappy inventory actions
- Avoid long-blocking operations during add/move/aliquot/use

### Accessibility Level
- Baseline accessibility via Reflex components (keyboard navigation, contrast)
- Aim for practical WCAG AA alignment for forms and interactions

### SEO Strategy
- Not applicable; app is internal to Constellab

### Implementation Considerations
- No roles in MVP; any user can perform actions
- No bulk operations
- Locations remain a simple selectable list; single lab instance

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

MVP Approach: Problem-solving MVP focused on simple, reliable inventory actions and Note linkage within Constellab.
Resource Requirements: 1 Reflex developer (UI + integration), 1 part-time QA/PM; leverage existing Constellab components.

### MVP Feature Set (Phase 1)

Core User Journeys Supported:
- Material & Batch Management: create materials/batchs, increment/decrement, assign location, transform (multi-level aliquots), move.
- Note-Linked Action: perform inventory actions from Notes based on batch selection with consumption/usage differentiation.

Must-Have Capabilities:
- Create materials with consumable flag; create batchs with material reference, optional supplier, and location assignment (default: "labo").
- Simple location and supplier CRUD; simple selectable lists.
- Multi-level aliquots without depth restriction (aliquot can be parent of another aliquot).
- Increment/decrement batch quantities; move batchs between locations.
- From Notes: select batch, decrement consumable or reference non-consumable usage; link to Note with traceability (material, batch, parent chain, quantities, units).
- Constellab auth/session reuse; minimal concurrency checks on batch updates.
- No lineage visualization in MVP; no bulk operations; no roles; no alerts/reporting/compliance.


### Post-MVP Features

Phase 2 (Growth):
- Lineage visualization: view parent chain for batchs and aliquots
- Action history: view past actions linked to a Note
- Alerts/reporting; richer location hierarchies; role-based access (RBAC).
- Dashboards; improved audit views; mixture provenance entity.
- Automated reordering rules.

Phase 3 (Expansion):
- Compliance features (ISO/GxP readiness); multi-site support.
- Advanced analytics; external integrations.

### Risk Mitigation Strategy

Technical Risks: Concurrency and data integrity — mitigate with conflict checks and confirmations; ensure lineage consistency.
Market Risks: Adoption — measure daily usage of core flows and ratio of notes with linked usage.
Resource Risks: Scope creep — enforce MVP boundaries (no bulk, no advanced permissions) and iterate.

## Functional Requirements

### A. Material Management (Generic Definitions)

- **FR1:** User can create a material with name, description, and consumable flag (boolean).
- **FR2:** User can edit material metadata (name, description, consumable flag).
- **FR3:** User can view material catalog listing all defined materials.
- **FR4:** User can delete unused material definitions (not referenced by any batch).

### B. Batch Management (Physical Instances)

- **FR5:** User can create a batch by selecting a material, optionally specifying a supplier, and assigning a location (default: "labo" if not specified).
- **FR6:** User can view batch details: material reference, batch number, supplier, location, quantity, units, parent batch ID (if aliquot), creation date.
- **FR7:** User can increment batch quantity (e.g., receiving additional stock) with amount and unit.
- **FR8:** User can decrement consumable batch quantity with amount and unit (e.g., usage or removal).
- **FR9:** User can move a batch to a different location.
- **FR10:** User can delete empty or obsolete batchs.

### C. Aliquot Creation (Batch Derivation)

- **FR11:** User can create an aliquot from a parent batch, specifying quantity and unit for the new aliquot. The system creates a new batch with parent_batch_id referencing the parent.
- **FR12:** User can create multi-level aliquots without depth restriction (aliquot from aliquot).
- **FR13:** Aliquot inherits material reference from parent but maintains independent quantity, location, and supplier (if specified).

### D. Consumption & Usage Actions

- **FR14:** User can decrement consumable batch quantity from batch management interface with amount, unit, and optional reason.
- **FR15:** User can view confirmation and updated batch quantity after increment or decrement actions.
- **FR16:** Non-consumable usage references are captured only in Note-linked actions (see section E).

### E. Note-Linked Actions

- **FR17:** User can open the inventory tool from a Constellab Note.
- **FR18:** User can select a batch (not material directly) from available inventory within the Note context.
- **FR19:** User can perform a consumption action on a consumable batch: decrement quantity with amount and unit.
- **FR20:** User can perform a usage reference action on a non-consumable batch: record usage without quantity change.
- **FR21:** User can link the action to the Note with batch details: material name, batch number, supplier, quantity (if consumable), units.
- **FR22:** Note captures traceability: material, batch, parent batch chain (if aliquot), quantities, units.

### F. Supplier Management (CRUD)

- **FR23:** User can create a supplier with name and contact information.
- **FR24:** User can edit supplier details.
- **FR25:** User can view supplier list.
- **FR26:** User can delete unused suppliers (not referenced by any batch).

### G. Location Management (CRUD)

- **FR27:** User can create a location with name and description.
- **FR28:** User can edit location details.
- **FR29:** User can view location list.
- **FR30:** User can delete unused locations (not referenced by any batch).
- **FR31:** System assigns default location "labo" to batchs if location not specified on creation.

### H. Constellab Integration

- **FR32:** User can access the app via Constellab with existing auth/session.
- **FR33:** Inventory tool embeds seamlessly within Constellab Notes interface.

### I. Data Consistency & Units

- **FR34:** User can select quantities in supported units (volume, mass, length, count).
- **FR35:** System displays units on all quantities; automatic unit conversion is out of scope for MVP.
- **FR36:** System enforces referential integrity: batch references valid material, supplier (if specified), location; aliquot references valid parent batch.

## Non-Functional Requirements

### Performance
- Typical inventory actions (add/move/aliquot/use) complete without long blocking; pages feel responsive in Reflex.
- No realtime websockets required; views refresh after actions.

### Reliability
- Actions apply atomically; inventory state and Note linkages remain consistent after success.
- Simple concurrency checks prevent conflicting updates on the same batch.
- Referential integrity enforced: batch → material, batch → location (required), batch → supplier (optional), aliquot batch → parent batch.

### Integration
- Reuse Constellab auth/session; embed inventory tool within Notes reliably.
- App manages a simple location list; interface is stable for Note actions.

### Accessibility
- Practical keyboard navigation and readable contrast via Reflex components; align with WCAG AA pragmatically for forms.

### Security
- Access via Constellab session; transport is HTTPS; no sensitive data beyond lab inventory in MVP.
