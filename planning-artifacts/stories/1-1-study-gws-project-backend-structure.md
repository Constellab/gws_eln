# Story 1.1: Study gws_project Backend Structure

Status: ready-for-dev

## Story

As a developer,
I want to study the gws_project repository backend patterns,
so that I follow established conventions for entities and services.

## Acceptance Criteria

1. Review gws_project entity definitions (Model, ModelWithUser)
2. Document naming conventions (snake_case tables, columns)
3. Identify service patterns (CRUD operations)
4. Understand test structure
5. Create reference notes for team

## Context

This is the **first story** in Epic 1 and the **foundation story** for the entire gws_eln project. The purpose is to thoroughly study the `gws_project` repository to extract critical architectural patterns, naming conventions, and implementation standards that MUST be followed throughout gws_eln development.

**Critical Mission:** Prevent future implementation mistakes by establishing a deep understanding of the reference patterns. This story is about **learning and documenting**, not implementing.

## Technical Requirements

### 1. Study gws_project Entity Structure

**Location:** `/lab/user/bricks/others/gws_project/src/gws_project/`

**Focus Areas:**
- **Model base classes:** `gws_core.Model` and `gws_core.ModelWithUser`
  - How audit fields are implemented (`created_by_id`, `last_modified_by_id`, `created_at`, `last_modified_at`)
  - How Peewee ORM is used for field definitions
  - Foreign key patterns and relationship definitions
- **Entity organization:** How entities are organized by domain (e.g., `project/`, `task/`, `document/`, `user/`)
- **Naming conventions:**
  - Table names: `snake_case` plural
  - Column names: `snake_case`
  - Foreign keys: `<entity>_id` pattern
  - Indices naming: `idx_<table>_<column(s)>`

**Example Entities to Study:**
- Check entities in `project/`, `task/`, `document/`, `user/` folders
- Look for patterns in how entities extend base models
- Note how relationships (1:N, N:1, self-references) are defined

### 2. Study Service Layer Patterns

**Focus Areas:**
- **Service structure:** How services are organized alongside entities
- **CRUD patterns:** Standard create, read, update, delete operations
- **Validation:** Where and how validation occurs
- **Transaction handling:** How database transactions are managed
- **Error handling:** How errors are raised and caught
- **CurrentUserService:** How user context is accessed and used

**Key Questions to Answer:**
- Where do services live relative to entities? (co-located in domain folders?)
- What is the standard pattern for a service class?
- How are foreign key relationships validated?
- How are audit fields populated automatically?

### 3. Study Test Structure

**Location:** `/lab/user/bricks/others/gws_project/tests/`

**Focus Areas:**
- **Test organization:** How tests mirror source structure
- **Test naming:** File and function naming conventions
- **Test patterns:** Setup, fixtures, assertions
- **Database setup:** How test database is initialized/cleaned
- **Mocking patterns:** How external dependencies are mocked

**Key Questions to Answer:**
- How are tests organized by domain?
- What testing framework/tools are used? (pytest, fixtures, etc.)
- How is test data created and cleaned up?
- What is the expected test coverage standard?

### 4. Document Project Structure Alignment

**Create Reference Document:** `gws_project_reference_patterns.md` in planning-artifacts

**Document Should Include:**

#### Section 1: Entity Patterns
- Base model usage (Model vs ModelWithUser)
- Field definition patterns
- Relationship patterns (ForeignKey, self-reference)
- Audit field implementation
- Index definitions

#### Section 2: Naming Conventions
- Table naming: examples and rules
- Column naming: examples and rules
- Foreign key naming: pattern and examples
- Index naming: pattern and examples
- File/folder naming: structure and conventions

#### Section 3: Service Layer Patterns
- Service class structure template
- CRUD operation patterns
- Validation approach
- Transaction management
- User context usage

#### Section 4: Test Patterns
- Test organization structure
- Test naming conventions
- Common test patterns (setup, teardown, assertions)
- Database test setup
- Expected coverage standards

#### Section 5: gws_eln Alignment Strategy
- Map gws_eln domains to gws_project patterns
- Identify any necessary deviations (with justification)
- Define folder structure for gws_eln following gws_project
- Document standards for upcoming stories

## Tasks / Subtasks

- [ ] Task 1: Study gws_project entity structure (AC: #1, #2)
  - [ ] Navigate `/lab/user/bricks/others/gws_project/src/gws_project/`
  - [ ] Examine base model classes in gws_core
  - [ ] Study 3-5 example entities across different domains
  - [ ] Document entity patterns and naming conventions
  
- [ ] Task 2: Study service layer patterns (AC: #3)
  - [ ] Locate service files in gws_project
  - [ ] Analyze CRUD operation patterns
  - [ ] Document validation and error handling approaches
  - [ ] Note transaction and user context patterns
  
- [ ] Task 3: Study test structure (AC: #4)
  - [ ] Navigate `/lab/user/bricks/others/gws_project/tests/`
  - [ ] Examine test organization and naming
  - [ ] Study 3-5 example test files
  - [ ] Document test patterns and setup approaches
  
- [ ] Task 4: Create reference documentation (AC: #5)
  - [ ] Create `gws_project_reference_patterns.md` in planning-artifacts
  - [ ] Document all findings in structured format
  - [ ] Include code examples for critical patterns
  - [ ] Define gws_eln alignment strategy
  - [ ] Get team review and approval

## Dev Notes

### Project Structure Context

**gws_eln Location:** `/lab/user/bricks/gws_eln/`

**Current Structure:**
```
bricks/gws_eln/
├── planning-artifacts/     # PRD, architecture, epics
├── src/
│   └── gws_eln/
│       └── __init__.py     # Currently minimal
├── tests/                  # Test folder (currently empty)
├── settings.json
└── README.md
```

**Target Structure (Based on gws_project):**
```
bricks/gws_eln/
├── planning-artifacts/
├── src/
│   └── gws_eln/
│       ├── __init__.py
│       ├── core/           # DB manager, base setup (Story 1.6-1.7)
│       ├── materials/      # material.py, material_batch.py, services (Story 1.2, 1.3, Epic 4-6)
│       ├── suppliers/      # supplier.py, supplier_service.py (Story 1.4, Epic 3)
│       ├── locations/      # location.py, location_service.py (Story 1.5, Epic 3)
│       ├── activities/     # activity.py, activity_service.py (Story 1.6, Epic 7)
│       ├── utils/          # units.py, validators.py (Epic 2)
│       └── project_app/    # Reflex UI (Phase 2, Epic 8+)
└── tests/                  # Mirror src structure
```

### Critical Implementation Rules

**From Architecture:**
1. **MUST** follow gws_project patterns exactly unless justified deviation
2. **MUST** use `gws_core.ModelWithUser` for all entities (audit fields)
3. **MUST** use snake_case for all database identifiers
4. **MUST** store quantities in base units (L, kg, m, units) with DECIMAL(20,12)
5. **MUST** implement comprehensive service-layer tests BEFORE any UI work

**From PRD:**
- 5 core entities: Material, Material_Batch, Supplier, Location, Activity
- Unified model: is_consumable flag determines behavior (no separate tables)
- Multi-level aliquots via parent_batch_id self-reference
- Default "labo" location must be seeded

**Key Technical Decisions:**
- Framework: Python Reflex
- Database: MariaDB (production), SQLite (dev)
- ORM: Peewee via gws_core.Model
- Auth: Constellab CurrentUserService
- Testing: pytest with service-layer focus

### Research Areas

**Questions to Answer:**
1. How does gws_core.ModelWithUser implement audit fields automatically?
2. What is the standard pattern for service initialization with current user?
3. How are database migrations handled? (if at all)
4. What testing utilities/fixtures are available in gws_core?
5. How is the database connection/session managed?

### References

- **Architecture:** [architecture-summary.md](architecture-summary.md)
- **Database Schema:** [database-schema.md](database-schema.md)
- **Implementation Patterns:** [implementation-patterns.md](implementation-patterns.md)
- **PRD:** [prd.md](prd.md)
- **Epics:** [epics.md](epics.md)
- **gws_project Location:** `/lab/user/bricks/others/gws_project/`

### Success Metrics

- [ ] Reference document created and approved
- [ ] All patterns documented with examples
- [ ] Team has clear understanding of conventions
- [ ] gws_eln structure aligns with gws_project patterns
- [ ] Future stories can reference this document to prevent mistakes

### Expected Output

**Deliverable:** `gws_project_reference_patterns.md` in `planning-artifacts/` folder

**Document Structure:**
1. Executive Summary
2. Entity Patterns (with code examples)
3. Naming Conventions (with rules and examples)
4. Service Layer Patterns (with templates)
5. Test Patterns (with examples)
6. gws_eln Alignment Strategy

**Usage:** This document becomes the **bible** for all future development work in gws_eln.

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

**Files to Create:**
- `planning-artifacts/gws_project_reference_patterns.md`

**Files to Study:**
- `/lab/user/bricks/others/gws_project/src/gws_project/**/*.py` (entities and services)
- `/lab/user/bricks/others/gws_project/tests/**/*.py` (test patterns)
- `/lab/user/bricks/gws_core/src/gws_core/model/*.py` (base model classes)
