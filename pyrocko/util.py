import time, logging, os, sys, re, calendar
from scipy import signal

from os.path import join as pjoin

import config

logger = logging.getLogger('pyrocko.util')

def setup_logging(programname, levelname,):
    levels = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}

    logging.basicConfig(
        level=levels[levelname],
        format = programname+':%(name)-20s - %(levelname)-8s - %(message)s' )

class Stopwatch:
    def __init__(self):
        self.start = time.time()
    
    def __call__(self):
        return time.time() - self.start
        
        
def progressbar_module():
    try:
        import progressbar
    except:
        logger.warn('progressbar module not available.')
        progressbar = None
    
    return progressbar


def progress_beg(label):
    if config.show_progress:
        sys.stderr.write(label)
        sys.stderr.flush()

def progress_end(label=''):
    if config.show_progress:
        sys.stderr.write(' done. %s\n' % label)
        sys.stderr.flush()
        


def decimate(x, q, n=None, ftype='iir', axis=-1):
    """downsample the signal x by an integer factor q, using an order n filter
    
    By default, an order 8 Chebyshev type I filter is used or a 30 point FIR 
    filter with hamming window if ftype is 'fir'.

    (port to python of the GNU Octave function decimate.)

    Inputs:
        x -- the signal to be downsampled (N-dimensional array)
        q -- the downsampling factor
        n -- order of the filter (1 less than the length of the filter for a
             'fir' filter)
        ftype -- type of the filter; can be 'iir' or 'fir'
        axis -- the axis along which the filter should be applied
    
    Outputs:
        y -- the downsampled signal

    """

    if type(q) != type(1):
        raise Error, "q should be an integer"

    if n is None:
        if ftype == 'fir':
            n = 30
        else:
            n = 8
    if ftype == 'fir':
        b = signal.firwin(n+1, 1./q, window='hamming')
        y = signal.lfilter(b, 1., x, axis=axis)
    else:
        (b, a) = signal.cheby1(n, 0.05, 0.8/q)
        y = signal.lfilter(b, a, x, axis=axis)

    return y.swapaxes(0,axis)[n/2::q].swapaxes(0,axis)

class UnavailableDecimation(Exception):
    pass
    
class GlobalVars:
    reuse_store = dict()
    decitab_nmax = 0
    decitab = {}

def mk_decitab(nmax=100):
    tab = GlobalVars.decitab
    for i in range(1,10):
        for j in range(1,i+1):
            for k in range(1,j+1):
                for l in range(1,k+1):
                    for m in range(1,l+1):
                        p = i*j*k*l*m
                        if p > nmax: break
                        if p not in tab:
                            tab[p] = (i,j,k,l,m)
                    if i*j*k*l > nmax: break
                if i*j*k > nmax: break
            if i*j > nmax: break
        if i > nmax: break
    
def decitab(n):
    if n > GlobalVars.decitab_nmax:
        mk_decitab(n*2)
    if n not in GlobalVars.decitab: raise UnavailableDecimation('ratio = %g' % ratio)
    return GlobalVars.decitab[n]

def ctimegm(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M:%S"))

def gmctime(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))
    
def gmctime_v(t):
    return time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime(t))

def gmctime_fn(t):
    return time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime(t))

def plural_s(n):
    if n == 1:
        return ''
    else:
        return 's' 

def ensuredirs(dst):
    d,x = os.path.split(dst)
    dirs = []
    while d and not os.path.exists(d):
        dirs.append(d)
        d,x = os.path.split(d)
        
    dirs.reverse()
    
    for d in dirs:
        if not os.path.exists(d):
            os.mkdir(d)

def ensuredir(dst):
    ensuredirs(dst)
    if not os.path.exists(dst):
        os.mkdir(dst)
    
def reuse(x):
    grs = GlobalVars.reuse_store
    if not x in grs:
        grs[x] = x
    return grs[x]
    
    
class Anon:
    def __init__(self,dict):
        for k in dict:
            self.__dict__[k] = dict[k]


def select_files( paths, selector=None,  regex=None ):

    progress_beg('selecting files...')
    if logger.isEnabledFor(logging.DEBUG): sys.stderr.write('\n')

    good = []
    if regex: rselector = re.compile(regex)

    def addfile(path):
        if regex:
            logger.debug("looking at filename: '%s'" % path) 
            m = rselector.search(path)
            if m:
                infos = Anon(m.groupdict())
                logger.debug( "   regex '%s' matches." % regex)
                for k,v in m.groupdict().iteritems():
                    logger.debug( "      attribute '%s' has value '%s'" % (k,v) )
                if selector is None or selector(infos):
                    good.append(os.path.abspath(path))
                
            else:
                logger.debug("   regex '%s' does not match." % regex)
        else:
            good.append(os.path.abspath(path))
        
        
    for path in paths:
        if os.path.isdir(path):
            for (dirpath, dirnames, filenames) in os.walk(path):
                for filename in filenames:
                    addfile(pjoin(dirpath,filename))
        else:
            addfile(path)
        
    progress_end('%i file%s selected.' % (len( good), plural_s(len(good))))
    
    return good

