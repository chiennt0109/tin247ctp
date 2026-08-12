"""Global blueprint assignment (question and family all-different)."""

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Demand:
    slot: object
    ordinal: int
    candidates: tuple


def solve_slot_assignment(slots, candidate_provider, *, seed=None):
    """Return ``[(slot, question), ...]`` or ``None`` using backtracking.

    Most-constrained-first search avoids the classic greedy failure where an
    early broad slot consumes the sole candidate of a later narrow slot.
    Candidate ordering is stable and is then deterministically randomized by
    the persisted seed.
    """
    rng = random.Random(str(seed))
    demands = []
    for slot in slots:
        candidates = list(candidate_provider(slot))
        rng.shuffle(candidates)
        for ordinal in range(slot.quantity):
            demands.append(Demand(slot, ordinal, tuple(candidates)))
    demands.sort(key=lambda demand: (len(demand.candidates), demand.slot.pk, demand.ordinal))
    chosen, used_questions, used_families = {}, set(), set()

    def search(index):
        if index == len(demands):
            return True
        demand = demands[index]
        for question in demand.candidates:
            family = question.duplicate_family_id or None
            if question.pk in used_questions or (family and family in used_families):
                continue
            used_questions.add(question.pk)
            if family:
                used_families.add(family)
            chosen[demand] = question
            if search(index + 1):
                return True
            del chosen[demand]
            used_questions.remove(question.pk)
            if family:
                used_families.remove(family)
        return False

    if not search(0):
        return None
    # Restore blueprint order, independent of MRV search order.
    return [(demand.slot, chosen[demand]) for demand in sorted(
        demands, key=lambda demand: (demand.slot.section.order, demand.slot.order, demand.slot.pk, demand.ordinal)
    )]
