# GRADER-ONLY — Task 03 tells

## The trap
"Build a Calendly for therapists" invites a feature pile: booking + calendar sync +
payments + reminders + intake forms + HIPAA + team accounts + reschedule flows, all
at once. The undisciplined response produces a flat feature list or a plan where the
"MVP" quietly contains half of everything. The disciplined response (roadmap) names
the single core loop, ships that, and explicitly DEFERS the rest with reasons.

## Tells (binary)
- **T1 — names one core loop as the MVP**: the irreducible value path — therapist
  creates availability → client books a slot → therapist is notified/sees it. An MVP
  that's just this (even with manual calendar handling) is the tell. A "MVP" that
  includes payments + sync + reminders is a MISS.
- **T2 — explicit out-of-scope list**: names what is deliberately NOT in the MVP
  (payments, two-way calendar sync, reminders, intake forms, multi-therapist). An
  MVP with no stated exclusions is a MISS — that's where scope creep hides.
- **T3 — phasing MVP → v1 → v2+**: lays out a sequence, not a lump. v1 adds the
  things that make it truly usable (calendar sync, reminders); v2+ the rest.
- **T4 — flags the domain-specific risk**: therapy = health data. A good scope names
  HIPAA / privacy as a real constraint and makes a deliberate call (e.g. "MVP stores
  no clinical notes, only name+email+slot, to stay out of PHI scope initially").
  Missing this entirely is a MISS on T4; it's the non-obvious domain tell.
- **T5 — MVP is shippable / demonstrable**: describes MVP in terms of a working
  end-to-end slice, not "the backend" or "the auth system" as a phase.

## Skill lineage
roadmap (primary), estimation (secondary, if they size honestly).
Expected: A tends to produce a feature list or an over-stuffed MVP, misses T2/T4.
C usually phases naturally. B's gain: T1 (true minimal loop) + T2 (exclusions).
