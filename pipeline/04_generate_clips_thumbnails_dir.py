
import os;
import sys;
import pathlib;
import argparse;
import numpy as np;
import pandas as pd;
from multiprocessing import Pool
import functools
import cv2;


#REV: input col names... I know because I make in 03
colnames=[ "RAWVID", "VIDSOURCE", "FPS", "SCALE", "HOFF", "VOFF", "STARTSEC", "ENDSEC", "STARTFRAME", "ENDFRAME" ]

outdfcols = colnames.copy();
outdfcols.append( "UNIQUEPATH" );
outdfcols.append( "THUMBFILE" ); #e.g. {:5d}. zero-indexed
outdfcols.append( "VIDFILE" );
outdfcols.append( "NTHUMBS" );
outdfcols.append( "THUMBWIDPX" );
outdfcols.append( "THUMBHEIPX" );
outdfcols.append( "THUMBPERSEC" );

ext='.webm'
#ext='.mp4'
THUMB_FMT = "thumbnail-{:05d}.jpeg";
VID_FMT = "video" + ext;

#fourcc_string = "mp4v";
#fourcc_string = "avc1";
#fourcc_string = 'x264';
fourcc_string = 'vp09';
#fourcc_string = 'x264';
#ffmpeg -codecs | grep -P "(h264|VP8|VP9)"
#REV: Yep, need to compile to even get mp4, and mp4v is not supported by browsers -_-;
#https://www.swiftlane.com/blog/generating-mp4s-using-opencv-python-with-the-avc1-codec/

fourcc = cv2.VideoWriter_fourcc(*fourcc_string);
#fourcc =  cv2.VideoWriter_fourcc(*'VP90')

#REV: allow specification of NUMBER of thumbnails as well (instead of imgfps?).
#REV: 26 aug 2022 -- added to ensure we always grab last frame as well?
def make_clips_and_thumbs( subdf, outdir, imgfps, outwidpx, viddir ):
    #REV: myrow contains necessary info, everything else is just params.
    REPORT_SKIP=50;
    #outdf = pd.DataFrame(columns=['UNIQUEPATH']);
    outdf = pd.DataFrame(columns=outdfcols);

    #REV: User itertuples() instead???
    done=0;
    for idx, row in subdf.iterrows():
        done+=1;
        if( done % REPORT_SKIP == 0 ):
            print("Doing IDX {}/{} ({:4.1f} pct)".format(done, len(subdf), float(done)/len(subdf)*100));
        vidfile = row.RAWVID;
        vidpath = os.path.join(viddir, vidfile);
        cap = cv2.VideoCapture( vidpath );
        if( False == cap.isOpened() ):
            print("Error cap not opened file {}".format(vidpath));
            exit(1);
        #REV: extract FPS, etc. If FPS does not match error.

        #seek to target frame location
        orig_w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));  # float
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); # float
        orig_fps = cap.get(cv2.CAP_PROP_FPS);
        orig_nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT));

        clipstart_fr = row.STARTFRAME;
        clipend_fr = row.ENDFRAME;
        if( clipend_fr <= clipstart_fr ):
            print("Big error somewhere, clipend fr <= clipstart fr");
            exit(1);
            
        if( clipend_fr >= orig_nframes ):
            print("REV: Error, original video {} contains only {} frames, but I am requesting end frame of clip as {}".format(vidpath, orig_nframes, clipend_fr ));
            exit(1);
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, clipstart_fr-1)
        
        nframes = clipend_fr - clipstart_fr;
        doneframes=0;
        skipframes = int(orig_fps/imgfps+0.5); #30 / 2 = 15. 30/0.5 = 60 ok.
        imgnum=0;
        
        #UNIQUE_NAME = row.VIDSOURCE + "/" + "scale-" + row.SCALE + "_hoff-" + row.HOFF + "_voff-" + row.VOFF + "/" + "sframe-" + clipstart_fr + "_eframe-" + clipend_fr + "/";
        UNIQUE_NAME = row.VIDSOURCE + "/scale-{}_hoff-{}_voff-{}/sframe-{}_eframe-{}/".format(row.SCALE, row.HOFF, row.VOFF, clipstart_fr, clipend_fr);
        origrat_hw = float(orig_h) / orig_w;
        wid=int(outwidpx);
        hei=int(wid*origrat_hw + 0.5);
        
                
        UNIQUE_PATH= outdir + "/data/" + UNIQUE_NAME;
        
        #MKDIR
        try:
            print("Attempting to create (internal, clip-specific) directory {}".format(UNIQUE_PATH));
            os.makedirs(UNIQUE_PATH); #REV: mkdir -p
        except OSError:
            print ("WARNING: Creation of unique dir [{}] failed (exists!) -- files will be overwritten!?".format(UNIQUE_PATH));
        else:
            print ("Successfully created unique dir [{}]!".format(UNIQUE_PATH));
        
        imgfname=UNIQUE_PATH + "/" + THUMB_FMT;
        vidfname=UNIQUE_PATH + "/" + VID_FMT;
        
        vw = cv2.VideoWriter(vidfname, fourcc, orig_fps, (wid, hei));
        
        ret, frame = cap.read();
        while ((True == ret) and (doneframes < nframes)):
            # REV: DO WORK HERE
            # 0) resize
            # 1) add to video writer
            # 2) save as image if time is right.
            
            # 0) Resize
            smallframe=cv2.resize(frame, (wid,hei));
            
            # 1) VideoWriter
            vw.write( smallframe );
            
            # 2) Thumbnail output
            #REV Note: output every skipframes, AND also output the very final frame.
            if( doneframes % skipframes == 0 ):
                imgidx = int((doneframes/skipframes) + 0.5);
                if( imgidx != imgnum ):
                    print("REV: Welp, my math is all fucked up. Kill me now. {} vs {} (note: skip={}, doneframes={}, nframes={})".format(imgidx, imgnum, skipframes, doneframes, nframes));
                    exit(1);
                
                cv2.imwrite( imgfname.format(imgidx), smallframe );
                imgnum += 1;
                pass;
            elif( doneframes == (nframes-1) ): #REV: last frame (only if it is not exactly the same as a skipframe interval...)
                imgidx = int(float(nframes)/skipframes + 0.5);
                #wouldbeimgidx = int(float(doneframes)/skipframes + 0.5); #299/30
                #if( imgidx == wouldbeimgidx ):
                #    imgidx += 1; #REV: won't be a common multiple...ugh.
                #    print("REV: WARNING -- index of final frame would overlap with natural index, i.e. final frame is not evenly distant from other frames");
                #    pass;
                if( imgidx != imgnum ):
                    print("REV: (FINAL IMG FRAME) Welp, my math is all fucked up. Kill me now. {} vs {} (note: skip={}, doneframes={}, nframes={})".format(imgidx, imgnum, skipframes, doneframes, nframes));
                    exit(1);
                    
                cv2.imwrite( imgfname.format(imgidx), smallframe );
                imgnum += 1;
                pass;
            
            # FINALLY) next frame (go around again)
            ret, frame = cap.read();
            doneframes += 1;

        if( doneframes != nframes ):
            print("REV: ERROR -- number of read frames different than expected # of frames (expected: {}, got: {})".format(nframes, doneframes));
            exit(1);
            
        vw.release();
        
        outrow = row;
        outrow[ "UNIQUEPATH" ] = UNIQUE_NAME; #REV: use name otherwise it will be global.
        outrow[ "THUMBFILE" ] = THUMB_FMT;
        outrow[ "VIDFILE" ] = VID_FMT;
        outrow[ "NTHUMBS" ] = imgnum;
        outrow[ "THUMBWIDPX" ] = wid;
        outrow[ "THUMBHEIPX" ] = hei;
        outrow[ "THUMBPERSEC" ] = imgfps;
        
        #print(outrow);
        outdf.loc[len(outdf)] = outrow;

    return outdf;
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate actual clips and thumbnails from large list of ones to produce.');

    parser.add_argument('--inputcsv', metavar='INPUT_CSV', nargs=1, required=True, action='append',
                        help='Path to CSV containing desired length clips as rows with start/end frame times etc.');

    parser.add_argument('--outdir', metavar='OUT_DIR', nargs=1, required=True,
                        help='The full (preferably absolute) path to the directory in which (1) csv file and (2) video clips will be created. Video clips will be produced in $OUT_DIR/data, which will contain $OUTDIR/data/filename/clipsmall.mkv as well as video frames. $OUT_DIR/clips.csv will contain the data about individual clips (start/end time, original video, clip location, etc.)');
    
    
    parser.add_argument('--images_fps', metavar="FPS", nargs=1, required=True, type=float, help='Frames per second for saving the images (thumbnails).');
    
    #downsample size should be...pixels? I guess. Make ra
    parser.add_argument('--outwid_px', metavar="PX", nargs=1, required=True, type=int, help='Width (in pixels) of output clips and thumbnails. Will maintain aspect ratio.');
    
    parser.add_argument('--ncores', type=int, nargs=1, required=True, help='Number of CPU cores to run in parallel (python multiprocessing).');
    
    parser.add_argument('--viddir', nargs=1, required=True, action="append", help='Specifies (appends) directory that contains original (spatial subframed etc.) videos to sample etc. (only allow single for now)');

    #REV: how to 'group' clips together? Just do all clips from original VIDEO within *N* timeframes of one another? Have user select "best"
    #Keep refining?

    args = vars(parser.parse_args())

    inputcsvs = args['inputcsv'][0];
    outdir = args['outdir'][0];
    outwid_px = args['outwid_px'][0];
    images_fps=args['images_fps'][0];
    ncores=args['ncores'][0];
    viddir=args['viddir'][0][0]; #only allow single vid dir? or multiple to search through for video?
    
    try:
        print("Attempting to create directory {}".format(outdir));
        os.makedirs(outdir); #REV: mkdir -p
    except OSError:
        print ("WARNING: Creation of out meta dir [{}] failed (exists!) -- files will be overwritten!?".format(outdir));
    else:
        print ("Successfully created out meta dir [{}]!".format(outdir));

    #print(inputcsvs);
    bigdf = pd.read_csv( inputcsvs[0] );
    for csv in inputcsvs[1:]:
        exit(1);
        df = pd.read_csv( csv );
        bigdf = bigdf.append( df );

    #isdup = bigdf.duplicated();
    dupcols = ["VIDSOURCE", "SCALE", "HOFF", "VOFF", "STARTFRAME", "ENDFRAME"];
    isdup = bigdf.duplicated(dupcols, keep=False);
    print("Num Duplicates: {}".format( len(bigdf[isdup])));
    
    #print( bigdf[isdup].groupby(dupcols) );
    #exit(1);
    if( len(bigdf[isdup]) > 0 ):
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)
        for _, val in bigdf[isdup].groupby(dupcols):
            print(val);
        print("ERROR: At least one duplicate (there should not be). Exiting.");
        exit(1);
        
    #REV: add "group" information? It's kind of in there ;)
    
    #for clip, create (1) frames (2) video clip.
    
    #split creation hopefully lock on dir won't be an issue.
    df_split = np.array_split(bigdf, ncores)
    #print(df_split);
    
    pool = Pool(ncores)
    outdfs = pd.concat( pool.map( functools.partial(make_clips_and_thumbs, outdir=outdir, imgfps=images_fps, outwidpx=outwid_px, viddir=viddir), df_split) );
    
    outdups=outdfs.duplicated();
    print( outdups );
    print( "Out dups #: {}".format(len(outdfs[outdups])));
    pool.close()
    pool.join()
    
    outcsvfname = outdir + "/index.csv";
    print("Outputting CSV to {}".format(outcsvfname));
    outdfs.to_csv(outcsvfname);
    
    exit(0);
