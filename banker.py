# banker.py
from typing import List, Dict

class BankersAlgorithm:
    """
    Python implementation of the Banker's Algorithm equivalent from your Java code.
    allocation: list of list (processes x resources)
    maximum: list of list (processes x resources)
    available: list (resources)
    """

    def __init__(self, allocation: List[List[int]], maximum: List[List[int]], available: List[int]):
        self.allocation = allocation or []
        self.maximum = maximum or []
        self.available = available[:] if available else []
        self.processes = len(self.allocation)
        self.resources = len(self.available)
        self.need = [[0] * self.resources for _ in range(self.processes)]
        self._calculate_need()

    def _calculate_need(self):
        for i in range(self.processes):
            for j in range(self.resources):
                try:
                    self.need[i][j] = self.maximum[i][j] - self.allocation[i][j]
                except Exception:
                    self.need[i][j] = 0

    def get_result(self) -> Dict:
        """
        returns dict:
        {
            "safe": bool,
            "sequence": [0-based process indices],
            "message": str
        }
        """
        finish = [False] * self.processes
        work = self.available[:] if self.available else [0]*self.resources
        safe_seq = []

        count = 0
        while count < self.processes:
            found = False
            for p in range(self.processes):
                if not finish[p]:
                    can_finish = True
                    for j in range(self.resources):
                        if self.need[p][j] > work[j]:
                            can_finish = False
                            break
                    if can_finish:
                        for k in range(self.resources):
                            work[k] += self.allocation[p][k]
                        safe_seq.append(p)
                        finish[p] = True
                        found = True
                        count += 1
            if not found:
                return {"safe": False, "sequence": [], "message": "⚠ System is NOT in a safe state."}

        seq_str = "--->".join("P{}".format(i+1) for i in safe_seq)
        message = "✅ System is in a safe state.\nSafe Sequence: " + seq_str
        return {"safe": True, "sequence": safe_seq, "message": message}
# banker.py
def is_safe_state(total_available, allocations, max_demands):
    """
    Classic Banker's Algorithm safe state check
    Returns (is_safe, safe_sequence)
    """
    n = len(allocations)
    m = len(total_available)
    work = total_available[:]
    finish = [False] * n
    safe_seq = []

    while len(safe_seq) < n:
        progress = False
        for i in range(n):
            if not finish[i]:
                need = [max_demands[i][j] - allocations[i][j] for j in range(m)]
                if all(need[j] <= work[j] for j in range(m)):
                    work = [work[j] + allocations[i][j] for j in range(m)]
                    finish[i] = True
                    safe_seq.append(i)
                    progress = True
        if not progress:
            return False, safe_seq
    return True, safe_seq
