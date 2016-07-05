#!/usr/bin/env python

import cnfformula.cnfgen as cnfgen
import cnfformula.transformations as transformations
import cnfformula.cmdline as cmdline

from .test_commandline_helper import TestCommandline, stderr_redirector

class TestCnfgen(TestCommandline):
    def test_empty(self):
        self.checkCrash([])

    def test_help(self):
        with self.assertRaises(SystemExit) as cm:
            cnfgen.command_line_utility(["cnfgen","-h"])
        self.assertEqual(cm.exception.code, 0)

    def test_find_formula_transformations(self):
        subcommands = cmdline.find_methods_in_package(transformations,
                                                      cmdline.is_cnf_transformation_subcommand)
        self.assertNotEqual(subcommands[:],[])
        
    def test_transformations_help(self):
        subcommands = cmdline.find_methods_in_package(transformations,
                                                      cmdline.is_cnf_transformation_subcommand)
        for sc in subcommands:
            with self.assertRaises(SystemExit) as cm:
                cnfgen.command_line_utility(["cnfgen", "and", "0", "0" ,"-T", sc.name, "-h"])
            self.assertEqual(cm.exception.code, 0)

    def test_nonformula_empty(self):
        self.checkCrash(["spam"])

    def test_nonformula_help(self):
        self.checkCrash(["spam", "-h"])
