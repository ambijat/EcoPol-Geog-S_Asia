# Browser-First and Qt-Sidecar Architecture

Status: `GOVERNING_ARCHITECTURAL_INJUNCTION`

Effective: 2026-07-22

Implementation status: `KC01_BROWSER_PILOT_IMPLEMENTED`

## Governing rule

The browser-based cockpit is the preferred and primary instructor-facing interface for IS529N. It must support browser-capable desktop, laptop and tablet use across Ubuntu, Windows and other suitable platforms through responsive layouts.

The Qt application is preserved and supported as an ancillary native sidecar. Its preferred scope is protected local file-system work, historical-resource inspection, LibreOffice conversion, PDF and thumbnail generation, local-folder opening, and genuinely offline or desktop-dependent operations. Qt must not become a separate academic system or source of truth.

## Shared state and services

Both adapters must use the same governed data model, titles, classifications, triangulation records, decisions, artefact statuses and versioning rules. No workflow may create conflicting browser and Qt records.

The preferred dependency direction is:

```text
shared application/domain services
→ browser adapter
→ Qt adapter
```

Business logic must not be independently reimplemented in both interfaces. Generic logic currently located under `qt_gui/services` should be considered for extraction into an interface-neutral service layer before browser parity is added.

## Browser parity priorities

1. Supervisor Home
2. Lecture navigation
3. Artefact map
4. Instructor decision queue
5. Triangulation workspace
6. Note review
7. Slide-plan review
8. PDF and thumbnail review
9. Student-note review
10. Registry-candidate review
11. Session review records

Instructor workflows that do not require native desktop capability should be prioritised for safe browser parity. Native conversion, protected historical-file inspection and desktop shell integration remain sidecar responsibilities.

## Responsive interaction

Browser workflows must remain usable on large monitors, laptops, tablets and narrower windows. Tablet presentation should favour stacked evidence panels, readable typography, large touch targets, collapsible technical detail and simplified decision controls rather than fixed desktop geometry.

## Security and locality

Browser-first does not imply public access. The browser cockpit may remain local, private, LAN-restricted or otherwise access-controlled.

Browser responses must not expose:

- absolute filesystem paths;
- private historical-resource locations or protected source bytes;
- unpublished notes without explicit authorised review context;
- database files or internals;
- canonical ledger internals; or
- local-only artefacts outside their governed access boundary.

Browser-safe presentation models should use governed identifiers, symbolic locators and redacted metadata. Any LAN or non-loopback deployment requires a separately authorised access-control and request-integrity design.

## Current review boundary

Lecture 1A `v0.4` review may be conducted through either interface, but the review record and decisions must remain interface-neutral and shared. The local review record is not a canonical ledger event.

The separately authorised KC01 reinforcement pilot implements a bounded browser vertical slice. It does not authorise a general migration of every Qt workflow or expansion beyond Lecture 1A KC01.

## Current-state assessment

The evidence-based parity assessment, native-capability classification, required shared-service refactoring and divergence risks are recorded in `reports/instructor_review/lecture_01_part_a_v0.4_review.md` under “Browser-first architectural injunction”.
