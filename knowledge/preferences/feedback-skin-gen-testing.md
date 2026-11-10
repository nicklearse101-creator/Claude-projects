---
name: feedback-skin-gen-testing
description: "Skin generator - test on the cars Nik actually uses, not random batches; don't rebuild the installer unless the problem is significant"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 7bc58086-8268-4a36-9c4f-30a7e0b6caf0
  modified: 2026-11-10T22:02:14.347Z
---

For Ratty's4Skin Generator: no more random 30-car batch tests, and no installer rebuild after every change.

**Why:** Nik 2026-11-10: "that random 30 car test is pointless" - he found many faults on just 2 cars (Talbot,
Kadett) that the batch never caught; it only checks for crashes and wastes time. "dont build any more unless it's a
significant problem."

**How to apply:** test changes on the cars Nik is using (his saved settings via tests/nik_test.py, plus the car in his
screenshot) and look at the preview pictures closely, every view, before saying it's done. Keep work in source + git;
build the installer only for a significant fix or when Nik asks. Related: [[ac-skin-generator-project]].
