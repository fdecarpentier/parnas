# -*- coding: utf-8 -*-

import unittest
from Bio import Phylo
from io import StringIO

from medoids import find_n_medoids, build_distance_functions


class TestTreeMedoids(unittest.TestCase):

    def test_one_medoid(self):
        tree = Phylo.read(StringIO("(((a:2,b:1):2,e:1):1,(c:1,d:2):1);"), 'newick')
        distance_funcs = build_distance_functions(tree)
        medoids, obj = find_n_medoids(tree, 1, distance_funcs)
        self.assertEqual(len(medoids), 1)
        self.assertEqual(medoids[0], 'e')
        self.assertEqual(obj, 18)

    def test_two_medoids(self):
        tree = Phylo.read(StringIO("((a:1,(b:2.5,c:2.5):1):3,(d:0.5,(e:2.5,f:3):1):2)"), 'newick')
        distance_funcs = build_distance_functions(tree)
        medoids, obj = find_n_medoids(tree, 2, distance_functions=distance_funcs)
        self.assertEqual(len(medoids), 2)
        self.assertEqual(obj, 17.5)
        self.assertEqual(set(medoids), {'a', 'd'})

    def test_two_medoids_w_radius1(self):
        tree = Phylo.read(StringIO("((a:1,(b:2.5,c:2.5):1):3,(d:0.5,(e:2.5,f:3):1):2)"), 'newick')
        radius = 4  # d should cover e.
        distance_funcs = build_distance_functions(tree, radius=radius)
        medoids, obj = find_n_medoids(tree, 2, distance_functions=distance_funcs)
        self.assertEqual(len(medoids), 2)
        self.assertEqual(obj, 13.5)
        self.assertEqual(set(medoids), {'a', 'd'})

    def test_two_medoids_w_radius2(self):
        tree = Phylo.read(StringIO("((a:1,(b:2.5,c:2.5):1):3,(d:0.5,(e:2.5,f:3.5):1):2)"), 'newick')
        radius = 4.5  # d should cover e; a should cover b and c.
        distance_funcs = build_distance_functions(tree, radius=radius)
        medoids, obj = find_n_medoids(tree, 2, distance_functions=distance_funcs)
        self.assertEqual(len(medoids), 2)
        self.assertEqual(obj, 5)
        self.assertEqual(set(medoids), {'a', 'd'})

    def test_one_medoid_w_prior(self):
        tree = Phylo.read(StringIO("(((a:2,b:1):2,e:1):1,(c:1,d:2):1);"), 'newick')
        prior_centers = ['b']
        distance_funcs = build_distance_functions(tree, prior_centers=prior_centers)
        medoids, obj = find_n_medoids(tree, 1, distance_funcs)
        print(medoids, obj)
        self.assertEqual(len(medoids), 1)
        self.assertTrue(medoids[0] in {'c', 'd'})
        # self.assertEqual(obj, 18)


if __name__ == '__main__':
    unittest.main()
