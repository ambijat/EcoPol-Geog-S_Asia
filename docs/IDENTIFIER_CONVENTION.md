# Identifier Convention

## Resources

Registered resources use an immutable, sequential identifier:

```text
IS529N-RES-0001
```

Identifiers are never reused, renumbered, or derived from filenames. A changed byte sequence is a new resource version or derivative and must not silently inherit the identity of the original.

## Lecture-part identifiers

Semester 2026 lecture parts use:

```text
IS529N-L01-A
IS529N-L01-B
IS529N-L02-A
IS529N-L02-B
```

`A` is normally Tuesday and `B` is normally Friday. Historical Part C files are supplementary exceptions and do not create a third canonical weekly part.

Recommended derivative names are:

```text
IS529N_L01A_<short_topic>.pptx
IS529N_L01A_<short_topic>.pdf
IS529N_L01B_<short_topic>.pptx
IS529N_L01B_<short_topic>.pdf
```

This convention applies only to Semester 2026 derivatives and new outputs. Historical originals are never renamed.

## Other suggested derivative identifiers

Controlled working derivatives may use `IS529N-DER-0001`; teaching modules may use `IS529N-MOD-01`. A sanitised working derivative retains its derivative identifier and records the sanitisation action in its provenance. These identifiers supplement, but never replace, the registered source ID and checksum.

## Paths and titles

Paths are storage locations, titles are descriptive labels, and identifiers are stable identities. Renaming a project derivative does not change its identifier. External absolute paths and URLs may be recorded as source locations but must not be treated as portable project paths.
