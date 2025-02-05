
#REV: Script 02 -- splits scenes of all videos found in argument $DIR using PySceneDetect content mode. Specified threshold etc. is used
#     for all videos...which is not ideal now (in future use CSV/database file with per-video content thresholds? Slippery...will customize
#     everything haha.).

# Parallel execute python?
# REV: do parallels in here. Only thing passed is FILE DIRECTORY? Name is just filename hahaha. OK.

import argparse
import os

from multiprocessing import Pool
import functools

from impls.i_02_split_scenes_single import *

def wrapper(i, _vidfiles, _vidpaths, _outmetadir, _thresh, _min, _max ):
    outdir = os.path.join( _outmetadir, _vidfiles[i] );

    print("++++ Executing (parallel) for video file {}".format(_vidfiles[i]));
    #REV: outdir will be created in function
    split_scenes_for_video( _vidpaths[i], outdir, _thresh, _min, _max );
    
    return;

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Split Single Video Scenes with PySceneDetect');

    parser.add_argument('--inputpath', metavar='INPUT_VID', nargs=1, required=True, action='append',
                        help='Path containing input videos to be processed (will recursively process *ALL* files in directory, regardless of type, so make sure only videos are present. May specify this multiple times to add more directories.');

    parser.add_argument('--outmetadir', metavar='META_DIR', nargs=1, required=True,
                        help='The full (preferably absolute) path of the directory to which output directories will be created and written. Will be created if it does not exist.');
    
    parser.add_argument('--content_threshold', type=float, nargs=1, required=True, help='PySceneDetect content threshold (will detect scene split if difference between frames is > threshold, thus higher threshold means rarer scene splitting (more false negative splits), low threshold means more splits (more false positive splits due to normal video motion etc.).');

    parser.add_argument('--minlen_sec', type=float, nargs=1, required=False, help='Minimum length of scenes that will be saved to database (note, this is not passed to PySceneDetect min scene length).');

    parser.add_argument('--maxlen_sec', type=float, nargs=1, required=False, help='Max length of scenes that will be saved to database.');

    parser.add_argument('--ncores', type=int, nargs=1, required=True, help='Number of CPU cores to run in parallel (python multiprocessing).');

    #parser.add_argument('--oldstats', nargs=1, required=False, help='Old stats file to read in (content already calculated, scene splitting will be faster?).');
    
    args = vars(parser.parse_args());
    print(args);
    
    outmetadir=args['outmetadir'][0];
    contthresh=args['content_threshold'][0];

    inputdirs=args['inputpath'];
    
    minlen_sec = 0;
    if( None != args['minlen_sec'] ):
        minlen_sec=args['minlen_sec'][0];

    maxlen_sec = 10000000000;
    if( None != args['maxlen_sec'] ):
        maxlen_sec=args['maxlen_sec'][0];
    
    ncores=args['ncores'][0];
    
    vidfiles=[];
    vidpaths=[];
    
    for rootdir in inputdirs[0]:
        for root, subdirs, files in os.walk(rootdir):
            for filename in files:
                file_path = os.path.join(root, filename)
                vidpaths.append(file_path);
                vidfiles.append(filename);


    #Create meta output dir
    try:
        os.makedirs(outmetadir); #REV: mkdir -p
    except OSError:
        print ("WARNING: Creation of out meta dir [{}] failed (exists!) -- files will be overwritten".format(outmetadir));
    else:
        print ("Successfully created out meta dir [{}]!".format(outmetadir));

    
    mypool = Pool(ncores);
    
    mypool.map( functools.partial(wrapper, _vidfiles=vidfiles, _vidpaths=vidpaths, _outmetadir=outmetadir, _thresh=contthresh, _min=minlen_sec, _max=maxlen_sec) , range(len(vidpaths)) );
    
    #just give it "i" in length, and read out.

    mypool.close();
    mypool.join();

    exit(0);
# END MAIN
    
