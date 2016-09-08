# Common Imports
from __future__ import print_function

import glob
import os
import sys
import shutil
import re
import sympy

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

from periodictable import elements

# Import Rate
from pyreaclib.rates import Rate

# Import Util function
from pyreaclib.util import list_unique

class RateCollection(object):
    """ a collection of rates that together define a network """

    def __init__(self, rate_files):
        """
        rate_files are the files that together define the network.  This
        can be any iterable or single string, and can include
        wildcards

        """

        self.pyreaclib_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.files = []
        self.rates = []

        if type(rate_files) is str:
            rate_files = [rate_files]

        # get the rates
        self.pyreaclib_rates_dir = os.path.join(self.pyreaclib_dir,
                                                'rates')
        exit_program = False
        for p in rate_files:
            # check to see if the rate file is in the working dir
            fp = glob.glob(p)
            if fp:
                self.files += fp
            else:
                # check to see if the rate file is in pyreaclib/reaclib-rates
                fp = glob.glob(os.path.join(self.pyreaclib_rates_dir, p))
                if fp:
                    self.files += fp
                else: # Notify of all missing files before exiting
                    print('ERROR: File {} not found in {} or the working directory!'.format(
                        p,self.pyreaclib_rates_dir))
                    exit_program = True 
        if exit_program:
            exit()

        for rf in self.files:
            try:
                self.rates.append(Rate(rf))
            except:
                print("Error with file: {}".format(rf))
                raise
                    
        # get the unique nuclei
        u = []
        for r in self.rates:
            t = list_unique(r.reactants + r.products)
            u = list_unique(u + t)

        self.unique_nuclei = sorted(u)

        # now make a list of each rate that touches each nucleus
        # we'll store this in a dictionary keyed on the nucleus
        self.nuclei_consumed = {}
        self.nuclei_produced = {}

        for n in self.unique_nuclei:
            self.nuclei_consumed[n] = []
            for r in self.rates:
                if n in r.reactants:
                    self.nuclei_consumed[n].append(r)

            self.nuclei_produced[n] = []
            for r in self.rates:
                if n in r.products:
                    self.nuclei_produced[n].append(r)

        # Re-order self.rates so Reaclib rates come first,
        # followed by Tabular rates. This is needed if
        # reaclib coefficients are targets of a pointer array
        # in the Fortran network.
        # It is desired to avoid wasting array size
        # storing meaningless Tabular coefficient pointers.
        self.rates = sorted(self.rates,
                            key = lambda r: r.chapter=='t')
        
        self.tabular_rates = []
        self.reaclib_rates = []
        for n,r in enumerate(self.rates):
            if r.chapter == 't':
                self.tabular_rates.append(n)
            elif type(r.chapter)==int:
                self.reaclib_rates.append(n)
            else:
                print('ERROR: Chapter type unknown for rate chapter {}'.format(
                    str(r.chapter)))
                exit()

    def print_network_overview(self):
        for n in self.unique_nuclei:
            print(n)
            print("  consumed by: ")
            for r in self.nuclei_consumed[n]:
                print("     {}".format(r.string))

            print("  produced by: ")
            for r in self.nuclei_produced[n]:
                print("     {}".format(r.string))

            print(" ")
                
    def make_network(self, outfile):
        typenet_avail = {
            'python'   : pyreaclib.networks.net_python.Network_py,
            'sundials' : pyreaclib.networks.net_fortran.sundials.Network_sundials,
            'boxlib'   : pyreaclib.networks.net_fortran.boxlib.Network_boxlib
        }
        base, ext = os.path.splitext(outfile)
        if ext == '.py' or outfile == 'python':
            self.output_file = outfile
            print(self.output_file)
            net = typenet_avail['python'](self)
            net.write_network(outfile)
        else:
            if outfile in typenet_avail:
                net = typenet_avail[outfile](self)
                net.write_network()
            else:
                print('Network type {} not available. Available networks are:'.format(outfile))
                for k in typenet_avail.keys():
                    print(k)
                exit()
                
    def plot(self):
        G = nx.DiGraph()
        G.position={}
        G.labels = {}

        plt.plot([0,0], [8,8], 'b-')

        # nodes
        for n in self.unique_nuclei:
            G.add_node(n)
            G.position[n] = (n.N, n.Z)
            G.labels[n] = r"${}$".format(n.pretty)

        # edges
        for n in self.unique_nuclei:
            for r in self.nuclei_consumed[n]:
                for p in r.products:
                    G.add_edges_from([(n, p)])


        nx.draw_networkx_nodes(G, G.position,
                               node_color="1.0", alpha=0.4,
                               node_shape="s", node_size=1000)
        nx.draw_networkx_edges(G, G.position, edge_color="0.5")
        nx.draw_networkx_labels(G, G.position, G.labels, 
                                font_size=14, font_color="r", zorder=100)

        plt.xlim(-0.5,)
        plt.xlabel(r"$N$", fontsize="large")
        plt.ylabel(r"$Z$", fontsize="large")

        ax = plt.gca()
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.xaxis.set_ticks_position('bottom')
        ax.yaxis.set_ticks_position('left')
        plt.show()

    def __repr__(self):
        string = ""
        for r in self.rates:
            string += "{}\n".format(r.string)
        return string

# Import Network Modules
import pyreaclib.networks.net_fortran
import pyreaclib.networks.net_python
