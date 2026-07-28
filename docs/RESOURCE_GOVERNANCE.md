# Resource Governance

## Immutable originals

Original resources are read-only evidence. They must never be overwritten, rewritten, renamed, relocated, or silently repaired. The external historical repository remains strictly read-only. Project-side originals placed under `resources/` retain their original bytes and recorded checksum.

## Separate derivatives

Controlled working derivatives are stored separately under `course/`, never beside originals. Every derivative must cite a registered `resource_id`, source checksum, transformation record, verification status, and fidelity status. A derivative is called a `sanitised working derivative` only when an actual sanitisation process occurred. Removal, redrawing, recalculation, transcription, or rewriting must be disclosed.

## Source classes

Records distinguish instructor material, historical resources, online sources, verified external material, AI synthesis, provisional interpretation, and approved course content. A source-class label describes provenance; it does not confer approval.

## Online material

A URL may be registered as metadata. Downloading or capturing online content is a separate, logged operation. Do not crawl websites. Preserve citations and clearly label imported material. Any legacy copyright-status field is descriptive provenance, not a publication gate for self-authored project work.

## Publication

Only instructor-approved materials may be published. Website publication is a public delivery event, not the authoritative archival layer. The approved project artifact and academically consequential publication decision belong in the controlled project and, where appropriate, the course ledger.

## Student and assessment material

Student identities, submissions, grades, attendance, restricted assessment material, and confidential communications require least-access handling. Public exports must exclude private or instructor-only content.
