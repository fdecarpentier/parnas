#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import colorsys
import math
from datetime import datetime
from typing import List

from Bio import SeqRecord
from dendropy import Tree

from parnaslib import parnas_logger, parser, parse_and_validate
from parnaslib.sequences import SequenceSimilarityMatrix
from parnaslib.medoids import find_n_medoids, annotate_with_closest_centers, build_distance_functions, binarize_tree,\
    get_costs


# os.environ["NUMBA_DUMP_ANNOTATION"] = "1"


def color_by_clusters(tree: Tree, centers: List[str], prior_centers=None, radius=None):
    # Annotate the tree nodes with the closest centers.
    annotate_with_closest_centers(tree, centers, prior_centers=prior_centers, radius=radius)

    # Choose n different colors. If prior_centers list is not empty, add an additional reserved color.
    n = len(centers) if not prior_centers else len(centers) + 1
    hsv_colors = [(i / n, 0.7, 0.7) for i in range(n)]
    rgb_colors = [colorsys.hsv_to_rgb(*hsv) for hsv in hsv_colors]
    rgb_colors = [[round(255 * color[i]) for i in range(len(color))] for color in rgb_colors]
    hex_colors = ['#%02x%02x%02x' % (color[0], color[1], color[2]) for color in rgb_colors]
    if prior_centers:
        prior_color = hex_colors[0]  # Reserve the first color for prior centers.
        hex_colors = hex_colors[1:]

    # Color the edges.
    for edge in tree.preorder_edge_iter():
        if edge.head_node:
            edge.head_node.annotations.drop(name='!color')  # remove any previous color scheme.
        # If the two ends of the edge are covered by the same center -- color it.
        if edge.head_node and edge.tail_node and edge.head_node.annotations.get_value('center') is not None and\
                edge.head_node.annotations.get_value('center') == edge.tail_node.annotations.get_value('center'):
            if edge.head_node.annotations.get_value('center') < 0:  # negative if it is covered by a prior center.
                edge.head_node.annotations.add_new('!color', prior_color)  # use the reserved color.
            else:
                center_ind = edge.head_node.annotations.get_value('center')
                color = hex_colors[center_ind]
                edge.head_node.annotations.add_new('!color', color)

    # Drop previous color annotations and color 'regular' taxa black (to avoid color mixing in FigTree).
    black = '#000000'
    special_taxa = centers
    if prior_centers:
        special_taxa = special_taxa + prior_centers
    special_taxa = set(special_taxa)
    for taxon in tree.taxon_namespace:
        taxon.annotations.drop(name='!color')  # Remove any previous colors if any.
        if not taxon.label in special_taxa:
            taxon.annotations.add_new('!color', black)

    # Color the centers.
    for center_ind, center in enumerate(centers):
        taxon = tree.taxon_namespace.get_taxon(center)
        color = hex_colors[center_ind]
        taxon.annotations.add_new('!color', color)

    # Color prior centers if applicable.
    if prior_centers:
        for prior_center in prior_centers:
            taxon = tree.taxon_namespace.get_taxon(prior_center)
            taxon.annotations.add_new('!color', prior_color)


def assess_clade_similarity(annotated_tree: Tree, centers: List[str], records: List[SeqRecord.SeqRecord],
                            sim_matrix: SequenceSimilarityMatrix):
    for i, center in enumerate(centers):
        print('Clade of %s:' % center)
        max_within_dist = 0
        min_outside_dist = math.inf
        for leaf1 in annotated_tree.leaf_nodes():
            if leaf1.taxon.label != center:
                continue
            for leaf2 in annotated_tree.leaf_nodes():
                leaf1_ind = [i for i, rec in enumerate(records) if rec.id == leaf1.taxon.label][0]
                leaf2_ind = [i for i, rec in enumerate(records) if rec.id == leaf2.taxon.label][0]
                dist = 1 - sim_matrix.matrix[leaf1_ind][leaf2_ind]
                if leaf1.annotations.get_value('center') == i and leaf2.annotations.get_value('center') == i:
                    if dist > max_within_dist:
                        max_within_dist = dist
                if leaf1.annotations.get_value('center') == i and leaf2.taxon.label in centers and leaf1 != leaf2:
                    if dist < min_outside_dist:
                        min_outside_dist = dist
        print('\tmax within clade: %.3f%%' % (max_within_dist * 100))
        print('\tclosest other representative: %.3f%%' % (min_outside_dist * 100))


if __name__ == '__main__':
    args, query_tree, n, radius, prior_centers, excluded_taxa, fully_excluded = parse_and_validate()

    # Binarize the query tree:
    binarize_tree(query_tree, edge_length=0)

    dist_functions = build_distance_functions(query_tree, prior_centers=prior_centers, fully_excluded=fully_excluded,
                                              radius=radius)
    cost_map = get_costs(query_tree, excluded_taxa, fully_excluded)
    parnas_logger.info("Inferring best representatives...")
    if not args.cover:
        representatives, value = find_n_medoids(query_tree, n, dist_functions, cost_map, max_dist=radius)
    else:
        opt_n = -1
        for n in range(1, len(query_tree.leaf_nodes()) + 1):
            representatives, value = find_n_medoids(query_tree, n, dist_functions, cost_map, max_dist=radius)
            if value == 0:
                opt_n = n
                break

    if len(representatives) == 0:
        parnas_logger.info('The diversity on the tree is already fully covered by the prior centers - no new representatives needed.')
    else:
        parnas_logger.info('Chosen representatives:')
        for rep in representatives:
            print('%s' % rep)

    if args.out_path:
        color_by_clusters(query_tree, representatives, prior_centers=prior_centers, radius=radius)
        parnas_logger.debug('Finished coloring', datetime.now().strftime("%H:%M:%S"))
        try:
            query_tree.write(path=args.out_path, schema='nexus')
            parnas_logger.info('Colored tree was saved to "%s".' % args.out_path)
        except Exception:
            parser.error('Cant write to the specified path "%s".' % args.out_path)

        # if args.nt_alignment:
        #     # Parsing assuming its swIAV HA sequences.
        #     alignment_path = args.nt_alignment
        #     records = list(SeqIO.parse(alignment_path, 'fasta'))
        #     sim_matrix = SequenceSimilarityMatrix(None, None, records, records, aligned=True, ignore_tails=True, nt_alphabet=True)
        #     assess_clade_similarity(query_tree, representatives, records, sim_matrix)
