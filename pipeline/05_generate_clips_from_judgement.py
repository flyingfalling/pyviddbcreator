import os;
import sys;
import pathlib;
import argparse;
import numpy as np;
import cv2
import pandas as pd;

#REV: create output_dir

#REV: get list of files in procsourcevids_dir...make sure they exist
#for actual running (full path of them superset of unique vids in
#csv).

#REV: get extension of all vids in procsourcevidsdir (remove final extension?)

#REV: construct procfilenames from corresponding guy (multi-dict from files I guess?)


def extract_offset_params( basename ):
    #print("Extracting params from [{}]".format(basename));
    noext = basename.split('.');
    ext = noext[-1];
    stem = '.'.join(noext[:-1]);
    uscore_split = stem.split('_');
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
    return origbasename, scale, hoff, voff, ext;




incsv = sys.argv[1];
procsourcevids_dir = sys.argv[2];
output_dir = sys.argv[3];


try:
    os.makedirs(output_dir); #REV: mkdir -p
except OSError:
    print ("WARNING: Creation of out dir [{}] failed (exists!) -- files will be overwritten".format(output_dir));
else:
    print ("Successfully created out dir [{}]!".format(output_dir));
            



columns = [ "PROCVIDPATH", "FULLNAME", "PROCVIDNAME", "SCALE", "HOFF", "VOFF", "EXT" ]

srcdf = pd.DataFrame( columns=columns );

paths=[];
rootdir = procsourcevids_dir;
for root, subdirs, files in os.walk(rootdir):
    for filename in files:
        file_path = os.path.join(root, filename); #this is CSV file.
        #REV: this is video path!
        
        #print( file_path );
        #print( extract_offset_params( file_path ) );
        sourcevid, scale, hoff, voff, ext = extract_offset_params( file_path );
        sourcevidpath = '/'.join(sourcevid.split('/')[:-1]);
        sourcevidfname = sourcevid.split('/')[-1];

        fullname = os.path.join(root, filename);
        newrow = [ sourcevidpath, fullname, sourcevidfname, scale, hoff, voff, ext ];
        #print( sourcevidpath, sourcevidfname );
        srcdf.loc[ len(srcdf) ] = newrow;



inputdf = pd.read_csv( incsv );



#print(srcdf);
#print(srcdf.PROCVIDNAME);

#for row in srcdf.itertuples():
#    print(row.PROCVIDNAME);

donerows=0;
nrows=len(inputdf);
for row in inputdf.itertuples():
    donerows+=1;
    #print(row);
    #print(row.HOFF);
    #print(row.VOFF);
    #print(row.SCALE);
    
    #vidnoext = '.'.join(row.VID.split('.')[:-1]);
    #ext = row.VID.split('.')[-1];
    #print(vidnoext);
    #REV: filtering conditions MUST ENCLOSE PARENTHESES!
    #srcrow = srcdf[ (srcdf.HOFF == row.HOFF) & (srcdf.VOFF == row.VOFF) & (srcdf.SCALE == row.SCALE) ]; #& (srcdf.PROCVIDNAME == vidnoext) ]; # & (srcdf.EXT == ext) ];
    srcrow = srcdf[ (srcdf.HOFF == row.HOFF) & (srcdf.VOFF == row.VOFF) & (srcdf.SCALE == row.SCALE) & (srcdf.PROCVIDNAME == row.VID) ];
    
    if(len(srcrow) != 1):
        print("ERROR, doesn't add up!?");
        exit(1);

    rowval = srcrow.iloc[0];
    #print(rowval);

    #print("Accessing vid file [{}], frames [{}-{}]".format( rowval.PROCVIDPATH + "/" + rowval.PROCVIDNAME, row.START_FR, row.END_FR ) );
    print("({}/{})  Accessing vid file [{}], frames [{}-{}]".format( donerows, nrows, rowval.FULLNAME, row.START_FR, row.END_FR ) );
    
    cap = cv2.VideoCapture( rowval.FULLNAME );
    
    if( cap.isOpened() ):
        orig_w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));  # float
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); # float
        orig_fps = cap.get(cv2.CAP_PROP_FPS);
        orig_nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT));
    else:
        print("Could not open video file [{}]".format(vidpath));

    startfr = row.START_FR;
    endfr = row.END_FR;
    nfr = endfr-startfr;
    cap.set(cv2.CAP_PROP_POS_FRAMES, startfr);

    clipid = row.ExtractedClipID;
    
    outext=".mp4";
    
    outclipfname = "{}/clip_{:010d}{}".format(output_dir, clipid, outext);
    
    fourcc_string = "avc1";
    fourcc = cv2.VideoWriter_fourcc(*fourcc_string)
    vw = cv2.VideoWriter( outclipfname, fourcc, orig_fps, (orig_w, orig_h) ); #REV: color is assumed...
        
    
    readframes=0;
    
    ret, frame = cap.read();
    while( True == ret and readframes < nfr ):
        vw.write( frame );
        
        readframes+=1;
        ret, frame = cap.read();

    if( readframes != nfr ):
        print("There weren't enough frames in input video?!");
        exit(1);
    #REV: finished writing...
    
    
