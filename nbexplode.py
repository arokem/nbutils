#!/usr/bin/env python
# from https://gist.github.com/2620735
"""
Explode a parametrized notebook into as many notebooks as there are
combinations of parameters.

Takes a notebook where the first cell looks something like this::

    ## Parameters
    x = [ 1, 5, 10, 20 ]
    y = 'I love python'.split()

and creates 12 notebooks, with the first cell replaced by all combinations of
members of `x` and `y`, for example, the first notebook that will get exploded
will have this as it's first cell::

    ## Parameterized by sample.ipynb
    x = 1
    y = 'I'

and the last exploded notebook will have its first cell be::

    ## Parameterized by sample.ipynb
    x = 20
    y = 'python'
"""

import os
import logging
import itertools
from collections import OrderedDict
from IPython.nbformat.current import reads, writes

logging.basicConfig(format='%(message)s')
log = logging.getLogger(os.path.basename(__file__))

loader_template = """
# What follows is a code snippet to load the __saved__ variables on
# re-execution, of this notebook.  This code only raises exception if the last
# cell in this notebook ran, and the desired variables were saved
try:
    saved_npz = '%s.npz';
    import numpy as np; _loaded = np.load(saved_npz);
    locals().update(_loaded); import datetime; import os.path;
    tstamp = os.path.getmtime(saved_npz) ;
    t = datetime.datetime.fromtimestamp(tstamp).strftime("%%Y-%%d-%%m @ %%H:%%M:%%S")
    class AlreadyRan(Exception): pass
    raise AlreadyRan("it appears this notebook already ran on %%s, halting" %%t)
except IOError:
    pass
__save__ = %s
"""



footer_template = """## autogenerated saving cell
np.savez('%s', %s)
"""

def explode(nb, quiet=False, stdout=False):
    """
    Explode a parametrized notebook

    Parameters
    ----------
    nb : IPython Notebook object
        The parameterized notebook to be exploded
    quiet : bool (default=False)
        whether to print out filenames of the exploded notebooks


    """
    first_cell = nb.worksheets[0].cells[0]
    if not first_cell.input.lower().startswith("## parameters"):
        log.warning("no parameters found in this notebook")
        return
    params = OrderedDict()
    exec(first_cell.input, globals(), params)

    saved = params.pop('__save__', [])
    saved_params =", ".join(["%s=%s"% (var,var) for var in saved])
    last_cell  = nb.worksheets[0].cells[0].copy()
    if saved:
        nb.worksheets[0].cells.append(last_cell)
    for i, p in enumerate(itertools.product(*params.values())):
        log.info("p = %s", p)
        basename = ipynb.rsplit('.ipynb')[0]
        outname = args.prefix + basename +"%04d" % i
        outfile = outname + ".ipynb"

        header = "## Parameterized by %s\n" % ipynb
        assignments = []
        # XXX: the code below won't currently work for callables, I think
        for k,v in zip(params.keys(), p):
            assignments.append('%s = %s' % (k,repr(v)))
        loader  = loader_template % (outfile, saved) if len(saved) else ''
        first_cell.input = header + "\n".join(assignments) + loader
        last_cell.input = footer_template % (outfile, saved_params)
        nb_as_json = writes(nb, 'json')
        with open(outfile, 'w') as f:
            f.write(nb_as_json)
        log.info('writing file...')
        if not quiet:
            print outfile

if __name__ == '__main__':
    from argparse import ArgumentParser, RawTextHelpFormatter

    parser = ArgumentParser(description=__doc__,
            formatter_class=RawTextHelpFormatter)
    parser.add_argument('inputs', nargs='+', metavar='input',
                        help='Paths to notebook files.')
    parser.add_argument('-i', '--inplace', '--in-place', default=False,
            action='store_true',
            help='Overwrite existing notebook when given.')

    parser.add_argument('-p', '--prefix', default='',
                        help='prefix for the resulting filenames')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='Be verbose')
    parser.add_argument('-q', '--quiet', default=False, action='store_true',
                        help='Be quiet, or I shall taunt you a second time!')
    parser.add_argument('-O', '--stdout', default=False, action='store_true',
        help='Print converted output instead of sending it to a file')
    # damn it, this next option breaks explosion being indpenedent of running
    #parser.add_argument('-c', '--clean', default=False, action='store_true',
    #    help='delete previous npz files from __save__ cell')

    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.INFO)
    if args.quiet:
        log.setLevel(logging.CRITICAL)


    for ipynb in args.inputs:
        log.info('Exploding '+ ipynb)
        with open(ipynb) as f:
            nb = reads(f.read(), 'json')

        explode(nb, quiet=args.quiet, stdout=args.stdout)
