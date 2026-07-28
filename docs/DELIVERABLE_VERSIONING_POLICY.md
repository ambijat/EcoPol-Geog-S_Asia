# IS529N Deliverable Versioning Policy

Status: operational policy for local course-production deliverables. It does not itself approve any deck for classroom use or publication.

## Names and progression

- The first generated working draft is `IS529N_L01A_v0.1_DRAFT.pptx`.
- Each subsequent draft or revision increments the zero-major minor version: `v0.2_REVISED`, `v0.3_REVISED`, and so on.
- The first explicitly approved output is `v1.0_APPROVED`.
- A later approved correction increments the approved minor version (`v1.1`, `v1.2`). A new major version requires a separately documented instructor decision.

The lecture number and part are embedded in the filename. Part A is Tuesday and Part B is Friday.

## Non-overwrite and immutability

Generation must fail if the selected output filename already exists. Every deliverable receives a recorded checksum. Rendering refuses to proceed if the PPTX checksum no longer matches its bundle record, and thumbnail generation applies the same rule to the PDF.

Approved files are immutable. Corrections create a new version and must not replace the approved bytes. Approval requires all retained slides to be verified and instructor-approved, the lecture part to be at fidelity F4, and validation errors to be resolved. Warnings require an explicit instructor override note.

## Bundle contents

Each version is represented by an editable PPTX, provenance sidecar, teaching brief, validation report, and—when rendering succeeds—a PDF and slide thumbnails. All remain local-only until separately reviewed and authorised for publication.
