# coding: utf-8
# Copyright (c) Pymatgen Development Team.
# Distributed under the terms of the MIT License.

from __future__ import division, print_function, unicode_literals
from __future__ import absolute_import

"""
This module provides a class used to describe the elastic tensor,
including methods used to fit the elastic tensor from linear response
stress-strain data
"""

from pymatgen.analysis.elasticity import voigt_map, reverse_voigt_map
from pymatgen.analysis.elasticity.tensors import TensorBase
from pymatgen.analysis.elasticity.stress import Stress
from pymatgen.analysis.elasticity.strain import Strain
import numpy as np
import warnings
import itertools
from six.moves import range

__author__ = "Maarten de Jong"
__copyright__ = "Copyright 2012, The Materials Project"
__credits__ = "Joseph Montoya, Shyam Dwaraknath, Mark Asta, Anubhav Jain"
__version__ = "1.0"
__maintainer__ = "Joseph Montoya"
__email__ = "montoyjh@lbl.gov"
__status__ = "Development"
__date__ = "March 22, 2012"


class ElasticTensor(TensorBase):
    """
    This class extends TensorBase to describe the 3x3x3x3
    elastic tensor, C_{ij}, in Voigt-notation
    """

    def __new__(cls, input_array, tol=1e-3):
        """
        Create an ElasticTensor object.  The constructor throws an error if
        the shape of the input_matrix argument is not 3x3x3x3, i. e. in true
        tensor notation.  Issues a warning if the input_matrix argument does
        not satisfy standard symmetries.  Note that the constructor uses
        __new__ rather than __init__ according to the standard method of
        subclassing numpy ndarrays.

        Args:
            input_array (3x3x3x3 array-like): the 3x3x3x3 array-like
                representing the elastic tensor

            tol (float): tolerance for initial symmetry test of tensor
        """

        obj = TensorBase(input_array).view(cls)
        if not ((obj - np.transpose(obj, (1, 0, 2, 3)) < tol).all() and
                (obj - np.transpose(obj, (0, 1, 3, 2)) < tol).all() and
                (obj - np.transpose(obj, (1, 0, 3, 2)) < tol).all() and
                (obj - np.transpose(obj, (3, 2, 0, 1)) < tol).all()):

            warnings.warn("Input elasticity tensor does "
                          "not satisfy standard symmetries")

        if obj.shape != (3, 3, 3, 3):
            raise ValueError("Default elastic tensor constructor requires "
                             "input to be the true 3x3x3x3 representation. "
                             "To construct from an elastic tensor from "
                             "6x6 Voigt array, use ElasticTensor.from_voigt")
        return obj 

    @property
    def compliance_tensor(self):
        """
        returns the compliance tensor, which is the matrix inverse of the
        Voigt-notation elastic tensor
        """
        return np.linalg.inv(self.voigt)

    @property
    def k_voigt(self):
        """
        returns the K_v bulk modulus
        """
        return self.voigt[:3, :3].mean()

    @property
    def g_voigt(self):
        """
        returns the G_v shear modulus
        """
        return (2. * self.voigt[:3, :3].trace() - 
                np.triu(self.voigt[:3, :3]).sum() +
                3 * self.voigt[3:, 3:].trace()) / 15.

    @property
    def k_reuss(self):
        """
        returns the K_r bulk modulus
        """
        return 1. / self.compliance_tensor[:3, :3].sum()

    @property
    def g_reuss(self):
        """
        returns the G_r shear modulus
        """
        return 15. / (8. * self.compliance_tensor[:3, :3].trace() -
                      4. * np.triu(self.compliance_tensor[:3, :3]).sum() +
                      3. * self.compliance_tensor[3:, 3:].trace())

    @property
    def k_vrh(self):
        """
        returns the K_vrh (Voigt-Reuss-Hill) average bulk modulus
        """
        return 0.5 * (self.k_voigt + self.k_reuss)

    @property
    def g_vrh(self):
        """
        returns the G_vrh (Voigt-Reuss-Hill) average shear modulus
        """
        return 0.5 * (self.g_voigt + self.g_reuss)

    @property
    def kg_average(self):
        """
        returns a list of Voigt, Reuss, and Voigt-Reuss-Hill averages of bulk
        and shear moduli similar to legacy behavior
        """
        return [self.k_voigt, self.g_voigt, self.k_reuss, self.g_reuss,
                self.k_vrh, self.g_vrh]

    @property
    def universal_anisotropy(self):
        """
        returns the universal anisotropy value
        """
        return 5. * self.g_voigt / self.g_reuss + \
            self.k_voigt / self.k_reuss - 6.

    @property
    def homogeneous_poisson(self):
        """
        returns the homogeneous poisson ratio
        """
        return (1. - 2. / 3. * self.g_vrh / self.k_vrh) / \
               (2. + 2. / 3. * self.g_vrh / self.k_vrh)

    def energy_density(self, strain):
        """
        Calculates the elastic energy density due to a strain
        """
        # Conversion factor for GPa to eV/Angstrom^3
        GPA_EV = 0.000624151
        
        with warnings.catch_warnings(record=True):
            e_density = np.dot(np.transpose(Strain(strain).voigt),
                np.dot(self.voigt, Strain(strain).voigt))/2 * GPA_EV

        return e_density

    @classmethod
    def from_strain_stress_list(cls, strains, stresses):
        """
        Class method to fit an elastic tensor from stress/strain data.  Method
        uses Moore-Penrose pseudoinverse to invert the s = C*e equation with
        elastic tensor, stress, and strain in voigt notation

        Args:
            stresses (Nx3x3 array-like): list or array of stresses
            strains (Nx3x3 array-like): list or array of strains
        """
        # convert the stress/strain to Nx6 arrays of voigt-notation
        warnings.warn("Linear fitting of Strain/Stress lists may yield "
                      "questionable results from vasp data, use with caution.")
        stresses = np.array([Stress(stress).voigt for stress in stresses])
        with warnings.catch_warnings(record=True):
            strains = np.array([Strain(strain).voigt for strain in strains])

        voigt_fit = np.transpose(np.dot(np.linalg.pinv(strains), stresses))
        return cls.from_voigt(voigt_fit)

    @classmethod
    def from_stress_dict(cls, stress_dict, tol=0.1, vasp=True, symmetry=False):
        """
        Constructs the elastic tensor from IndependentStrain-Stress dictionary
        corresponding to legacy behavior of elasticity package.

        Args:
            stress_dict (dict): dictionary of stresses indexed by corresponding
                IndependentStrain objects.
            tol (float): tolerance for zeroing small values of the tensor
            vasp (boolean): flag for whether the stress tensor should be
                converted based on vasp units/convention for stress
            symmetry (boolean): flag for whether or not the elastic tensor
                should fit from data based on symmetry
        """
        inds = [(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
        c_ij = np.array([[np.polyfit([strain[ind1] for strain in list(stress_dict.keys())
                                      if (strain.i, strain.j) == ind1],
                                     [stress_dict[strain][ind2] for strain
                                      in list(stress_dict.keys())
                                      if (strain.i, strain.j) == ind1], 1)[0]
                          for ind1 in inds] for ind2 in inds])
        if vasp:
            c_ij *= -0.1  # Convert units/sign convention of vasp stress tensor
        c_ij[0:, 3:] = 0.5 * c_ij[0:, 3:]  # account for voigt doubling of e4,e5,e6
        c = cls.from_voigt(c_ij)
        c = c.zeroed()
        return c

    @property
    def voigt_symmetrized(self):
        """
        Reconstructs the elastic tensor by symmetrizing the voigt
        notation tensor, to allow for legacy behavior
        """

        v = self.voigt
        new_v = 0.5 * (np.transpose(v) + v)
        return ElasticTensor.from_voigt(new_v)
