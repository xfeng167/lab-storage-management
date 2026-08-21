# User Acceptance Report

This report explains what users experienced while operating the deployed Lab
Storage Management application as a small regional laboratory network. It is
written for a beginner software development engineer (SDE), so each finding
connects visible user behavior to a concrete engineering lesson.

## 1. What Was Tested

User acceptance testing (UAT) asks a practical question:

> Can real users complete realistic work safely and understand the result?

The exercise used the deployed application through its browser interface. It did
not access the database directly, call undocumented endpoints, run a load
generator, or modify production code.

The workspace started empty. The exercise created a fictional consortium of four
institutions:

- Cascadia State University
- Northbridge University
- Harborview Medical College
- Redwood Institute of Technology

The finished demonstration dataset contains:

- 9 new user accounts
- 15 storage locations
- 12 laboratory materials
- 10 material requests
- 164 units on hand
- 24 visible inventory audit records

The original administrator account was not changed. No credentials are included
in this report.

## 2. Overall Result

The application supports the main laboratory workflow:

1. Staff create storage locations and materials.
2. An administrator records inventory.
3. Researchers browse materials and submit requests.
4. An administrator approves, rejects, fulfills, or cancels requests.
5. Reports and audit records explain the resulting inventory changes.

The most important inventory rules behaved correctly. Approval reserved stock,
fulfillment consumed stock, and canceling an approved request released its
reservation. A competing request could not reserve more material than remained
available.

The system is suitable for continued demonstrations, with one important
onboarding issue: repeated role changes were unreliable. Only two of the three
intended staff assignments persisted.

No server error, authorization bypass, inventory inconsistency, unexpected data
change, or repeated response slower than eight seconds was observed. All browser
sessions were signed out at the end.

## 3. Users and Roles

The application uses three roles:

- **Viewer** is the researcher/requester role.
- **Staff** manages material metadata, locations, and operational reports.
- **Admin** also manages inventory, users, audit history, and all requests.

The created accounts ended in this state:

| ID | Username | User perspective | Final role |
| ---: | --- | --- | --- |
| 2 | `maya_chen` | Regional platform administrator | Admin |
| 3 | `olivia_brooks` | Cascadia laboratory operations | Staff |
| 4 | `daniel_kim` | Northbridge researcher | Viewer |
| 5 | `priya_shah` | Harborview laboratory operations | Staff |
| 6 | `ethan_wu` | Cascadia researcher | Viewer |
| 7 | `sofia_martinez` | Northbridge researcher | Viewer |
| 8 | `noah_johnson` | Harborview researcher | Viewer |
| 9 | `ava_patel` | Intended Redwood operations account | Viewer |
| 10 | `liam_carter` | Redwood researcher | Viewer |

The intended result was one new admin, three staff members, and five
researchers. The actual result was one admin, two staff members, and six viewers
because one staff role could not be assigned reliably.

## 4. Storage Network Created

The product supported a useful parent-child location hierarchy. The final
structure is:

```text
Cascadia State University
└── CSU Molecular Biology Core
    └── Cascadia Room B214
        └── CSU Freezer FZ-01
            └── Cascadia Freezer Shelf A

Northbridge University
└── Northbridge Chemical Sciences
    └── Northbridge Cold Room C07

Harborview Medical College
└── Harborview Translational Medicine
    └── Harborview Freezer HF-20
        └── Harborview Control Box C

Redwood Institute of Technology
└── Redwood Bioengineering Center
    └── Redwood Cryostorage Room R3
```

This exercised institution, department, room, freezer, shelf, and box levels.
Users could also record a temperature zone and a plain-English description.

## 5. Materials and Final Inventory

The catalogue included reagents, consumables, biological reference materials,
and controls. Quantities below are the final values after request processing.

| ID | Code | Material | Type | QC | On hand | Reserved |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 1 | CSU-REAG-001 | Tris-HCl Buffer 1 M pH 8.0 | Reagent | Passed | 18 bottles | 0 |
| 2 | CSU-REAG-002 | PCR Master Mix 2X | Reagent | Passed | 6 kits | 0 |
| 3 | NBU-CONS-001 | Sterile Pipette Tips 200 uL | Consumable | Passed | 36 boxes | 0 |
| 4 | RIT-CONS-001 | Cryogenic Storage Vials 2 mL | Consumable | Passed | 24 packs | 4 |
| 5 | HMC-BIO-001 | Human Genomic DNA Reference NA12878 | Biological reference | Passed | 5 vials | 0 |
| 6 | HMC-BIO-002 | E. coli K-12 Genomic DNA Reference | Biological reference | Pending | 4 vials | 0 |
| 7 | HMC-CTRL-001 | Positive Amplification Control RNA | Control | Passed | 1 vial | 0 |
| 8 | CSU-CTRL-001 | Negative Extraction Control | Control | Passed | 10 vials | 0 |
| 9 | NBU-REAG-001 | Sodium Chloride USP | Reagent | Passed | 11 bottles | 0 |
| 10 | NBU-REAG-002 | Bovine Serum Albumin Fraction V | Reagent | Pending | 7 bottles | 0 |
| 11 | RIT-CONS-002 | Nitrile Examination Gloves Medium | Consumable | Passed | 40 boxes | 0 |
| 12 | CSU-CTRL-002 | DNA Ladder 1 kb | Control | Failed | 2 vials | 0 |

The dashboard correctly reported 12 active materials, 164 total units on hand,
two low-stock materials, and no submitted requests after processing finished.

## 6. User Journeys

### Journey A: Laboratory staff prepares the workspace

Olivia signed in as Staff and created the location hierarchy and material
catalogue.

What worked well:

- Staff saw Locations and Reports but not Users or Audit Log.
- Location forms supported parents, types, temperature zones, and descriptions.
- Material forms supported codes, units, minimum quantities, QC status, storage
  conditions, locations, descriptions, and sources.
- Material types automatically became useful catalogue filters.

User outcome: a researcher could understand what a material was, where it was
stored, its QC state, and whether sufficient stock was available.

### Journey B: Administrator establishes inventory

Maya signed in as Admin and checked in the opening quantity for every material.
She also recorded one routine checkout of Sodium Chloride USP.

Observed changes:

- Initial Sodium Chloride check-in: `0 -> 15 bottles`
- Routine checkout: `15 -> 14 bottles`
- Later request fulfillment: `14 -> 11 bottles`

Every operation appeared in the audit history with the actor, reason, time, and
before/after quantity.

### Journey C: Researchers request materials

Five researchers browsed the catalogue and submitted ten requests with realistic
scientific-use notes. Examples included buffer preparation, genotyping, assay
validation, environmental DNA extraction, and cryostorage expansion.

Researchers saw only Overview, Inventory, and Requests. A direct attempt to open
the admin user directory returned a clear access-restricted page.

### Journey D: Administrator reviews requests

The request queue exercised every supported transition:

| Request | Material | Final result |
| ---: | --- | --- |
| 1 | Sodium Chloride USP | Fulfilled |
| 2 | Positive Amplification Control RNA | Fulfilled |
| 3 | PCR Master Mix 2X | Fulfilled |
| 4 | Negative Extraction Control | Canceled after approval |
| 5 | Bovine Serum Albumin Fraction V | Rejected because QC was pending |
| 6 | Positive Amplification Control RNA | Rejected after insufficient-stock check |
| 7 | Human Genomic DNA Reference NA12878 | Fulfilled |
| 8 | E. coli K-12 Genomic DNA Reference | Rejected because QC was pending |
| 9 | Cryogenic Storage Vials 2 mL | Approved and reserved for pickup |
| 10 | Nitrile Examination Gloves Medium | Canceled by the requester |

The approved cancellation for request 4 demonstrated reservation release:

```text
Before approval:    10 on hand, 0 reserved
After approval:     10 on hand, 2 reserved
After cancellation: 10 on hand, 0 reserved
```

This is an important invariant: canceling an approved request must release the
reservation without consuming physical stock.

## 7. Low-Stock Contention Example

Contention means that two users want more of the same material than the system
can safely allocate.

Two researchers requested two vials each of Positive Amplification Control RNA.
The material had three vials on hand and a minimum quantity of three, so it was
already marked Low Stock.

| Step | On hand | Reserved | Requestable | Request 2 | Request 6 |
| --- | ---: | ---: | ---: | --- | --- |
| Before review | 3 | 0 | 3 | Submitted | Submitted |
| Approve request 2 | 3 | 2 | 1 | Approved | Submitted |
| Try to approve request 6 | 3 | 2 | 1 | Approved | Submitted |
| Finish processing | 1 | 0 | 1 | Fulfilled | Rejected |

The second approval displayed:

```text
Insufficient unreserved stock to approve order
```

The second request remained Submitted until the administrator rejected it.
Inventory did not change during the failed approval.

### Engineering lesson

The safety rule belongs in the backend transaction, not only in the browser.
Two browser screens can both display old availability. The server must lock or
atomically update the material row, calculate `on hand - reserved`, and allow
only one valid reservation.

Add a database-backed concurrency test that starts two approvals for the same
low-stock material and asserts:

- at most one approval succeeds;
- reserved quantity never exceeds on-hand quantity;
- the failed request stays Submitted;
- no audit record is written for the failed transition.

## 8. Role Experience

| Role | Navigation observed | Important actions |
| --- | --- | --- |
| Viewer | Overview, Inventory, Requests | Browse, request, view own requests, cancel eligible own requests |
| Staff | Overview, Inventory, Requests, Locations, Reports | Viewer actions plus material and location management |
| Admin | All staff pages plus Audit Log and Users | Inventory operations, user roles, and all-request review |

The visible navigation and direct route protection matched the intended role
model. Backend authorization must remain the source of truth because hiding a
button is not a security boundary.

## 9. Findings by Priority

### P0: No critical defect observed

No authorization bypass, over-reservation, negative quantity, unexpected data
change, or server failure was observed.

### P1: Role assignment is unreliable

**What the user saw:** An administrator changed several user roles. Some changes
persisted, while others reverted to Viewer. The page displayed:

```text
User roles are being updated; retry the request
```

The alert remained visible after reloading the page and signing in as a different
administrator.

**Why it matters:** A new organization cannot onboard staff reliably. The final
workspace had only two Staff accounts instead of three.

**Expected behavior:** Each role selector should save independently, show progress
only for that user, and finish with a clear success or failure result.

**Recommended first fix:** Store pending state by user ID instead of using one
page-wide `isUpdating` flag. Disable only the affected row, await the request,
refresh that user's confirmed role, and clear pending state in `finally`.

**Acceptance criteria:**

- Five consecutive role changes persist without a reload.
- A failed update restores only the affected selector.
- A later role change is not blocked by an earlier failure.
- Reloading the page shows the server-confirmed roles.
- Automated tests cover success, failure, and rapid consecutive changes.

### P2: Requester names are hidden from administrators

**What the user saw:** The request queue displayed `User #4`, `User #7`, and
similar labels instead of usernames.

**Why it matters:** An administrator must cross-reference IDs before making an
operational decision.

**Recommended fix:** Include a safe requester summary in the order response, or
join it in the service layer, and display `daniel_kim (#4)`.

### P2: The active request count includes terminal requests

**What the user saw:** A researcher with one Submitted request and one Canceled
request still saw `2 active requests`.

**Why it matters:** The count overstates actionable work.

**Recommended fix:** Define active statuses explicitly, for example Submitted and
Approved, and calculate both the heading and table filter from the same rule.

### P2: Quantity text does not handle singular units

**What the user saw:** The interface displayed `1 vials`.

**Recommended fix:** Add one shared quantity formatter and test zero, one, and
multiple units.

### P2: Audit changes expose raw JSON

**What the user saw:** Dashboard and report entries displayed objects such as:

```json
{"quantity_available": 3, "quantity_reserved": 2}
```

**Why it matters:** Laboratory users should not need to understand the backend
storage format.

**Recommended fix:** Render labeled values such as `Available: 3 -> 1` and
`Reserved: 2 -> 0`. Raw JSON can remain in an expandable technical-details view.

## 10. Verified, Suspected, and Not Tested

### Verified

- Authentication and explicit sign-out
- Viewer, Staff, and Admin navigation boundaries
- Direct protection of an admin-only route
- Hierarchical location creation
- Material creation with mixed types and QC states
- Inventory check-in and checkout
- Request submission, approval, rejection, fulfillment, and cancellation
- Reservation creation and release
- Insufficient-stock handling
- Dashboard, reports, and inventory consistency
- Order-driven inventory audit records

### Suspected product questions

- A Failed-QC material appears in the general low-stock list. The team should
  decide whether failed or quarantined stock belongs in replenishment reporting.
- Pending-QC materials can be requested. The team should decide whether to block
  submission, warn the requester, or continue enforcing QC only during review.

### Not tested

- Parallel load or large-scale performance
- Password change and recovery
- Profile image upload
- Material and request archival
- Material movement between locations
- Mobile layouts and additional browsers
- Session expiration
- External email or identity integrations

## 11. Recommended Learning Order for a Beginner SDE

1. Reproduce the role-update bug locally with the smallest possible automated
   test.
2. Trace the action from React event handler to API client, FastAPI route,
   service, transaction, and returned response.
3. Fix pending/error state so one failed request cannot block unrelated rows.
4. Add integration tests for all order transitions and their audit records.
5. Add a real concurrent-approval test around the inventory invariant.
6. Define QC policy before adding new QC or shipment features.
7. Improve user-facing names, counts, pluralization, and audit formatting.
8. Run lint, frontend tests, backend tests, and a production build before asking
   a user to repeat UAT.

The most valuable lesson is that a green happy-path test is not enough. A safe
inventory system must preserve its rules when requests fail, overlap, are
canceled, or are retried, and it must explain the result clearly to the person
using it.
