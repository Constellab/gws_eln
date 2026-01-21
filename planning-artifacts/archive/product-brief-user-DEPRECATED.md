---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: []
date: 2026-01-20
author: Nour
status: DEPRECATED, DO NOT USE
---

# Product Brief: user

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

Build a minimal, lab-friendly ELN/LIMS to trace Materials, Samples, Instruments/Equipment, and ELN Notes/Templates with just-what’s-needed workflows. The MVP keeps operations flexible (reception, usage, aliquoting, and reordering in any order), models multi-lot/supplier, treats multi-source as separate products, supports multi-level aliquots, and keeps locations simple via a selectable list. No compliance scoring, alerts, or reporting in MVP. Single lab instance. Focus is on straightforward registration, storage assignment, aliquoting, experiment linkage, and usage logging for reproducibility and inventory awareness.

---

## Core Vision

### Problem Statement
Small labs lack a simple tool to reliably trace consumables, samples, instruments, and ELN context without the overhead of full LIMS platforms. This leads to fragmented records, inventory blind spots, and difficulty reproducing experiments.

### Problem Impact
- Hard-to-audit experiment provenance and inventory usage.
- Stock and lot context scattered across spreadsheets and notes.
- Delays and waste from poor visibility into what’s available where.
- Overhead from heavyweight tools that are overkill for MVP needs.

### Why Existing Solutions Fall Short
- Traditional LIMS are complex/expensive and slow to adapt.
- Simple inventory apps don’t handle lots, aliquot hierarchies, or lab workflows well.
- ELNs often don’t tie inventory/instruments tightly to experiments.

### Proposed Solution
A minimal ELN/LIMS centered on four pillars, designed for flexible, real lab use:
- Materials: register products with supplier + lot/batch + expiry + packaging; receive deliveries; assign to a simple set of locations; create multi-level aliquots; link usage to experiments/protocols; decrement stock; reordering is a manual action (no automated rules).
- Samples: create/derive samples with lineage and storage; support aliquots; link to experiments; treat “mixtures” as multiple products used together (no special mixture entity).
- Instruments/Equipment: track identity, status, calibration/maintenance notes (simple), and link instrument usage to experiments.
- ELN Notes & Templates: versioned notes/templates with statuses and links to materials, samples, instruments, and experiments.

MVP boundaries:
- No alerts, no reporting, no compliance scoring (ISO/GxP).
- Locations are a selectable list (no hierarchy), configurable by the lab.
- Units supported: volume (e.g., µL, mL), mass (mg, g), length (mm, cm), and count.
- Single lab instance.

### Key Differentiators
- Lab-first simplicity for day-one usability.
- Multi-level aliquots with straightforward lineage; no mixture complexity.
- Flexible, non-linear lifecycle (receive/use/aliquot/reorder in any order).
- Tight linking across ELN notes, inventory, samples, and instruments without heavy compliance baggage.

## Target Users

### Primary Users

- Lab Technicians: Perform day-to-day tasks (receive, assign location, aliquot, log usage). Need simplicity and speed; no role-specific restrictions in MVP.
- Lab Managers: Keep visibility on stock and locations; use the same flows as technicians; prioritize straightforward tracking rather than complex controls.
- Project Leads: Link usage to experiments; write notes that narrate what was done and what was used; value simple traceability tied to their work.

### Secondary Users

N/A

### User Journey

- Discovery/Onboarding: Start using immediately with minimal setup; single lab instance and common access model.
- Core Usage: Flexible order of operations (receive, use, aliquot, reorder). Record usage directly within ELN notes; link materials/samples/instruments to the note and decrement stock.
- Success Moment: “It’s simple, and I can see exactly what happened to this product.”
- Long-term: Daily notes become living reports—textual description plus inventory usage embedded—providing reproducible context without extra reporting modules.

## Success Metrics

User success metrics are intentionally deferred for MVP. We will focus on lightweight operational and adoption signals.

### Business Objectives

- 3 months: single lab live; consistent daily use across core flows (reception, usage, aliquoting).
- 12 months: sustained daily usage; smooth onboarding of new team members; minimal friction in logging inventory-linked notes.

### Key Performance Indicators

- Adoption: daily active users in the lab.
- Engagement: ratio of notes that include linked product usage.
- Inventory hygiene: ratio of materials with an assigned location.
- Aliquot activity: aliquots created per week.
- Operational ease: median time to log reception or usage.

Targets: baseline in month 1; thresholds set post-baseline (no dashboards in MVP).

## MVP Scope

### Core Features

- Materials: register products (supplier, lot/batch, expiry, packaging); receive deliveries; assign simple locations; create multi-level aliquots; log usage inside notes; decrement stock; manual reordering.
- Samples: create/derive, store, aliquot, link to experiments; treat multi-source as separate products (no mixture entity).
- Instruments/Equipment: identity, status, simple calibration/maintenance notes; link instrument usage to experiments.
- ELN Notes/Templates: versioned notes/templates with statuses; embed inventory usage directly in notes for narrative + traceability.

### Out of Scope for MVP

- Alerts, reporting, compliance scoring (ISO/GxP), multi-site support.
- Complex role-based permissions; hierarchical locations; mixture entity.
- Automated reordering rules; dashboards; unit conversions.

### MVP Success Criteria

- App used daily to log reception, aliquots, and usage within notes.
- Majority of materials have an assigned location; notes commonly include linked product usage.
- Teams onboard without training-heavy workflows; flows remain simple and fast.

### Future Vision

- Add alerts/reporting and richer location hierarchies.
- Role-based access, mixture provenance entity, automated reordering.
- Compliance features (ISO/GxP readiness), multi-site support, dashboards.
