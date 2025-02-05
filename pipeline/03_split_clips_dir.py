
#03: load all "scenes.csv" files from a directory
#    combine into single CSV file (pandas dataframe).
#    for every clip (over min length etc.), walk through and do at
#     WINDOW_STEP, to extract clips of length TARG_LENGTH.
#     for now, only handle single length...10 seconds etc. 600 frames.

#    Just get all files named "scenes.csv" or some shit.


#REV: define shared content as:

#1) time shifted (up to X seconds overlap?)
#2) spatial subframe shifted (i.e. different part of larger movie but with primarily shared section too).
#   -- REV: faster, just use overlapping time and space from original video. Overlapping time will be what, same subclips? Yea...
#      Though, PySceneDetect may have messed things up and split wrong, in which case there may be truly similar videos from ANOTHER
#      clip adjacent to it (but there will be no windowing, since I use only one threshold). Or I could multi-threshold, and combine
#      all the sub-clips together as similar ones. Have user select "good" ones? But what is good about human-selected? No, the goal is to
#      just select one per "group"
#3) other overlap (i.e. similar contents, even if different spatial subframe and different time, broadly same content, spatial frequencies,
#   color histograms, etc.

#4) Might as well run through "text detection" and exclude those too? Problem is it may include JAPANESE text too?


#REV: oof, I don't want to re-extract all the things just because I sub-sampled the openCV thing first.
#REV: oh well, go back and create it. And make sure at beginning I make a database with filename locations, etc. (although that makes
#     it harder?). Well, assume it is using my naming method hahahaha.


import os;
import sys;
import pathlib;
import argparse;
import numpy as np;

import pandas as pd;

from multiprocessing import Pool
import functools

smalldelta=0.1;

colnames=[ "RAWVID", "VIDSOURCE", "FPS", "SCALE", "HOFF", "VOFF", "STARTSEC", "ENDSEC", "STARTFRAME", "ENDFRAME" ]

def extract_offset_params( basename ):

    #print("Extracting params from [{}]".format(basename));
    noext = basename.split('.');
    ext = noext[-1];
    stem = '.'.join(noext[:-1]);
    uscore_split = stem.split('_');
    origbasename = ''; #uscore_split[0];
    hoff=-1;
    voff=-1;
    scale=-1;
    finalbasename=[];
    for mypair in uscore_split:
        #hypthen split
        #print("handling pair: [{}]".format(mypair));
        hs = mypair.split('-');
        #if(len(hs) != 2 ):
        #    print("Hyphen split size is not 2?!");
        #    exit(1);
        
        pname = hs[0];
                
        if( pname == 'hoff' or pname == 'voff' or pname == 'scale' ):
            if( len(hs) != 2 ):
                print("Wtf not 2 in hyphen seperated? NOTE: I make all sorts of assumptions that the video name does not include _scale_ or _hoff_ or _voff_");
                exit(1);
            val = float(''.join( hs[1:] )); #REV: when will python error for float?
            if( val == -0 ):
                val = 0;
            if( val < 0 ):
                print("Error val (for {}) < 0!: =={}".format(pname, val));
                exit(1);
        
        if( pname == 'hoff' ):
            hoff = val;
        elif( pname == 'voff' ):
            voff = val;
        elif( pname == 'scale' ):
            scale = val;
        else:
            finalbasename.append(mypair);
            #print("Unrecognized param  {}".format(hs));
    
    #print("Orig file: [{}],  scale {},   hoff {},  voff {}".format(origbasename, scale, hoff, voff ) );
    
    origbasename = '_'.join(finalbasename);
    #print("Original basename: {}".format(origbasename));
    return origbasename, scale, hoff, voff;

def add_targlen_clips_to_full_df( df, targlen_sec, jumplen_sec ):
    #aspath = pathlib.Path(file_path);
    #parent=str(aspath.parent.name); #REV: name and stem.
    
    #df = pd.read_csv( file_path );
    
    #print("My val [{}]".format(df.LEN_FRAMES));
    #add each row of df to fulldf, appending "parent" in new column "VID" for each row
    #df['VID'] = parent;
    #oh it is already included.
    
    #REV: included original clip number? nah...
    
    retdf = pd.DataFrame( columns=colnames );
    
    #REV: re-couch everything in terms of frames ;)
    #print(df);
    for idx, cliprow in df.iterrows():
        #print("Value: [{}]".format(cliprow));
        lensec = cliprow.LEN_SECS;
        lenfr = cliprow.LEN_FRAMES;
        startstartsec = cliprow.START_SEC;
        startstartfr = cliprow.START_FRAME;
        startendsec = cliprow.END_SEC - targlen_sec;
        
        myfps=cliprow.FPS;
        targlen_fr = int(targlen_sec * myfps + smalldelta);
        startendfr = cliprow.END_FRAME - targlen_fr;

        origbasename, scale, hoff, voff = extract_offset_params( cliprow.VID );

        if( lenfr < targlen_fr ):
            print("SKIPPING scene b/c Length frames {} < desired length frames {} (note: lensec = {}).".format(lenfr, targlen_fr, lensec));
            continue;
        
        
        #print(type(lensec),   type(targlen_sec));
        
        #legalstartend = (lensec - targlen_sec);
        legalstartend = (lenfr - targlen_fr);
        
        jumplen_fr = int(jumplen_sec * myfps);
        
        #if length is already (by miracle) directly equal to, just do it? Nah, fuck it just always get the "middle", i.e. offset start/end
        #nstarts = int( legalstartend / jumplen_sec ); #e.g. 11 - 10 = 1. / 1 = 1.
        nstarts = int( legalstartend / jumplen_fr ); #e.g. 11 - 10 = 1. / 1 = 1.
        if(nstarts < 1):
            nstarts = 1;
        
        #print("Clip length {}, targ length {}, laststart {}, nstarts {}".format(lensec, targlen_sec, legalstartend, nstarts));
        #print("Clip length {}, targ length {}, laststart {}, nstarts {}".format(lenfr, targlen_fr, legalstartend, nstarts));
        
        #extent = nstarts * jumplen_sec;
        extent = (nstarts-1) * jumplen_fr;
        diff = legalstartend - extent;
        diff_twotailed = diff/2;
        
        #print( "Extent is {} sec (clip len {}, start {}  end {}  nstarts {}  targlen {}".format(extent, lenfr, startstartfr, startendfr, nstarts, targlen_fr) );
        
        #startstartsec = startstartsec + diff_twotailed;
        #startendsec = startstartsec + extent;

        
        startstartfr = startstartfr + int(diff_twotailed);
        if( startstartfr < 0 ):
            print( "diff two {}, start start neg {}".format(diff_twotailed, startstartfr));
            exit(1);
        startendfr = startstartfr + extent;
        
        
        #print( "Extent is {} sec (clip len {}, start {}  end {}  nstarts {}  targlen {}".format(extent, lensec, startstartsec, startendsec, nstarts, targlen_sec) );
        
        #REV: 
        #starts_sec = np.linspace( startstartsec, startendsec, nstarts+1 );
        starts_fr = np.linspace( startstartfr, startendfr, nstarts );

                        
        
        #print(starts_fr);
        #if( len(starts_sec) and starts_sec[1]-starts_sec[0] != jumplen_sec ):
        if( len(starts_fr) > 1 and len(starts_fr) and starts_fr[1]-starts_fr[0] != jumplen_fr ):
            #print("Error (or floating point error)? Expected {}, got {}".format( jumplen_sec, starts_sec[1]-starts_sec[0] ));
            print("Error (or floating point error)? Expected {}, got {}".format( jumplen_fr, starts_fr[1]-starts_fr[0] ));
            exit(1);
        
        #START_FRAME, END_FRAME, START_SEC, END_SEC, FPS, VID
        #REV:
        #For each start/end, add too fulldf, which is created beforehand.
        
        #for s in starts_sec:
        for s in starts_fr:
            #endsec = s+targlen_sec;
            #endfr = s+targlen_fr;
            sframe = int(s); #int(s * myfps + smalldelta); #REV: will this be accurate...?
            eframe = int(sframe + targlen_fr); #int(endsec * myfps + smalldelta);
            nframes = int(eframe-sframe);

            if( lenfr == targlen_fr ):
                #print("Clip length is *EXACTLY* desired frames".format(lenfr, targlen_fr));
                if( nstarts != 1 or sframe != startstartfr ):
                    print("ERROR YOU FAIL!");
                    exit(1);

            
            #targframes = int(targlen_sec * myfps + smalldelta);
            if( nframes != targlen_fr ):
                print("REV: error, nframes for  start frame {} end frame {}: {} is not targ frames {}".format( sframe, eframe, nframes, targframes ));
                exit(1);
            #REV: keep track of original "clip" as well so I can
            #REV: exclude similars?
            #REV: what to do with similar content? Have them select
            #*ONE* best one, *OR* select that none of them are good.

            #REV: can iteratively do this.
            #REV: auto-compare content (within-frame? across frames?).
            #REV: just do content.
            startsec = sframe / myfps;
            endsec = eframe / myfps;
            newrow = [ cliprow.VID, origbasename, myfps, scale, hoff, voff, startsec, endsec, sframe, eframe ];
            #print(newrow);
            #fulldf.loc[ len(fulldf) ] = newrow; #super inefficient?
            retdf.loc[ len(retdf) ] = newrow; #super inefficient?
    #fulldf = fulldf.append( df ); #whatever, who cares about efficiency ahhahaa.
    return retdf;
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Split Single Video Scenes with PySceneDetect');

    parser.add_argument('--inputpath', metavar='INPUT', nargs=1, required=True, action='append',
                        help='Path containing sub-directories (which in turn contain scenes.csv) to be processed (will recursively process *ALL* subdirectories in nested fashion. Name of original video is (must be unique) the immediate parent directory\'s basename of each scenes.csv file. Recommend only running on directories produced by script 02.');

    parser.add_argument('--outcsv', metavar='OUT_CSV', nargs=1, required=True,
                        help='The full (preferably absolute) path and filename of csv file to create to (will overwrite)');

    parser.add_argument('--outlen_sec', metavar="LEN_SEC", nargs=1, required=True, type=float, help='Length (in seconds) of output clips.');

    parser.add_argument('--jumptime_sec', metavar="JUMP_SEC", nargs=1, required=True, type=float, help='Length (in seconds) to jump when doing sliding (jumping) window.');

    #parser.add_argument('--images_fps', metavar="FPS", nargs=1, required=True, type=float, help='Frames per second for saving the images (thumbnails).');
    
    #downsample size should be...pixels? I guess. Make ra
    #parser.add_argument('--outwid_px', metavar="PX", nargs=1, required=True, type=int, help='Width (in pixels) of output clips and thumbnails. Will maintain aspect ratio.');

    parser.add_argument('--ncores', type=int, nargs=1, required=True, help='Number of CPU cores to run in parallel (python multiprocessing).');

    #parser.add_argument('--viddir', nargs=1, required=True, action="append", help='Specifies (appends) directory that will contain original videos to sample etc.');

    args = vars(parser.parse_args());
    print(args);
    
    inputdirs=args['inputpath'];
    
    outcsv=args['outcsv'][0];
    outlen_sec=args['outlen_sec'][0];
    jumptime_sec=args['jumptime_sec'][0];
    
    #outwid_px = args['outwid_px'][0];
    #images_fps=args['images_fps'][0];
    ncores=args['ncores'][0];
    
    #full_df = pd.DataFrame( columns=colnames );
    
    paths=[];
    for rootdir in inputdirs[0]:
        for root, subdirs, files in os.walk(rootdir):
            for filename in files:
                file_path = os.path.join(root, filename); #this is CSV file.
                if( filename == 'scenes.csv' ):
                    paths.append( file_path );

    inputdf = pd.read_csv( paths[0] );
    for path in paths[1:]:
        tmpdf = pd.read_csv( path );
        inputdf = inputdf.append(tmpdf);

    df_split = np.array_split(inputdf, ncores);
    pool = Pool(ncores)
    outdfs = pd.concat( pool.map( functools.partial(add_targlen_clips_to_full_df, targlen_sec=outlen_sec, jumplen_sec=jumptime_sec), df_split) );
    
    
    #add_targlen_clips_to_full_df( file_path, outlen_sec, jumptime_sec );
    pool.close();
    pool.join();
        
    print("Outputting to CSV file (creating/overwriting): [{}]".format(outcsv));
    outdfs.to_csv( outcsv );
    exit(0);
