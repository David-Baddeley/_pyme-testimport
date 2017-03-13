#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
"""
Created on Sat May  9 12:23:57 2015

@author: david
"""
import matplotlib
matplotlib.use('Cairo')

from PYME.recipes import runRecipe
from PYME.recipes import modules
import os
import glob
from argparse import ArgumentParser
import traceback

import multiprocessing

NUM_PROCS = multiprocessing.cpu_count()

def runRec(args):
    #print args
    try:
        runRecipe.runRecipe(*args)
    except:
        traceback.print_exc()
    
def bake(recipe, inputGlobs, output_dir, num_procs = NUM_PROCS):
    """Run a given recipe over using multiple proceses.
    
    Arguments:
    ----------
      recipe:       The recipe to run
      inputGlobs:   A dictionary of where the keys are the input names, and each
                    entry is a list of filenames which provide the data for that
                    input.
      output_dir:   The directory to save the output in
      num_procs:    The number of worker processes to launch (defaults to the number of CPUs)
      
    """
    
    #check that we've supplied the right number of images for each named input/channel
    inputLengths = [len(v) for v in inputGlobs.values()]
    if not (min(inputLengths) == max(inputLengths)):
        raise RuntimeError('The number of entries in each input category must be equal')
        
    taskParams = []
    outputNames = recipe.outputs
    
    for i in range(inputLengths[0]):
        in_d = {k:v[i] for k, v in inputGlobs.items()}

        file_stub = os.path.splitext(os.path.basename(in_d.values()[0]))[0]
        
        fns = os.path.join(output_dir, file_stub)
        out_d = {k:('%s_%s'% (fns,k)) for k in  outputNames}

        cntxt = {'output_dir' : output_dir, 'file_stub': file_stub}

        taskParams.append((recipe, in_d, out_d, cntxt))

    if num_procs == 1:
        map(runRec, taskParams)
    else:
        pool = multiprocessing.Pool(num_procs)
    
        pool.map(runRec, taskParams)


def main():
    #start by finding out what recipe we're using - different recipes can have different options    
    ap = ArgumentParser()#usage = 'usage: %(prog)s [options] recipe.yaml')
    ap.add_argument('recipe')
    ap.add_argument('output_dir')
    ap.add_argument('-n', '--num-processes', default=NUM_PROCS)
    args, remainder = ap.parse_known_args()
    
    #load the recipe
    with open(args.recipe) as f:
        s = f.read()
        
    recipe = modules.ModuleCollection.fromYAML(s)

    output_dir = args.output_dir
    num_procs = args.num_processes
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    #create a new parser to parse input and output filenames
    op = ArgumentParser()
    for ip in recipe.inputs:
        op.add_argument('--%s' % ip)
        
        
    args = op.parse_args(remainder)
    
    inputGlobs = {k: glob.glob(getattr(args, k)) for k in recipe.inputs}
    
    bake(recipe, inputGlobs, output_dir, num_procs)
        
        
if __name__ == '__main__':
    main()
