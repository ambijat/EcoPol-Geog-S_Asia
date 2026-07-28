# Lecture Reinforcement Workflow

The Lecture Reinforcement Workspace helps renew an existing lecture without losing what made the inherited lecture teachable.

Use it in this order:

```text
Choose lecture
→ choose cluster
→ inspect old slides
→ inspect aligned resources
→ generate patterns
→ choose pattern
→ reinforce
→ rehearse
→ accept
```

## The current pilot

The active pilot is Lecture 1A, “South Asia as a Region”. It works only with KC01, “Regional imagination and ways of knowing South Asia”, covering historical slides 3–18.

The remaining five clusters are visible so that the whole lecture can be understood, but they are locked during this pilot.

## Using the workspace

Open **Lecture Reinforcement** in the browser.

1. **Open Historical Lecture** shows slides 3–18 without changing the inherited file. Record whether each old slide should be kept, updated, merged, moved or otherwise treated. For the Slide 3 pilot, recording `UPDATE`, `EXPAND`, `MERGE`, `SPLIT`, `REPLACE`, `CREATE_NEW` or `MOVE_TO_NOTES` exposes **Prepare Update Corpus**. Copy or download the packet, use it in an external ChatGPT conversation, paste the returned YAML, validate it, make an instructor edit, apply it manually, attach the derivative and accept or return the reinforced slide.
2. **Select Knowledge Cluster** confirms that KC01 is the cluster under review.
3. **Find Aligned Resources** shows only the indexed LEC_RES_1 source profiles. Decide how each source should be used; no source is registered automatically.
4. **Extract Knowledge Units** creates small, traceable teaching units instead of whole-document summaries. Decide whether each belongs in the cluster, a slide, notes or reading.
5. **Generate Knowledge Patterns** offers alternative ways to arrange the selected material. The six rotation buttons change the analytical viewpoint.
6. **Choose Pattern** asks for an explicit instructor confirmation. Selection alone is not confirmation.
7. **Reinforce Slides** places historical lineage beside proposed slides. Record a decision for every proposal.
8. **Rehearse Cluster** provides student-facing slides, notes, evidence, transitions and a timer. Record teaching comments while rehearsing.
9. **Accept Cluster** shows timing, evidence, visual and sequence problems before accepting or returning the cluster.
10. **Build Next Lecture Version** remains locked until every required cluster has been accepted.

## Important boundaries

- The historical lecture remains unchanged.
- Generated patterns and slides are proposals, not decisions.
- Instructor confirmation is always explicit.
- The workspace does not run AI.
- The Slide 3 packet separates direct slide evidence from wider cluster context. Missing page evidence is shown as missing rather than inferred.
- AI-assisted structured material, if pasted into the workspace, remains a draft requiring review.
- Cluster acceptance is local and does not publish, register or append anything.
- This pilot cannot build `v0.5`.
