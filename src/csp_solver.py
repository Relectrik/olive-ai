"""
Project done by Emilio Martin Del Campo
"""

"""
Calendar Satisfaction Problem (CSP) Solver
Designed to make scheduling those meetings a breeze! Suite of tools
for efficiently scheduling some n meetings in a given datetime range
that abides by some number of constraints.

In this module:
- A solver that uses the backtracking exact solver approach
- Tools for pruning domains using node and arc consistency
"""
from datetime import *
from date_constraints import *
from dataclasses import *
from copy import *


# CSP Backtracking Solver
# ---------------------------------------------------------------------------
def solve(
    n_meetings: int, date_range: set[datetime], constraints: set[DateConstraint]
) -> Optional[list[datetime]]:
    """
    When possible, returns a solution to the given CSP based on the need to
    schedule n meetings within the given date range and abiding by the given
    set of DateConstraints.
      - Implemented using the Backtracking exact solution method
      - May return None when the CSP is unsatisfiable

    Parameters:
        n_meetings (int):
            The number of meetings that must be scheduled, indexed from 0 to n-1
        date_range (set[datetime]):
            The range of datetimes in which the n meetings must be scheduled; by default,
            these are each separated a day apart, but there's nothing to stop these from
            being meetings scheduled down to the second
            [!] WARNING: AVOID ALIASING -- Remember that each variable must have its
            own domain but what's provided is a single reference to a set of datetimes
        constraints (set[DateConstraint]):
            A set of DateConstraints specifying how the meetings must be scheduled.
            See DateConstraint documentation for different types of DateConstraints
            that might be found, and useful methods for implementing this solver.

    Returns:
        Optional[list[datetime]]:
            If a solution to the CSP exists:
                Returns a list of datetimes, one for each of the n_meetings, where the
                datetime at each index corresponds to the meeting of that same index
            If no solution is possible:
                Returns None
    """
    new_date_range = set()
    for date in date_range:
        for hour in range(24):
            hour_date = datetime.combine(date, time(hour))
            new_date_range.add(hour_date)
    domains = {i: new_date_range.copy() for i in range(n_meetings)}
    node_consistency(list(domains.values()), constraints)

    arc_consistency(list(domains.values()), constraints)

    solution = recursive_backtracker([], list(range(n_meetings)), domains, constraints)

    if solution:
        return [date for _, date in solution]
    else:
        return None


def recursive_backtracker(
    assignment: List[Tuple[int, datetime]],
    variables: List[int],
    domains: Dict[int, Set[datetime]],
    constraints: Set[DateConstraint],
) -> Optional[List[Tuple[int, datetime]]]:
    """
    Reursively tracks through all assignment option available by assigning values
    to variables and then checking if any constraints are violated.

    Parameters:
        assignment (list[(int, datetime)]):
            The current assignment of variables and their values.
        variables (list[int]):
            The variables to be assigned.
        domains (dict[int, set[datetime]]):
            The domains for each variable
        constraints (set[DateConstraint]):
            A set of constraints for the assignment to follow.

    Returns:
        list[(int, datetime)] or None:
            Either an assignement that does not violate any constraints or None if
            no valid assignment is available.
    """
    if len(assignment) == len(variables):
        return assignment

    next_var = select_unassigned_variable(variables, assignment)
    if next_var is None:
        return None
    for value in order_domain_values(domains[next_var]):
        assignment.append((next_var, value))
        if is_consistent(assignment, constraints):
            result = recursive_backtracker(assignment, variables, domains, constraints)
            if result is not None:
                return result
        assignment.pop()

    return None


def select_unassigned_variable(
    variables: List[int], assignment: List[Tuple[int, datetime]]
) -> Optional[int]:
    """
    Determines what variable to assigne next taking care not to select
    a variable that is already being used in the assignment.

    Parameters:
        variables (list[int]):
            The variable to be assigned.
        assignment (list[(int, datetime)]):
            The current  assignment of variables and their values.

    Returns:
        int or None:
            A variable to assign next or None if no variables are available..
    """

    for var in variables:
        if var not in [assignment_var for assignment_var, _ in assignment]:
            return var
    return None


def order_domain_values(domain: Set[datetime]) -> List[datetime]:
    """
    Orders the values in the domain.

    Parameters:
        domain (set[datetime]):
            The domain of values to be ordered.

    Returns:
        list[datetime]:
            The ordered list of values in the domain.
    """
    return sorted(domain)


def is_consistent(
    assignment: List[Tuple[int, datetime]], constraints: Set[DateConstraint]
) -> bool:
    """
    Checks if the current assignment is valid given the constraints.

    Parameters:
        assignment (list[(int, datetime)]):
            The current assignment of variables and their values.
        constraints (set[DateConstraint]):
            The set of constraints that must be followed.

    Returns:
        bool:
            True if no constraints are violated otherwise, False.
    """
    for constraint in constraints:
        if constraint.L_VAL >= len(assignment):
            continue

        left_date = assignment[constraint.L_VAL][1]
        right_date = None
        if constraint.ARITY == 2:
            if isinstance(constraint.R_VAL, int):
                if len(assignment) > constraint.R_VAL:
                    right_date = assignment[constraint.R_VAL][1]
                else:
                    right_date = None
            else:
                right_date = constraint.R_VAL

        if right_date is None:
            if constraint.ARITY == 2:
                continue
        if not constraint.is_satisfied_by_values(left_date, right_date):
            return False
    return True


# CSP Filtering: Node Consistency
# ---------------------------------------------------------------------------
def node_consistency(
    domains: list[set[datetime]], constraints: set[DateConstraint]
) -> None:
    """
    Enforces node consistency for all variables' domains given in the set of domains.
    Meetings' domains' index in each of the provided constraints correspond to their index
    in the list of domains.

    [!] Note: Only applies to Unary DateConstraints, i.e., those whose arity() method
    returns 1

    Parameters:
        domains (list[set[datetime]]):
            A list of domains where each domain is a set of possible date times to assign
            to each meeting. Each domain in the given list is indexed such that its index
            corresponds to the indexes of meetings mentioned in the given constraints.
        constraints (set[DateConstraint]):
            A set of DateConstraints specifying how the meetings must be scheduled.
            See DateConstraint documentation for different types of DateConstraints
            that might be found, and useful methods for implementing this solver.
            [!] Hint: see a DateConstraint's is_satisfied_by_values

    Side Effects:
        Although no values are returned, the values in any pruned domains are changed
        directly within the provided domains parameter
    """

    for set_domain in range(len(domains)):
        to_remove = set()
        for single_domain in domains[set_domain]:
            for single_constraint in constraints:
                if single_constraint.arity() == 1:
                    if single_constraint.L_VAL == set_domain:
                        if not single_constraint.is_satisfied_by_values(single_domain):
                            to_remove.add(single_domain)
        domains[set_domain].difference_update(to_remove)


# CSP Filtering: Arc Consistency
# ---------------------------------------------------------------------------
class Arc:
    """
    Helper Arc class to be used to organize domains for pruning during the AC-3
    algorithm, organized as (TAIL -> HEAD) Arcs that correspond to a given
    CONSTRAINT.

    [!] Although you do not need to, you *may* modify this class however you see
    fit to accomplish the arc_consistency method

    Attributes:
        CONSTRAINT (DateConstraint):
            The DateConstraint represented by this arc
        TAIL (int):
            The index of the meeting variable at this arc's tail.
        HEAD (int):
            The index of the meeting variable at this arc's head.

    [!] IMPORTANT: By definition, the TAIL = CONSTRAINT.L_VAL and
        HEAD = CONSTRAINT.R_VAL
    """

    def __init__(self, constraint: DateConstraint):
        """
        Constructs a new Arc from the given DateConstraint, setting this Arc's
        TAIL to the constraint's L_VAL and its HEAD to the constraint's R_VAL

        Parameters:
            constraint (DateConstraint):
                The constraint represented by this Arc
        """
        self.CONSTRAINT: DateConstraint = constraint
        self.TAIL: int = constraint.L_VAL
        if isinstance(constraint.R_VAL, int):
            self.HEAD: int = constraint.R_VAL
        else:
            raise ValueError("[X] Cannot create Arc from Unary Constraint")

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if not isinstance(other, Arc):
            return False
        return (
            self.CONSTRAINT == other.CONSTRAINT
            and self.TAIL == other.TAIL
            and self.HEAD == other.HEAD
        )

    def __hash__(self) -> int:
        return hash((self.CONSTRAINT, self.TAIL, self.HEAD))

    def __str__(self) -> str:
        return (
            "Arc["
            + str(self.CONSTRAINT)
            + ", ("
            + str(self.TAIL)
            + " -> "
            + str(self.HEAD)
            + ")]"
        )

    def __repr__(self) -> str:
        return self.__str__()


def arc_consistency(
    domains: list[set[datetime]], constraints: set[DateConstraint]
) -> None:
    """
    Enforces arc consistency for all variables' domains given in the set of domains.
    Meetings' domains' index in each of the provided constraints correspond to their index
    in the list of domains.

    [!] Note: Only applies to Binary DateConstraints, i.e., those whose arity() method
    returns 2

    Parameters:
        domains (list[set[datetime]]):
            A list of domains where each domain is a set of possible date times to assign
            to each meeting. Each domain in the given list is indexed such that its index
            corresponds to the indexes of meetings mentioned in the given constraints.
        constraints (set[DateConstraint]):
            A set of DateConstraints specifying how the meetings must be scheduled.
            See DateConstraint documentation for different types of DateConstraints
            that might be found, and useful methods for implementing this solver.
            [!] Hint: see a DateConstraint's is_satisfied_by_values

    Side Effects:
        Although no values are returned, the values in any pruned domains are changed
        directly within the provided domains parameter
    """

    arc_set = initialize_arcs(constraints)
    while arc_set:
        curr_arc = arc_set.pop()
        if remove_inconsistent_values(domains, curr_arc):
            for arc in get_arcs_for_variable(curr_arc.TAIL, constraints):
                arc_set.add(arc)


def initialize_arcs(constraints: set[DateConstraint]) -> set[Arc]:
    """
    Creates a set of arcs from the set of constraints.

    Parameters:
        constraints (set[DateConstraint]):
            The set of constraints for the assignment to follow.

    Returns:
        set[Arc]:
           The set of arcs from the constraints..
    """
    arcs = set()
    for constraint in constraints:
        if constraint.ARITY == 2:
            arcs.add(Arc(constraint))
            arcs.add(Arc(constraint.get_reverse()))

    return arcs


def remove_inconsistent_values(domains: list[set[datetime]], curr_arc: Arc) -> bool:
    """
    This removes any values that would cause the tail to violate a constraint.

    Parameters:
        domains (list[set[datetime]]):
            A list of domains where each domain is a set of possible date times to assign
            to each meeting.
        curr_arc (Arc):
            The current arc to evaluate.

    Returns:
        bool:
            True if any value was removed from the domain of the tail variable, False otherwise.
    """
    tail_domain = domains[curr_arc.TAIL]
    head_domain = domains[curr_arc.HEAD]
    removed = False
    for tail_val in tail_domain.copy():
        consistent = False
        for head_val in head_domain:
            if curr_arc.CONSTRAINT.is_satisfied_by_values(tail_val, head_val):
                consistent = True
                break
        if not consistent:
            tail_domain.remove(tail_val)
            removed = True
    return removed


def get_arcs_for_variable(variable: int, constraints: set[DateConstraint]) -> set[Arc]:
    """
    Gets a set of arcs for the given variable from the set of constraints.

    Parameters:
        variable (int):
            The variable for which to get arcs.
        constraints (set[DateConstraint]):
            A set of DateConstraints specifying how the meetings must be scheduled.

    Returns:
        set[Arc]:
            A set of arcs associated with the given variable.
    """
    arcs = set()
    for constraint in constraints:
        if constraint.ARITY == 2 and constraint.R_VAL == variable:
            arcs.add(Arc(constraint))
    return arcs
