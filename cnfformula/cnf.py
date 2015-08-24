#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Utilities to build CNF formulas interesting for proof complexity.

The module `cnfgen`  contains facilities to generate  cnf formulas, in
order to  be printed  in dimacs  or LaTeX  formats. Such  formulas are
ready to be  fed to sat solvers.  In particular  the module implements
both a library of CNF generators and a command line utility.

Copyright (C) 2012, 2013, 2014, 2015  Massimo Lauria <lauria@kth.se>
https://github.com/MassimoLauria/cnfgen.git
"""


from __future__ import print_function
from itertools import product,combinations


_default_header=r"""Generated with `cnfgen` (C) Massimo Lauria <lauria@kth.se>
https://github.com/MassimoLauria/cnfgen.git

"""


class CNF(object):
    """Propositional formulas in conjunctive normal form.

    A CNF  formula is a  sequence of  clauses, which are  sequences of
    literals. Each literal is either a variable or its negation.

    Use ``add_variable`` method to add a variable to the formula. Two
    variable with the same name are considered the same variable, add
    successive additions do not have any effect.

    Use ``add_clause`` to add new clauses to CNF. Clauses will be added
    multiple times in case of multiple insertion of the same clauses.

    For documentation purpose it is possible use have an additional
    comment header at the top of the formula, which will be
    *optionally* exported to LaTeX or dimacs.

    Implementation:  for efficiency reason clauses and variable can
    only be added, and not deleted. Furthermore order matters in
    the representation.

    Examples
    --------
    >>> c=CNF([ [(True,"x1"),(True,"x2"),(False,"x3")], \
              [(False,"x2"),(True,"x4")] ])
    >>> print( c.dimacs(export_header=False) )
    p cnf 4 2
    1 2 -3 0
    -2 4 0

    >>> c.add_clause( [(False,"x3"),(True,"x4"),(False,"x5")] )
    >>> print( c.dimacs(export_header=False))
    p cnf 5 3
    1 2 -3 0
    -2 4 0
    -3 4 -5 0
    """

    def __init__(self, clauses=None, header=None):
        """Propositional formulas in conjunctive normal form.

        Parameters
        ----------
        clauses : ordered list of clauses
            a clause with k literals list containing k pairs, each
            representing a literal (see `add_clause`). First element
            is the polarity and the second is the variable, which must
            be an hashable object.

            E.g. (not x3) or x4 or (not x2) is encoded as [(False,"x3"),(True,"x4"),False,"x2")]

        header: string, optional
            a preamble which documents the formula
        """

        self._header = header if header!=None else _default_header

        # Initial empty formula
        self._clauses         = []

        # Variable indexes <--> Variable names correspondence
        # first variable is indexed with 1.
        self._index2name      = [None]
        self._name2index      = dict()
        self._name2descr      = dict()

        # Internal coherence can be disrupted by some methods.  API
        # methods require it to be rechecked.
        self._coherent        = True

        # Load the initial data into the CNF
        for c in clauses or []:
            self.add_clause(c)


    # Formula contains an header property
    def _set_header(self, value):
        """Header setter"""
        self._header = value

    def _get_header(self):
        """Header getter"""
        return self._header

    header = property(_get_header, _set_header)

    #
    # Implementation of some standard methods
    #

    def __iter__(self):
        """Iterates over all clauses of the CNF
        """
        for cls in self._clauses:
            assert self._coherent
            yield self._uncompress_clause(cls)

    def __str__(self):
        """String representation of the formula
        """
        assert self._coherent
        return self._header

    def __len__(self):
        """Number of clauses in the formula
        """
        return len(self._clauses)


    #
    # Internal implementation methods, use at your own risk!
    #

    def _uncompress_clause(self, clause):
        """(INTERNAL USE) Uncompress a clause from the numeric representation.

        Arguments:
        - `clause`: clause to be uncompressed

        >>> c=CNF()
        >>> c.add_clause([(True,"x"),(False,"y")])
        >>> print(c._uncompress_clause([-1,-2]))
        [(False, 'x'), (False, 'y')]
        """
        return [ (l>0, self._index2name[abs(l)]) for l in clause ]

    def _compress_clause(self, clause):
        """Convert a clause to its numeric representation.

        For reason of efficiency, clauses are memorized as tuples of
        integers. Each integer correspond to a variable, with sign +1
        or -1 depending whether it represents a positive or negative
        literal. The correspondence between the numbers and the
        variables names depends on the formula itself

        Parameters
        ----------
        clause: list of pairs
            a clause, in the form of a list of literals, which are
            pairs (bool,string).

        Returns
        -------
        a tuple of int

        Examples
        --------
        >>> c=CNF()
        >>> c.add_clause([(True,"x"),(False,"y")])
        >>> print(c._compress_clause([(False, 'x'), (False, 'y')]))
        (-1, -2)

        """
        return tuple((1 if p else -1) * self._name2index[n] for p, n in clause)


    def _add_compressed_clauses(self, clauses):
        """(INTERNAL USE) Add to the CNF a list of compressed clauses.

        This method uses the internal compressed clause representation
        to add a large batch of data  into the CNF.  It does not check
        for internal  coherence conditions,  and it  does not  need to
        convert between  internal and external  clause representation,
        so it  is very fast.   When assertions  are tested, a  call to
        this method will  disable the standard API, since  the CNF can
        be in an inconsistent state.

        Whenever the high level API is used with an inconsisten state
        the code will fail some assertion.

        In particular it does not check if the indexes correspond to a
        variable in the formula.

        To test consistency and re-enable the API, please call method
        `CNF._check_coherence`.

        Arguments:
        - `clauses`: a sequence of compressed clauses.

        >>> c=CNF()

        We add the variables in advance, so that the internal status
        stays coherent.

        >>> c.add_variable("x")
        >>> c.add_variable("y")
        >>> c.add_variable("z")

        When we add some compressed clauses, we need to test the
        internal status of the object. If the test is positive, then
        the high level API is available again.

        >>> c._add_compressed_clauses([[-1,2,3],[-2,1],[1,-3]])
        >>> c._check_coherence()
        True
        >>> print(c.dimacs(export_header=False))
        p cnf 3 3
        -1 2 3 0
        -2 1 0
        1 -3 0

        If we call the internal API several times, we need to test the
        object only once.

        >>> c._add_compressed_clauses([[-2,-3]])
        >>> c._add_compressed_clauses([[-1, 2]])
        >>> c._check_coherence()
        True
        >>> print(c.dimacs(export_header=False))
        p cnf 3 5
        -1 2 3 0
        -2 1 0
        1 -3 0
        -2 -3 0
        -1 2 0
        """
        self._coherent = False
        self._clauses.extend(tuple(c) for c in clauses)


    def _check_coherence(self, force=False):
        """Check if the formula is internally consistent.

        Certain fast manipulation methods are not safe if used
        incorrectly, so the CNF object may be corrupted. This method
        tests if that was not the case.

        Arguments:
        - `force`: force check even if the formula claims coherence

        >>> c=CNF()
        >>> c.add_variable("x")
        >>> c.add_variable("y")

        We add clauses mentioning three variables, and the formula is
        not coherent.

        >>> c._add_compressed_clauses([(-1,2),(1,-2),(1,3)])
        >>> c._check_coherence()
        False

        We cannot use the API now

        >>> c.clauses()
        Traceback (most recent call last):
        AssertionError
        """
        if not force and self._coherent:
            return True

        varindex=self._name2index
        varnames=self._index2name
        
        # number of variables and clauses
        N=len(varindex.keys())
        
        # Consistency in the variable dictionary
        if N != len(varnames)-1:
            return False

        for i in range(1,N+1):
            if varindex[varnames[i]]!=i:
                return False


        # Count clauses and check literal representation
        for clause in self._clauses:
            for literal in clause:
                if not 0 < abs(literal) <= N:
                    return False

        # formula passed all tests
        self._coherent = True
        return True

    #
    # High level API: build the CNF
    #

    def add_clause(self,clause,strict=False):
        """Add a clause to the CNF.

        The clause must be well formatted. Otherwise it raises
        `TypeError` if the clause is not well formatted.

        E.g. (not x3) or x4 or (not x2) is encoded as
             [(False,u"x3"),(True,u"x4"),(False,u"x2")]

        All variable mentioned in the clause will be added to the list
        of variables  of the CNF,  in the  order of appearance  in the
        clauses.

        Arguments:
        - `clause`: a clause with k literals is a list with k pairs.
                    First coords are the polarities, second coords are
                    utf8 encoded strings with variable names.

        - `strict`: if true the clause must not contain new variables.
                    By default this is false, and new variables will
                    be included in the formula. If that is true and a clause
                    contains an unknow variables, `ValueError` is raised.
        """
        assert self._coherent

        # A clause must be an immutable object
        try:
            hash(tuple(clause))
        except TypeError:
            raise TypeError("%s is not a well formatted clause" %clause)

        # Add all missing variables
        try:
            for _, var in clause:
                if var in self._name2index:
                    continue
                if strict:
                    raise ValueError("The clause contains an illegal variable %s" % var)
                else:
                    self.add_variable(var)
        except TypeError:
            raise TypeError("%s is not a well formatted clause" %clause)

        # Add the compressed clause
        self._clauses.append( self._compress_clause(clause) )


    def add_variable(self,var,description=None):
        """Add a variable to the formula (if not already resent).

        The variable must be `hashable`. I.e. it must be usable as key
        in a dictionary.  It raises `TypeError` if the variable cannot
        be hashed.

        Parameters
        ----------
        var: hashable
             the variable name to be added/updated. It can be any
             hashable object (i.e. a dictionary key).
        description: str, optional
             an explanation/description/comment about the variable.
        """
        assert self._coherent
        try:
            if not var in self._name2index:
                # name correpsond to the last variable so far
                self._index2name.append(var)
                self._name2index[var] = len(self._index2name)-1
        except TypeError:
            raise TypeError("%s is not a legal variable name" %var)

        # update description
        if description is not None:
            self._name2descr[var] = description

    #
    # High level API: read the CNF
    #

    def variables(self):
        """Returns (a copy of) the list of variable names.
        """
        assert self._coherent
        vars_iterator = iter(self._index2name)
        vars_iterator.next()
        return vars_iterator
    
    def clauses(self):
        """Return the list of clauses
        """
        assert self._coherent
        return self.__iter__()


    def dimacs(self, export_header=True):
        """Produce the dimacs encoding of the formula

        The formula is rendered in the DIMACS format for CNF formulas,
        which is a particularly popular input format for SAT solvers [1]_.

        Parameters
        ----------
        export_header : bool
            determines whether the formula header should be inserted as
            a comment in the DIMACS output.

        Returns
        -------
        string
            the string contains the LaTeX code


        Examples
        --------
        >>> c=CNF([[(False,"x_1"),(True,"x_2"),(False,"x_3")],\
                   [(False,"x_2"),(False,"x_4")], \
                   [(True,"x_2"),(True,"x_3"),(False,"x_4")]])
        >>> print(c.dimacs())
        c Generated with `cnfgen` (C) Massimo Lauria <lauria@kth.se>
        c https://github.com/MassimoLauria/cnfgen.git
        c
        p cnf 4 3
        -1 2 -3 0
        -2 -4 0
        2 3 -4 0

        >>> c=CNF()
        >>> print(c.dimacs(export_header=False))
        p cnf 0 0
        <BLANKLINE>

        References
        ----------
        .. [1] http://www.satlib.org/Benchmarks/SAT/satformat.ps

        """
        from cStringIO import StringIO
        output = StringIO()
        self._dimacs_dump_clauses(output, export_header)
        return output.getvalue()

    def _dimacs_dump_clauses(self, output=None, export_header=True):
        """Dump the dimacs encoding of the formula to the file-like output

        This is for internal use only. It produces the dimacs output
        of the clauses, and write then on the output buffer, which is
        tipically a StringIO.
        """
        assert self._coherent

        # Count the number of variables and clauses
        n = len(self._index2name)-1
        m = len(self)

        # A nice header
        if export_header:
            for line in self.header.split("\n")[:-1]:
                output.write(("c "+line).rstrip()+"\n")

        # Formula specification
        output.write("p cnf {0} {1}".format(n, m))

        if len(self._clauses) == 0:
            output.write("\n")   # this newline makes `lingeling` solver happy

        # Clauses
        for cls in self._clauses:
            output.write("\n" + " ".join([str(l) for l in cls + (0,)]))

    def latex(self, export_header=True, full_document=False, extra_text=None):
        """Output a LaTeX version of the CNF formula

        The CNF formula is translated into the LaTeX markup language
        [1]_, using the names of the variable literally. The formula
        is rendered in the ``align`` environment, with one clause per
        row. Negated literals are rendered using the
        ``\\neg`` command.

        The output string is ready to be included in a document, but
        it does not include neither a preamble nor is nested inside
        ``\\begin{document}`` ... ``\\end{document}``.

        Parameters
        ----------
        export_header : bool, optional
            determines whether the formula header should be inserted as
            a LaTeX comment in the output. By default is True. 

        full_document : bool, optional
            rather than just output the formula, output a document 
            that contains it. False by default.

        extra_text : str, optional
            Additional text attached to the abstract.

        Returns
        -------
        string
            the string contains the LaTeX code

        Examples
        --------
        >>> c=CNF([[(False,"x_1"),(True,"x_2"),(False,"x_3")],\
                   [(False,"x_2"),(False,"x_4")], \
                   [(True,"x_2"),(True,"x_3"),(False,"x_4")]])
        >>> print(c.latex())
        % Generated with `cnfgen` (C) Massimo Lauria <lauria@kth.se>
        % https://github.com/MassimoLauria/cnfgen.git
        %
        \\begin{align}
        &       \\left( {\\overline{x}_1} \\lor            {x_2} \\lor {\\overline{x}_3} \\right) \\\\
        & \\land \\left( {\\overline{x}_2} \\lor {\\overline{x}_4} \\right) \\\\
        & \\land \\left(            {x_2} \\lor            {x_3} \\lor {\\overline{x}_4} \\right)
        \\end{align}
        >>> c=CNF()
        >>> print(c.latex(export_header=False))
        \\begin{align}
           \\top
        \\end{align}

        References
        ----------
        .. [1] http://www.latex-project.org/
        """
        assert self._coherent

        clauses_per_page = 40

        latex_preamble=r"""%
\documentclass[10pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath}
\usepackage{listings}
"""
        
        from cStringIO import StringIO
        output = StringIO()
        
        # formula header as a LaTeX comment
        if export_header:
            for s in self.header.split("\n")[:-1]:
                output.write( ("% "+s).rstrip()+"\n" )

        # document opening
        if full_document:
            output.write(latex_preamble)
            output.write("\\begin{document}\n")
            output.write("\\title{{{}}}\n".format(self.header.split('\n')[0]))
            output.write("\\author{CNFgen formula generator}\n")
            output.write("\\maketitle\n")
            output.write("\\noindent\\textbf{Formula header:}\n")
            output.write("\\begin{lstlisting}[breaklines]\n")
            output.write(self.header)
            output.write("\\end{lstlisting}\n")
            output.write("\\bigskip\n")

        if extra_text is not None and full_document:
            output.write(extra_text)
                
        def map_literals(l):
            """Map literals to LaTeX string"""
            assert l!=0
            if l>0 :
                return  "           {"+str(self._index2name[l])+"}"
            else:
                name = self._index2name[-l]
                split_point=name.find("_")
                return "{\\overline{"+name[:split_point]+"}"+name[split_point:]+"}"

        def write_clause(cls, first,full_document):
            """Write the clause in LaTeX."""
            output.write("\n&" if first  else " \\\\\n&")
            output.write("       " if full_document or first else " \\land ")

            # build the latex clause
            if len(cls) == 0:
                output.write("\\square")
            elif full_document:
                output.write(" \\lor ".join(map_literals(l) for l in cls))
            else:
                output.write("\\left( " + \
                             " \\lor ".join(map_literals(l) for l in cls) + \
                             " \\right)")

        # Output the clauses
        clauses_number = len(self._clauses)
        if full_document:
            output.write("\\noindent\\textbf{{CNF with {} variables and and {} clauses:}}\n".\
                         format(len(self._name2index),clauses_number))

        output.write("\\begin{align}")
        
        if clauses_number==0:
            output.write("\n   \\top")
        else:
            for i,clause in enumerate(self._clauses):
                if i% clauses_per_page ==0 and i!=0 and full_document:
                    output.write("\n\\end{align}\\pagebreak")
                    output.write("\n\\begin{align}")
                    write_clause(clause, True,full_document)
                else:
                    write_clause(clause, i==0,full_document)

        output.write("\n\\end{align}")

        # document closing
        if full_document:
            output.write("\n\\end{document}")
  
        return output.getvalue()


    def is_satisfiable(self, cmd=None, sameas=None):
        """Determines whether a CNF is satisfiable or not.

        The formula is passed to a SAT solver, according to the
        optional command line ``cmd``. If no command line is
        specified, the known solvers are tried in succession until one
        is found.

        It is possible to use any drop-in replacement for these
        solvers, but in this case more information is needed on how to
        communicate with the solver. In particular ``minisat`` does not
        respect the standard DIMACS I/O conventions, and that holds
        also for ``glucose`` which is a drop-in replacement of
        ``minisat``.

        For the supported solver we can pick the right interface, but
        for other solvers it is impossible to guess. Nevertheless it
        is possible to indicate which interface to use, or more
        specifically which known solver interface to mimic.

        >>> F.is_satisfiable(F,cmd='minisat-style-solver',sameas='minisat')  # doctest: +SKIP
        >>> F.is_satisfiable(F,cmd='dimacs-style-solver',sameas='lingeling') # doctest: +SKIP

        Parameters
        ----------
        cmd : string,optional
            the actual command line used to invoke the SAT solver

        sameas : string, optional
            use the interface of one of the supported solvers. Useful
            when the solver used in the command line is not supported.

        Examples
        --------
        >>> F = CNF()
        >>> F.is_satisfiable()                                              # doctest: +SKIP
        >>> F.is_satisfiable(cmd='minisat -no-pre')                         # doctest: +SKIP
        >>> F.is_satisfiable(cmd='glucose -pre')                            # doctest: +SKIP
        >>> F.is_satisfiable(cmd='lingeling --plain')                       # doctest: +SKIP
        >>> F.is_satisfiable(cmd='sat4j')                                   # doctest: +SKIP
        >>> F.is_satisfiable(cmd='my-hacked-minisat -pre',sameas='minisat') # doctest: +SKIP
        >>> F.is_satisfiable(cmd='patched-lingeling',sameas='lingeling')    # doctest: +SKIP

        Returns
        -------
        (boolean,assignment or None)
            A pair (answer,witness) where answer is either True when
            F is satisfiable, or False otherwise. If F is satisfiable
            the witness is a satisfiable assignment in form of
            a dictionary, otherwise it is None.

        Raises
        ------
        RuntimeError
           if it is not possible to correctly invoke the solver needed.

        ValueError
           if `sameas` is set and is not the name of a supported solver.

        TypeError
           if F is not a CNF object.

        See Also
        --------
        cnfformula.utils.solver.is_satisfiable
        cnfformula.utils.solver.supported_satsolvers

        """
        from .utils import solver
        return solver.is_satisfiable(self, cmd=cmd, sameas=sameas)

###
### Various utility function for CNFs
###
def parity_constraint(variables, constant):
    """Output the CNF encoding of a parity constraint

    E.g. X1 + X2 + X3 = 1 (mod 2) is encoded as

    ( X1 v  X2 v  X3)
    (~X1 v ~X2 v  X3)
    (~X1 v  X2 v ~X3)
    ( X1 v ~X2 v ~X3)

    Parameters
    ----------
    variables : array-like
        variables involved in the constraint
    constant : {0,1}
        the constant of the linear equation

    Returns
    -------
        a list of clauses

    Examples
    --------
    >>> parity_constraint(['a','b'],1)
    [[(True, 'a'), (True, 'b')], [(False, 'a'), (False, 'b')]]
    >>> parity_constraint(['a','b'],0)
    [[(True, 'a'), (False, 'b')], [(False, 'a'), (True, 'b')]]
    >>> parity_constraint(['a'],0)
    [[(False, 'a')]]
    """
    domains = tuple([((True, var), (False, var)) for var in variables])
    clauses = []
    for c in product(*domains):
        # Save only the clauses with the right polarity
        parity = sum(1-l[0] for l in c) % 2
        if parity != constant:
            clauses.append(list(c))
    return clauses


def _inequality_constraint_builder(variables, k, greater=False):
    """Builder for inequality constraint

    This is a generic builder used to build all the inequality
    constraints. By default it build a "stricly less that", and if
    ``greater`` is True it builds a "strictly greater than".
    """
    clauses = []
    polarity = greater
    if greater:
        k = len(variables) - k

    if k > len(variables):
        return []
    elif k < 0:
        return [[]]

    for tpl in combinations(variables, k):
        clauses.append([(polarity, v) for v in tpl])
    return clauses


def less_than_constraint(variables, upperbound):
    """Clauses encoding a \"strictly less than\" constraint

    E.g. X1 + X2 + X3 + X4 < 3

    (~X1 v ~X2 v ~X3)
    (~X1 v ~X2 v ~X4)
    (~X1 v ~X3 v ~X4)
    (~X2 v ~X3 v ~X4)

    Parameters
    ----------
    variables : list of variables
       variables in the constraint
    upperbound: int
       upper bound of the constraint

    Returns
    -------
        a list of clauses

    Examples
    --------
    >>> less_than_constraint(['a','b','c'],2)
    [[(False, 'a'), (False, 'b')], [(False, 'a'), (False, 'c')], [(False, 'b'), (False, 'c')]]
    >>> less_than_constraint(['a'],1)
    [[(False, 'a')]]
    >>> less_than_constraint(['a','b','c'],-1)
    [[]]
    >>> less_than_constraint(['a','b','c'],10)
    []
    """
    return _inequality_constraint_builder(variables, upperbound, greater=False)

def less_or_equal_constraint(variables, upperbound):
    """Clauses encoding a \"less than or equal to\" constraint

    E.g. X1 + X2 + X3 + X4 <= 2

    (~X1 v ~X2 v ~X3)
    (~X1 v ~X2 v ~X4)
    (~X1 v ~X3 v ~X4)
    (~X2 v ~X3 v ~X4)

    Parameters
    ----------
    variables : list of variables
       variables in the constraint
    upperbound: int
       upper bound of the constraint

    Returns
    -------
        a list of clauses

    Examples
    --------
    >>> less_than_constraint(['a','b','c'],3) == less_or_equal_constraint(['a','b','c'],2)
    True
    >>> less_or_equal_constraint(['a','b','c'],1)
    [[(False, 'a'), (False, 'b')], [(False, 'a'), (False, 'c')], [(False, 'b'), (False, 'c')]]
    >>> less_or_equal_constraint(['a','b'],0)
    [[(False, 'a')], [(False, 'b')]]
    >>> less_or_equal_constraint(['a','b','c'],-1)
    [[]]
    >>> less_or_equal_constraint(['a','b','c'],10)
    []
    """
    return _inequality_constraint_builder(variables, upperbound+1, greater=False)

def greater_than_constraint(variables, lowerbound):
    """Clauses encoding a \"strictly greater than\" constraint

    E.g. X1 + X2 + X3 + X4 > 2

    (X1 v X2 v X3)
    (X1 v X2 v X4)
    (X1 v X3 v X4)
    (X2 v X3 v X4)

    Parameters
    ----------
    variables : list of variables
       variables in the constraint
    lowerbound: int
       lower bound of the constraint

    Returns
    -------
        a list of clauses

    Examples
    --------
    >>> greater_than_constraint(['a','b','c'],2)
    [[(True, 'a')], [(True, 'b')], [(True, 'c')]]
    >>> greater_than_constraint(['a'],0)
    [[(True, 'a')]]
    >>> greater_than_constraint(['a','b','c'],-1)
    []
    >>> greater_than_constraint(['a','b','c'],3)
    [[]]
    """
    return _inequality_constraint_builder(variables, lowerbound, greater=True)

def greater_or_equal_constraint(variables, lowerbound):
    """Clauses encoding a \"greater than or equal to\" constraint

    E.g. X1 + X2 + X3 + X4 > 1

    (X1 v X2 v X3)
    (X1 v X2 v X4)
    (X1 v X3 v X4)
    (X2 v X3 v X4)

    Parameters
    ----------
    variables : list of variables
       variables in the constraint
    lowerbound: int
       lower bound of the constraint

    Returns
    -------
        a list of clauses

    Examples
    --------
    >>> greater_than_constraint(['a','b','c'],1) == greater_or_equal_constraint(['a','b','c'],2)
    True
    >>> greater_or_equal_constraint(['a','b','c'],3)
    [[(True, 'a')], [(True, 'b')], [(True, 'c')]]
    >>> greater_or_equal_constraint(['a'],0)
    []
    >>> greater_or_equal_constraint(['a','b','c'],4)
    [[]]
    """
    return _inequality_constraint_builder(variables, lowerbound - 1, greater=True)

def equal_to_constraint(variables, value):
    """Clauses encoding a \"equal to\" constraint

    E.g. X1 + X2 + X3 + X4 = 1

    (X1 v X2 v X3 v X4)
    (~X1 v ~X2)
    (~X1 v ~X3)
    (~X1 v ~X4)
    (~X2 v ~X3)
    (~X2 v ~X4)
    (~X3 v ~X4)

    Parameters
    ----------
    variables : list of variables
       variables in the constraint
    value: int
       target values

    Returns
    -------
        a list of clauses
    """
    return less_or_equal_constraint(variables, value) + \
           greater_or_equal_constraint(variables, value)


def loose_majority_constraint(variables):
    """Clauses encoding a \"at least half\" constraint

    Parameters
    ----------
    variables : list of variables
       variables in the constraint

    Returns
    -------
        a list of clauses
    """
    threshold = (len(variables)+1)/2
    return greater_or_equal_constraint(variables, threshold)

def loose_minority_constraint(variables):
    """Clauses encoding a \"at most half\" constraint

    Parameters
    ----------
    variables : list of variables
       variables in the constraint

    Returns
    -------
        a list of clauses
    """
    threshold = len(variables)/2
    return less_or_equal_constraint(variables, threshold)
