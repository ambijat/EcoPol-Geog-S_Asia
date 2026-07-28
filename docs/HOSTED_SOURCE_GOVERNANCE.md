---
status: APPROVED
authority: INSTRUCTOR_RULING
approved_date: 2026-07-21
document_role: SUBORDINATE_GOVERNANCE
---

# Hosted Source Governance

## Purpose and authority

The hosted Wikidot site is the course's inherited reference and distribution layer. It may provide evidence of historical organisation, publication, linked readings, maps, datasets, and other resources. It is not the authoritative Semester 2026 archive. The controlled active project, its instructor-approved classroom deliverables, and its authorised academic records remain authoritative for Semester 2026.

## Three-layer architecture

1. **Active writable project:** governance, registration records, controlled working derivatives, classroom deliverables, validation reports, and authorised ledger records.
2. **Historical read-only repository:** immutable original sources and evidence of previous course development.
3. **Hosted reference and distribution layer:** externally hosted pages, attachments, and links whose availability or publication does not establish authority, currency, or identity.

## Controlled terminology

- **Original source:** an immutable historical, instructor, or external source in its received form.
- **Registered source:** an original source whose identity, location, checksum where locally available, and minimum metadata have been entered in the controlled registry.
- **Controlled working derivative:** a project-owned working file derived from one or more sources with traceable provenance and transformation history.
- **Sanitised working derivative:** a controlled working derivative for which an actual sanitisation process has removed or isolated identified technical, privacy, security, accessibility, or presentational risks. This term must not be used when no sanitisation occurred.
- **Classroom deliverable:** an instructor-reviewed teaching output such as an editable lecture deck, classroom PDF, teaching brief, source map, verification record, handout, dataset, exercise, or post-class record.

## Intake, identity, and provenance

Hosted appearance, matching filenames, titles, lecture numbers, or apparent dates do not prove that remote and local items are identical. Filename-only identity claims are prohibited.

Where remote bytes have been deliberately retrieved, SHA-256 comparison should be used to test byte identity against a local candidate. A checksum match establishes byte identity only; it does not establish factual currency, pedagogical suitability, or instructor approval.

Before pedagogical reuse, a hosted source must have adequate provenance, source classification, factual verification, and a documented relationship to any controlled working derivative or classroom deliverable.

## Prohibited actions

Without explicit instructor authorisation, no agent may:

- crawl or systematically traverse the hosted site;
- download or capture hosted attachments or linked files;
- traverse Google Drive or other external storage links;
- republish hosted content;
- modify remote pages, attachments, metadata, or permissions;
- treat a live or historically published item as approved Semester 2026 content.

Authorisation to inspect or capture hosted material never authorises modification of the historical read-only repository.

## Teaching and publication threshold

Only instructor-approved classroom deliverables may be taught or published. Registration, checksum comparison, sanitisation, factual verification, Git tracking, repository validation, or ledger inclusion does not independently confer teaching or publication approval.

## Audit separation

Dated page revisions, link counts, access observations, redirect behaviour, filename overlaps, and other page-specific findings belong in `online_sources/references-ma_audit.md` or later authorised audit reports. Such observations are evidence, not normative governance.
