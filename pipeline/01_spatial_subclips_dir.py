import argparse
import os

from multiprocessing import Pool
import functools

#REV: how to get directory of this file? Fuck.
#sys.path.append('./impls')
from impls.i_01_spatial_subclips_single import spatial_subclips_singlevid


def run_single( vid, _outdir, _outsizepx, _scales ):
    print("++++++++++ Running singlevid on [{}]".format(vid));
    spatial_subclips_singlevid( vid, _outdir, _outsizepx, _scales );


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Spatially Sub-Sample Video');

    parser.add_argument('--addinputdir', metavar='INPUT_DIR', nargs=1, required=True, action="append",
                        help='The full (preferably absolute) path to directory that will be walked recursively. Can call multiple times. *ALL VIDEO (BASE) NAMES MUST BE UNIQUE*');

    parser.add_argument('--outdir', metavar='OUTPUT_DIR', nargs=1, required=True,
                        help='The full (preferably absolute) path of the directory to which output videos will be written.');

    #WID HEI
    parser.add_argument('--outsizepx', metavar=('WID', 'HEI'), type=int, nargs=2, required=True, help='Width and Height (in pixels) of output videos to be produced');

    parser.add_argument('--cores', metavar=('N'), type=int, nargs=1, required=True, help='Num cores to run on (split per input video)');

    #SCALE MINOVERLAP
    parser.add_argument('--addscale', metavar=('SCALE', 'MINOVERLAP'), type=float, action="append", nargs=2, required=True, help='SCALE: real value in range (0, 1]. Scales of smaller of width/height of input, outputs will be sampled as proportion of that value (e.g. 0.5 is one-half of height if height is smaller than width in original dimension. Width will be determined by aspect ratio requested in --outsizepx WID HEI. MINOVERLAP: Real valued minimum overlap of output videos tiling each spatial dimension. For example, at scale 1, for a width-larger video, there will only be one height offset. However, if width is 1000 and output width is 500, 2 width offset outputs will overlap 0.0 (one from [0, 499], one from [500, 999]). 3 width offsets will overlap 0.50 (250/500), because: [0, 499], [250, 749], [500, 999]. For 0.33 overlap, also 3. Will use 1 only in case where outputdim=inputdim, otherwise start with 2 and add until threshold is reached.');
    
    
    args = vars(parser.parse_args()); #REV: sys.argv by default
    print(args);
    
    #REV: faster to just use ffmpeg? Raw from the shell script? Nasty to calculate minimum overlap etc.
    
    
    _viddirs = args['addinputdir'];
    _outdir = args['outdir'][0];
    _outsizepx = args['outsizepx'];
    _scales = args['addscale'];

    cores = args['cores'][0];

    vidpaths=[];
    for rootdir in _viddirs[0]:
        for root, subdirs, files in os.walk(rootdir):
            for filename in files:
                file_path = os.path.join(root, filename)
                vidpaths.append(file_path);

    print(vidpaths);

    a_set = set(vidpaths);
    if( len(a_set) != len(vidpaths) ):
        print("ERROR: Your list contains duplicate video basenames, exiting.");
        exit(1);

    print("Running on {} cores".format(cores));

    pool = Pool(cores);
    
    pool.map( functools.partial(run_single, _outdir=_outdir, _outsizepx=_outsizepx, _scales=_scales), vidpaths );
    #REV: can parallelize it here I guess.
    #for vid in vidpaths:
    #    print("Running singlevid on [{}]".format(vid));
    #    spatial_subclips_singlevid( vid, _outdir, _outsizepx, _scales );
        
    pool.close();
    pool.join();
    exit(0);
    
