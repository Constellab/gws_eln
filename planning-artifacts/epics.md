---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
	- /lab/user/_bmad-output/planning-artifacts/prd.md
	- /lab/user/_bmad-output/planning-artifacts/architecture.md
	- /lab/user/_bmad-output/planning-artifacts/product-brief-user-2026-01-20.md
---

# user - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for user, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can register a material with supplier, lot/batch, expiry, and packaging.
FR2: User can receive a delivery and adjust available quantity for a material.
FR3: User can view material details including stock, units, and current location.
FR4: User can edit material metadata except immutable identifiers.
FR5: User can assign a material or aliquot to a location from a selectable list.
FR6: User can move a material or aliquot between locations.
FR7: User can view inventory filtered by location.
FR8: User can create aliquots from a source material with specified quantities and units (single-level).
FR9: User can create multi-level aliquots (aliquot from an aliquot) — post-MVP optional.
FR10: User can view lineage for a material or aliquot (parent–child chain).
FR11: User can relabel an aliquot without breaking lineage.
FR12: User can log usage that decrements stock with quantity and unit.
FR13: User can remove/discard materials or aliquots and record a reason.
FR14: User can view confirmations and updated stock after actions.
FR15: User can open an inventory tool from a Note.
FR16: User can perform increment, decrement, move, or transform (aliquots) actions within the Note context.
FR17: User can link actions to the Note with references to product, lot/batch, aliquot chain, instrument, quantities, and units.
FR18: User can view linked inventory actions from the Note.
FR19: User can register a sample and assign storage/location.
FR20: User can create sample aliquots and view sample lineage.
FR21: User can reference an instrument in a Note-linked action.
FR22: User can record simple instrument status or a maintenance note.
FR23: User can access the app via Constellab with existing auth/session.
FR24: User can use the app-managed location list within the app.
FR25: User can review a chronological activity log of inventory actions.
FR26: User can correct a misassignment by moving an item and retaining history.
FR27: User can mark an item for manual reordering and record a reorder event.
FR28: User can select quantities in supported units (volume, mass, length, count).
FR29: User can view units on all quantities; no automatic unit conversion in MVP.

### NonFunctional Requirements

NFR1: Performance — typical actions (add/move/aliquot/use) complete without long blocking.
NFR2: Performance — views refresh after actions; no realtime websockets in MVP.
NFR3: Reliability — actions apply atomically; inventory and Note linkages remain consistent.
NFR4: Reliability — simple concurrency checks prevent conflicting updates.
NFR5: Integration — reuse Constellab auth/session; embed inventory tool within Notes.
NFR6: Integration — app manages a simple location list; stable interfaces for Note actions.
NFR7: Accessibility — practical keyboard navigation and readable contrast; pragmatic WCAG AA alignment for forms.
NFR8: Security — session-based access; HTTPS transport; internal-only endpoints.
NFR9: Maintainability — follow feature-based structure and naming patterns; service-layer REST functions.
NFR10: Testing — service-layer tests via pytest; UI tests optional post-MVP.

### Additional Requirements

- Starter: Constellab Reflex App scaffold (gws_project pattern) selected; initialize via `gws reflex run bricks/gws_eln/src/gws_eln/project_app/_project_app/rxconfig.py`.
- Environment: `GWS_REFLEX_API_URL` must be set for `rxconfig.py`.
- ORM/DB: Peewee via `gws_core.Model`; MariaDB in production, SQLite for local dev via `DatabaseProxy`.
- Concurrency: optimistic checks (version/updated_at guard) with user confirmations on conflicts.
- API pattern: internal service-layer REST-like functions; no GraphQL; direct payload or `{data: ...}` success format; `{error: {code, message}}` for errors.
- Frontend state: Reflex `State` classes per page/feature; route-based pages; no global complex state.
- Migrations: versioned modules under `migrations/`; schema evolution tracked in brick.
- Naming/formatting: snake_case plural tables; snake_case JSON fields; ISO-8601 UTC dates.
- Units & seed data: seed units catalog and initial location list.
- Deferred: RBAC and websockets post-MVP; dashboards/reporting later.

### FR Coverage Map

FR1: Epic 1 - Register material with metadata
FR2: Epic 1 - Receive delivery; adjust quantity
FR3: Epic 1 - View material details
FR4: Epic 1 - Edit material metadata
FR5: Epic 2 - Assign to location
FR6: Epic 2 - Move between locations
FR7: Epic 2 - View inventory filtered by location
FR8: Epic 3 - Create single-level aliquots
FR9: Epic 3 - Multi-level aliquots (post-MVP)
FR10: Epic 3 - View lineage
FR11: Epic 3 - Relabel aliquot without breaking lineage
FR12: Epic 4 - Log usage decrement
FR13: Epic 4 - Remove/discard with reason
FR14: Epic 4 - Confirmations and updated stock
FR15: Epic 5 - Open inventory tool from Note
FR16: Epic 5 - Perform actions in Note context
FR17: Epic 5 - Link actions to Note with references
FR18: Epic 5 - View linked actions from Note
FR19: Epic 6 - Register sample and assign storage
FR20: Epic 6 - Sample aliquots and lineage
FR21: Epic 5 - Reference instrument in Note action
FR22: Epic 6 - Instrument status/maintenance note
FR23: Epic 9 - Access via Constellab session
FR24: Epic 9 - App-managed location list
FR25: Epic 7 - Chronological activity log
FR26: Epic 2 - Misassignment correction while retaining history
FR27: Epic 7 - Manual reordering flagging and events
FR28: Epic 8 - Units selection for quantities
FR29: Epic 8 - Units visible across app; no conversions

## Epic List

### Epic 1: Inventory Registration & Details
Users can register materials, receive deliveries, edit metadata, and view material details.
**FRs covered:** FR1, FR2, FR3, FR4

### Epic 2: Locations & Movement
Users can assign and move materials/aliquots between locations, view inventory by location, and correct misassignments while retaining history.
**FRs covered:** FR5, FR6, FR7, FR26

### Epic 3: Aliquoting & Lineage
Users can create single-level aliquots, view lineage, and relabel aliquots without breaking lineage. Multi-level aliquots are noted as post-MVP.
**FRs covered:** FR8, FR9 (post-MVP), FR10, FR11

### Epic 4: Usage & Decrement
Users can log usage that decrements stock, discard/remove items with reasons, and view confirmations with updated stock.
**FRs covered:** FR12, FR13, FR14

### Epic 5: Note-Linked Actions
Users can perform inventory actions within Constellab Notes, link actions (product, lot, aliquot chain, instrument, quantities, units), and view linked actions in Notes.
**FRs covered:** FR15, FR16, FR17, FR18, FR21

### Epic 6: Samples & Instruments
Users can register samples, create sample aliquots with lineage, and record instrument status or maintenance notes.
**FRs covered:** FR19, FR20, FR22

### Epic 7: Activity Log & Reorder
Users can review a chronological activity log and mark items for manual reordering with recorded events.
**FRs covered:** FR25, FR27

### Epic 8: Units & Consistency
Users select and see units consistently across the app; no conversions in MVP.
**FRs covered:** FR28, FR29

### Epic 9: Constellab Access & Session Integration
Users access the app via Constellab using existing auth/session and utilize the app-managed location list.
**FRs covered:** FR23, FR24
## Epic 1: Inventory Registration & Details

Enable users to register materials, receive deliveries, edit metadata, and view details.

### Story 1.1: Register Material with Metadata
As a lab user,
I want to register a material with supplier, lot/batch, expiry, and packaging,
So that the material becomes trackable in inventory with complete metadata.

**Acceptance Criteria:**
**Given** a registration form with required fields (supplier, lot/batch, expiry, packaging)
**When** I submit valid data
**Then** the material is created and visible in inventory with an ID
**And** invalid required fields show inline errors without creating a record

### Story 1.2: Receive Delivery and Adjust Quantity
As a lab user,
I want to record a delivery and adjust available quantity,
So that current stock reflects incoming materials.

**Acceptance Criteria:**
**Given** a material exists
**When** I add a received quantity and unit
**Then** stock increases atomically and confirms the new total
**And** a validation prevents negative quantities or missing units

### Story 1.3: View Material Details
As a lab user,
I want to view a material’s details (stock, units, current location, metadata),
So that I can understand its status and usage readiness.

**Acceptance Criteria:**
**Given** a material page
**When** I open the details view
**Then** I see stock, units, current location, supplier, lot/batch, expiry, packaging
**And** data loads within target performance without blocking

### Story 1.4: Edit Material Metadata
As a lab user,
I want to edit material metadata except immutable identifiers,
So that corrections and updates are possible.

**Acceptance Criteria:**
**Given** editable fields (supplier, expiry, packaging)
**When** I submit updates
**Then** changes persist and confirm success
**And** concurrent update conflicts prompt a confirmation and safe retry

## Epic 2: Locations & Movement

Enable users to assign and move items between locations, filter by location, and correct misassignments.

### Story 2.1: Assign Item to Location
As a lab user,
I want to assign a material or aliquot to a location from a simple list,
So that items are stored and discoverable.

**Acceptance Criteria:**
**Given** a location picker with available locations
**When** I select a location and confirm
**Then** the item’s location updates and displays in inventory
**And** invalid location selections are prevented

### Story 2.2: Move Item Between Locations
As a lab user,
I want to move a material or aliquot between locations,
So that I can reorganize storage.

**Acceptance Criteria:**
**Given** an item with a current location
**When** I select a new location and confirm
**Then** the location updates and movement is logged
**And** the inventory view refreshes showing the new location

### Story 2.3: View Inventory by Location
As a lab user,
I want to filter inventory by location,
So that I can quickly find items in a specific place.

**Acceptance Criteria:**
**Given** a location filter
**When** I choose a location
**Then** I see only items in that location
**And** clearing the filter shows all items

### Story 2.4: Correct Misassignment with History Retained
As a lab user,
I want to correct misassigned items while retaining a history entry,
So that auditability is preserved.

**Acceptance Criteria:**
**Given** an item incorrectly assigned
**When** I move it to the correct location
**Then** the change is recorded in activity log with reason
**And** the item appears under the correct location immediately

## Epic 3: Aliquoting & Lineage

Enable single-level aliquots, lineage viewing, and relabeling without breaking lineage.

### Story 3.1: Create Single-Level Aliquots
As a lab user,
I want to create aliquots from a source material with specified quantities and units,
So that derived items are traceable.

**Acceptance Criteria:**
**Given** a source material and aliquot form
**When** I enter valid quantities and units
**Then** aliquots are created and linked to the parent
**And** stock updates or reservations reflect the operation

### Story 3.2: View Lineage
As a lab user,
I want to view parent–child chain for materials and aliquots,
So that I can understand provenance.

**Acceptance Criteria:**
**Given** an item with lineage
**When** I open its lineage viewer
**Then** I see parent and children in sequence
**And** links navigate to related items

### Story 3.3: Relabel Aliquot without Breaking Lineage
As a lab user,
I want to relabel an aliquot while preserving its lineage,
So that labeling updates don’t lose provenance.

**Acceptance Criteria:**
**Given** an aliquot detail page
**When** I change its label
**Then** the label updates and lineage remains intact
**And** the change appears in activity history

## Epic 4: Usage & Decrement

Enable logging usage, discarding/removing with reasons, and confirmations with updated stock.

### Story 4.1: Log Usage that Decrements Stock
As a lab user,
I want to log usage with quantity and unit,
So that stock reflects consumption.

**Acceptance Criteria:**
**Given** a usage form
**When** I submit a valid quantity and unit
**Then** stock decrements atomically and confirms the new total
**And** negative or zero quantities are rejected

### Story 4.2: Discard/Remove with Reason
As a lab user,
I want to remove items with a recorded reason,
So that disposal is auditable.

**Acceptance Criteria:**
**Given** an item
**When** I select remove and provide a reason
**Then** the item is marked removed and stock updated
**And** the reason appears in the activity log

### Story 4.3: Show Confirmations and Updated Stock
As a lab user,
I want confirmations after actions with updated stock displayed,
So that I have immediate feedback.

**Acceptance Criteria:**
**Given** a completed action (use/remove)
**When** the operation succeeds
**Then** I see a success message with new stock
**And** any failure shows an error with guidance

## Epic 5: Note-Linked Actions

Enable performing inventory actions in Constellab Notes with lineage links.

### Story 5.1: Open Inventory Tool from Note
As a lab user,
I want to open an inventory tool within a Note,
So that I can act without leaving the Note.

**Acceptance Criteria:**
**Given** a Note context
**When** I launch the inventory tool
**Then** the tool opens with my session and Note reference
**And** available actions are displayed

### Story 5.2: Perform Actions in Note Context
As a lab user,
I want to increment, decrement, move, or transform aliquots within the Note,
So that inventory updates are linked to my Note.

**Acceptance Criteria:**
**Given** the Note tool
**When** I perform an action with valid inputs
**Then** inventory updates occur and the view refreshes
**And** errors present clear messages

### Story 5.3: Link Actions to Note with References
As a lab user,
I want actions to link product, lot, aliquot chain, instrument, quantities, and units to the Note,
So that lineage and context are captured.

**Acceptance Criteria:**
**Given** a completed action in the Note tool
**When** the link is created
**Then** the Note contains references to product, lot, aliquot chain, instrument, quantities, units
**And** audit entries reference the Note ID

### Story 5.4: View Linked Actions from Note
As a lab user,
I want to view inventory actions linked to a Note,
So that I can verify performed operations.

**Acceptance Criteria:**
**Given** a Note with linked actions
**When** I open the linked actions view
**Then** I see a chronological list with action details
**And** links navigate to inventory items

## Epic 6: Samples & Instruments

Enable sample registration, sample aliquots with lineage, and instrument status notes.

### Story 6.1: Register Sample with Storage
As a lab user,
I want to register a sample and assign storage/location,
So that samples are tracked.

**Acceptance Criteria:**
**Given** a sample form
**When** I submit valid data
**Then** the sample is created and assigned to a location
**And** invalid inputs show inline errors

### Story 6.2: Create Sample Aliquots and View Lineage
As a lab user,
I want to create aliquots from a sample and view their lineage,
So that provenance is clear.

**Acceptance Criteria:**
**Given** a sample
**When** I create aliquots
**Then** child records link to the sample
**And** lineage viewer shows the chain

### Story 6.3: Record Instrument Status or Maintenance Note
As a lab user,
I want to record simple instrument status or a maintenance note,
So that instrument history is captured.

**Acceptance Criteria:**
**Given** an instrument
**When** I add a status or maintenance note
**Then** the entry saves and appears in activity
**And** it can be referenced from Note actions

## Epic 7: Activity Log & Reorder

Enable an activity log and manual reordering.

### Story 7.1: View Activity Log
As a lab user,
I want to view a chronological activity log of inventory actions,
So that I can audit changes.

**Acceptance Criteria:**
**Given** the activity page
**When** I open it
**Then** I see actions (use, move, aliquot, edit) with timestamps and actor
**And** I can filter by item or action type

### Story 7.2: Mark Item for Manual Reordering
As a lab user,
I want to mark items for manual reordering and record events,
So that replenishment is trackable.

**Acceptance Criteria:**
**Given** an inventory item
**When** I mark it for reorder and add an event
**Then** a reorder flag and event are stored and visible
**And** the activity log shows the event

## Epic 8: Units & Consistency

Enable consistent units selection and display across the app.

### Story 8.1: Select Units for Quantities
As a lab user,
I want to select units for quantities (volume, mass, length, count),
So that inputs are standardized.

**Acceptance Criteria:**
**Given** a quantity input
**When** I select a unit from supported list
**Then** the unit saves with the value
**And** invalid unit selections are prevented

### Story 8.2: Display Units Consistently
As a lab user,
I want units displayed consistently across all quantities,
So that readability is improved.

**Acceptance Criteria:**
**Given** any quantity field
**When** I view the item
**Then** units are shown with values
**And** no automatic conversion occurs

## Epic 9: Constellab Access & Session Integration

Enable app access via Constellab session and use of the app-managed location list.

### Story 9.1: Access App via Constellab Session
As a lab user,
I want to access the app with my existing Constellab session,
So that I don’t reauthenticate.

**Acceptance Criteria:**
**Given** a valid Constellab session
**When** I open the app
**Then** the session is reused and I am authenticated
**And** HTTPS transport is enforced

### Story 9.2: Use App-Managed Location List
As a lab user,
I want to use a simple location list managed by the app,
So that assignments remain straightforward.

**Acceptance Criteria:**
**Given** location management
**When** I view and select locations
**Then** available locations are listed from the app catalog
**And** changes are reflected across inventory
<!-- Finalized: All placeholders removed and validation complete -->
