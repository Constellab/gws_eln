stepsCompleted: ["step-01-init", "step-02-discovery", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish"]
inputDocuments:
	- /lab/user/_bmad-output/planning-artifacts/product-brief-user-2026-01-20.md
workflowType: 'prd'
project_name: user
user_name: Nour
date: 2026-01-20
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

## User Journeys

All actions are available to any user in MVP; there are no roles or bulk operations.

1. Inventory Management (All Users)
- Receive/add materials with supplier, lot/batch, expiry, packaging
- Assign material to a location from a simple selectable list
- Create and transform multi-level aliquots
- Move materials/aliquots between locations
- Remove/decrement stock via usage

2. Note-Linked Inventory Action (All Users)
- Within Constellab’s existing Note system, open a custom Reflex inventory tool
- Select materials/samples/instruments and perform an action (usage, aliquot, move)
- Link the action to the note; stock decrements and lineage updates
- Ensure the note captures minimal lineage: product, lot, aliquot chain, instrument, quantities, units

### Journey Requirements Summary
- Inventory section: add, remove, transform (aliquots), move; simple location list; decrement stock; lineage capture
- Note integration: Reflex tool embedded in Constellab Notes; uses existing auth and storage; updates inventory and note links
- Roles/Permissions: none in MVP; anyone can perform actions
- Constraints: no bulk actions; no alerts/reporting/compliance; single lab instance

## Domain-Specific Requirements

### Compliance & Regulatory
- None in MVP; emphasize reproducibility via lineage recorded in Notes: product, lot/batch, aliquot chain, instrument, quantities, units.

### Technical Constraints
- Authentication: Reuse Constellab auth/session.
- Data: Persist materials, locations, aliquot hierarchies; decrement stock; support single lab instance; simple selectable location list (no hierarchy).
- Performance: Responsive Reflex pages; fast actions for add/move/aliquot/use with minimal blocking.
- Concurrency: Prevent conflicting updates on the same material/aliquot (simple conflict check or lock).

### Integration Requirements
- Note Tool: Embed a custom Reflex inventory tool inside Constellab Notes to perform actions and link them to the note.
- Data Contracts: Material IDs, supplier, lot/batch, aliquot lineage, instrument references, quantities, units; updates must reflect in both inventory and note linkages.
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
- Inventory Management: add/receive, assign location, transform (aliquots), move, remove/decrement.
- Note-Linked Action: perform inventory actions from Notes and capture lineage.

Must-Have Capabilities:
- Register/add materials (supplier, lot/batch, expiry, packaging).
- Simple location list assignment; single lab instance.
- Multi-level aliquots creation/transform; move between locations.
 - Aliquot creation/transform (single-level); move between locations.
- Decrement stock and record usage from inventory and Notes; lineage capture (product, lot, aliquot chain, instrument, quantities, units).
- Constellab auth/session reuse; minimal concurrency checks on updates.
- No roles; no bulk operations; no alerts/reporting/compliance.


### Post-MVP Features

Phase 2 (Growth):
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

### Terminology Clarifications
- Packaging: physical container type and size for a material (e.g., vial 1.5 mL, bottle 500 mL); recorded to reflect handling and aliquoting constraints.
- Aliquots: derived portions from a source material tracked as individual items. MVP supports single-level aliquots only (no aliquot-from-aliquot).

### Inventory Registration & Metadata
- FR1: User can register a material with supplier, lot/batch, expiry, and packaging (container type/size).
- FR2: User can receive a delivery and adjust available quantity for a material.
- FR3: User can view material details including stock, units, and current location.
- FR4: User can edit material metadata except immutable identifiers.

### Locations & Movement
- FR5: User can assign a material or aliquot to a location from a selectable list.
- FR6: User can move a material or aliquot between locations.
- FR7: User can view inventory filtered by location.

### Aliquoting & Lineage
- FR8: User can create aliquots from a source material with specified quantities and units (single-level).
- FR9: User can create multi-level aliquots (aliquot from an aliquot) — post-MVP optional; not required for MVP.
- FR10: User can view lineage for a material or aliquot (parent–child chain).
- FR11: User can relabel an aliquot without breaking lineage.

### Usage & Decrement
- FR12: User can log usage that decrements stock with quantity and unit.
- FR13: User can remove/discard materials or aliquots and record a reason (distinct from FR12 usage; removal is a non-usage decrement).
- FR14: User can view confirmations and updated stock after actions.

### Note-Linked Actions
- FR15: User can open an inventory tool from a Note.
- FR16: User can perform increment, decrement, move, or transform (aliquots) actions within the Note context.
- FR17: User can link actions to the Note with references to product, lot/batch, aliquot chain, instrument, quantities, and units.
- FR18: User can view linked inventory actions from the Note.

### Samples & Instruments
- FR19: User can register a sample and assign storage/location.
- FR20: User can create sample aliquots and view sample lineage.
- FR21: User can reference an instrument in a Note-linked action.
- FR22: User can record simple instrument status or a maintenance note.

### Constellab Integration & Session
- FR23: User can access the app via Constellab with existing auth/session.
- FR24: User can use the app-managed location list within the app.

### Activity & Correction Flows
- FR25: User can review a chronological activity log of inventory actions.
- FR26: User can correct a misassignment by moving an item and retaining history.
- FR27: User can mark an item for manual reordering and record a reorder event.

### Units & Data Consistency
- FR28: User can select quantities in supported units (volume, mass, length, count).
- FR29: User can view units on all quantities; automatic unit conversion is out of scope for MVP.

## Non-Functional Requirements

### Performance
- Typical inventory actions (add/move/aliquot/use) complete without long blocking; pages feel responsive in Reflex.
- No realtime websockets required; views refresh after actions.

### Reliability
- Actions apply atomically; inventory state and Note linkages remain consistent after success.
- Simple concurrency checks prevent conflicting updates on the same material/aliquot.

### Integration
- Reuse Constellab auth/session; embed inventory tool within Notes reliably.
- App manages a simple location list; interface is stable for Note actions.

### Accessibility
- Practical keyboard navigation and readable contrast via Reflex components; align with WCAG AA pragmatically for forms.

### Security
- Access via Constellab session; transport is HTTPS; no sensitive data beyond lab inventory in MVP.
