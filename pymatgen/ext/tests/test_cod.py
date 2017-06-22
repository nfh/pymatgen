# coding: utf-8
# Copyright (c) Pymatgen Development Team.
# Distributed under the terms of the MIT License.

from __future__ import division, unicode_literals

import unittest
from monty.os.path import which

from pymatgen.ext.cod import COD


"""
Created on Jun 9, 2012
"""


__author__ = "Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyuep@gmail.com"
__date__ = "Jun 9, 2012"


class CODTest(unittest.TestCase):

    @unittest.SkipIf(not which("mysql"), "No mysql.")
    def test_get_cod_ids(self):
        ids = COD().get_cod_ids("Li2O")
        print(ids)

    def test_get_structure_by_id(self):
        s = COD().get_structure_by_id(2002926)
        self.assertEqual(s.formula, "Be8 H64 N16 F32")



if __name__ == "__main__":
    unittest.main()