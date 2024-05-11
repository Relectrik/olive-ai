from dataclasses import *
from datetime import *
from typing import *

class DateConstraint:
    '''
    DateConstraints represent the conditions on how meetings are scheduled in
    the Calendar Satisfaction Problems (CSPs).
    
    Attributes:
        L_VAL (int):
            The index corresponding to one of the CSP meetings
        OP (str):
            The comparison operator like "==" or ">"
        R_VAL (int OR datetime):
            Depending on whether or not this DateConstraint is unary or binary,
            represents either the other meeting index or specific date against
            which to compare the given meeting in the L_VAL
        ARITY (int):
            How many variables appear in the DateConstraint: 1 for unary, 2
            for binary
    '''
    
    # The only valid operators to compare datetimes in this class
    _VALID_OPS = ["==", "!=", ">", "<", ">=", "<="]
    
    def __init__(self, l_val: int, op: str, r_val: Union[int, datetime]):
        '''
        Constructs a new DateConstraint with the given variables/datetime and relational
        operator.
        
        Parameters:
            l_val (int):
                The index of one of the variables being constrained
            op (str):
                The logical operator constraining the variable(s) in this DateConstraint.
                Legal choices for op can be found in DateConstraint._VALID_OPS
            r_val (Union[int, datetime]):
                Either the index of another variable being constrained (making this a
                Binary Date Constraint) or a datetime constraining the l_val (making
                this a Unary Date Constraint)
        
        [Unary Date Constraints]
            Constrain a single meeting by its index where the index is always the
            DateConstraint's L_VAL and the specific datetime is always the R_VAL
            Example:
                "Meeting 0 must occur on 1/3/2023"
                DateConstraint(0, "==", datetime(2023, 1, 3))
        
        [Binary Date Constraints]
            Constrain two meetings by their indexes where both L_VAL and R_VAL are
            meeting indexes
            Example:
                "Meeting 0 must occur sometime before meeting 1"
                DateConstraint(0, "<", 1)
        '''
        if not op in DateConstraint._VALID_OPS:
            raise ValueError("[X] Date constraint " + str(self) + " has invalid OP.")
        if not isinstance(l_val, int) or l_val < 0:
            raise ValueError("[X] Date constraint L_VAL " + str(l_val) + " must be an int >= 0.")
        if isinstance(r_val, int) and r_val < 0:
            raise ValueError("[X] Date constraint R_VAL " + str(r_val) + " for binary constraints must be an int >= 0.")
        if not isinstance(r_val, int) and not isinstance(r_val, datetime):
            raise ValueError("[X] Date constraint R_VAL " + str(r_val) + " must be either a datetime (unary constraint) or int (binary constraint).")
        self.L_VAL: int = l_val
        self.OP: str = op
        self.R_VAL: Union[int, datetime] = r_val
        self.ARITY = 1 if isinstance(r_val, datetime) else 2

    def generate_dates(self, start_date: datetime, n_days: int) -> set[datetime]:
        '''
        Constructs a range of dates starting at the given start_date and then advancing
        some n_days into the future, each datetime separated by exactly 1 day.
        
        Parameters:
            start_date (datetime):
                The date at which to begin the range
            n_days (int):
                The number of days that this range spans
        
        Returns:
            set[datetime]
                The set of dates in the range provided by the parameters
        '''
        return {start_date + timedelta(days=x) for x in range(n_days)}
    
    def arity(self) -> int:
        '''
        Getter for this Constraint's arity, in this context, meaning the number of variables
        that appear in the constraint.
        
        Returns:
            int:
                The number of variables that appear in this constraint:
                    => 1 for Unary constraints like:     3 == datetime(2023, 1, 1)
                    => 2 for Binary constraints like:    3 < 1
        '''
        return self.ARITY
    
    def is_satisfied_by_assignment(self, assignment: list[datetime]) -> bool:
        '''
        Determines whether or not this DateConstraint is satisfied by the given assignment,
        which can either be a full or partial assignment of values to meeting variables,
        by index (e.g., index 1 of assignment would correspond to the datetime assigned to
        meeting 1).
        
        Parameters:
            assignment (list[datetime]):
                The list of assigned datetimes to meetings, by index, e.g.,
                [datetime(2023, 1, 1), datetime(2023, 1, 2)]
        
        Returns:
            True if EITHER:
                - The values assigned to this constraint's variables satisfy it, e.g.
                    assignment = [datetime(2023, 1, 1), datetime(2023, 1, 2)]
                    constraint = 0 < 1
                - The values of at least one variable in this constraint have not yet
                  been assigned, e.g.,
                    assignment = [datetime(2023, 1, 1), datetime(2023, 1, 2)]
                    constraint = 3 == 1
            False if:
                - The values assigned to this constraint's variables do NOT satisfy it, e.g.,
                    assignment = [datetime(2023, 1, 1), datetime(2023, 1, 2)]
                    constraint = 1 == 0
        '''
        left_date = assignment[self.L_VAL] if self.L_VAL < len(assignment) else None
        right_date = self.R_VAL if isinstance(self.R_VAL, datetime) else \
                     (assignment[self.R_VAL] if self.R_VAL < len(assignment) else None)
        if left_date is None or right_date is None:
            return True
        
        return self._dates_satisfy(left_date, right_date)
        
    def is_satisfied_by_values(self, left_date: datetime, right_date: Optional[datetime] = None) -> bool:
        '''
        Determines whether or not this DateConstraint is satisfied by the provided 
        left_date and right_date LITERALS, meaning that the input dates must not 
        be variable indexes.
        
        [!] Essentially ignores the constraint's variable indexes in its L_VAL and R_VAL,
        trusting that the method's caller has faithfully supplied values from these domains.
        
        Parameters:
            left_date (datetime):
                The datetime to insert for this constraint's L_VAL
            right_date (Optional[datetime]):
                If NOT None:
                    The datetime to insert for this constraint's R_VAL
                If None:
                    For Unary Date Constraints, will use the constraint's R_VAL date,
                    but will raise a ValueError if left None for a Binary Date Constraint
        
        Returns:
            True when the L_VAL = left_date and R_VAL = right_date, the constraint is satisfied
            False otherwise
        
        Examples:
            unary_dc  = DateConstraint(2, ">", datetime(2023, 1, 3))
            binary_dc = DateConstraint(0, "<", 1)
            
            unary_dc.is_satisfied_by_values(datetime(2023, 1, 5)) => True
            binary_dc.is_satisfied_by_values(datetime(2023, 1, 5), datetime(2023, 1, 4)) => False
        '''
        if right_date is None:
            if isinstance(self.R_VAL, datetime):
                right_date = self.R_VAL
            else:
                raise ValueError("[X] Can only leave right_date parameter unspecified for Unary Date Constraints")
        return self._dates_satisfy(left_date, right_date)
    
    def get_reverse(self) -> "DateConstraint":
        '''
        Returns a logically-equivalent, but syntactically reversed, DateConstraint
        that is equivalent to this one.
        
        [!] Useful for implementing Arc Consistency, wherein it is convenient to keep
        a constraint's L_VAL and the Arc's TAIL as the same variable (and vice versa for R_VAL, HEAD)
        
        [!] ONLY applicable to Binary Date Constraints -- will raise error for unary date constraints
        
        Returns:
            DateConstraint:
                A new DateConstraint that is logically equivalent, but syntactically reversed,
                from the current one.
        
        Example:
            binary_dc = DateConstraint(0, "<", 1)
            binary_dc.get_reverse()
                => DateConstraint(1, ">" 0)
        '''
        if not isinstance(self.R_VAL, int):
            raise ValueError("[X] The get_reverse method can only be used for BINARY constraints")
        return DateConstraint(self.R_VAL, self._get_symmetrical_op(), self.L_VAL)
    
    # "Private" Helpers Below
    # [!] You should not need to call any of these directly in your implementation
    # ---------------------------------------------------------------------------
    def _dates_satisfy(self, left_date: datetime, right_date: datetime) -> bool:
        '''
        Evaluates the given datetimes based on this constraint's operator.
        
        Parameters:
            left_date (datetime):
                The datetime to insert for this constraint's L_VAL
            right_date (Optional[datetime]):
                The datetime to insert for this constraint's R_VAL
        
        Returns:
            Whether or not the constraint is satisfied when the given dates are inserted
            for its L_VAL and R_VAL
        '''
        if self.OP == "==": return left_date == right_date
        if self.OP == "!=": return not left_date == right_date
        if self.OP == ">": return left_date > right_date
        if self.OP == "<": return left_date < right_date
        if self.OP == ">=": return left_date >= right_date
        if self.OP == "<=": return left_date <= right_date
        return False
        
    def _get_symmetrical_op(self) -> str:
        '''
        Returns:
            The symmetrical operator compared to this DateConstraint's current OP such
            that if the L_VAL and R_VAL were swapped, the symmetrical op would retain its
            same truth values.
        '''
        if self.OP == ">": return "<"
        if self.OP == "<": return ">"
        if self.OP == ">=": return "<="
        if self.OP == "<=": return ">="
        return self.OP
    
    def __str__(self) -> str:
        return str(self.L_VAL) + " " + self.OP + " " + str(self.R_VAL)
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other: Any) -> bool:
        if other is None: return False
        if not isinstance(other, DateConstraint): return False
        return self.L_VAL == other.L_VAL and self.OP == other.OP and self.R_VAL == other.R_VAL
    
    def __hash__(self) -> int:
        return hash((self.L_VAL, self.OP, self.R_VAL))
    