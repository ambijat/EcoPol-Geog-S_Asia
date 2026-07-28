# Slide-Level External-AI Bridge

This browser workflow helps revise Historical Slide 3 without sending files or calling an AI service from the cockpit.

The working sequence is:

```text
Choose action
→ add your instruction
→ prepare corpus
→ copy to ChatGPT
→ paste revision back
→ validate
→ edit
→ fix the slide
→ attach
→ accept
```

## Preparing the packet

Open Lecture 1A and Stage 1. On Slide 3, choose an action and write a specific intervention note. After recording the decision, select **Prepare Update Corpus**.

The packet contains the inherited slide, visible references, slide-specific sources, nearby lecture context and your instruction. Wider KC01 sources are shown separately as context. Missing page-level evidence is identified as missing and is never inferred from a filename or title.

Select **Copy for ChatGPT** to copy the complete packet, or **Download Packet** to save the local Markdown file. The cockpit does not send the packet anywhere.

## Bringing a revision back

After using the packet externally, mark it as sent and paste the returned YAML into **Paste AI-Assisted Revision**. Validation checks the structure, Slide 3 identity, sources, citations and prohibited approval language.

A valid result remains labelled `AI_ASSISTED_DRAFT` and `REQUIRES_INSTRUCTOR_REVIEW`.

## Completing the slide

Compare the inherited and proposed versions. Open the instructor editing view, make your own changes or explicitly waive editing, and then update the working slide manually.

Record where the manual work was applied. Attach a local derivative or provide a symbolic reference and checksum. Only then can the reinforced slide be accepted locally.

Acceptance does not alter the historical slide, approve the deck, build v0.5, publish material, register a source or append the ledger.
