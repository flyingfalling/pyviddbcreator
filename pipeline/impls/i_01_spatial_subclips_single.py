
###################################
#REV: use opencv (cv2) to extract spatial sub-clips based on arguments


#REV: right now, if desire e.g. 800x600, and source video is unable to satisfy that aspect, it will skip that scale.
#   e.g. if source video is 800x599, it will fail at scale 1.0




import argparse

import cv2
import numpy as np
import os

#import functools
#import multiprocessing


class paramclass:
    def __init__(self):
        self.finscales=[];
        self.finhoffs=[];
        self.finvoffs=[];
        self.outdir='';
        self.vidbase='';
        self.vidpath='';
        self.fourcc='';
        self.orig_fps=0;
        self.outsizepx_hw=[];
        self.finvstartpxs=[];
        self.finvendpxs=[];
        self.finhstartpxs=[];
        self.finhendpxs=[];
        

#fourcc_string = "FFV1";
#fourcc_string = "vp09";
fourcc_string = "mp4v";
#fourcc_string = "H264";
#fourcc_string = "avc1";

#FILEEXT=".mkv";
#FILEEXT=".mp4";
FILEEXT=".m4v";

#REV: so many args to include ;( Make dict or something?
def extract_and_add_subvids( i, frame, params, vws ):
    if( vws[i] == None ):
        #print("Scale: {} (len {})".format( params.finscales[i], len(params.finscales)));
        #print("hoff: {} (len {})".format( params.finhoffs[i], len(params.finhoffs)));
        #print("voff: {} (len {})".format( params.finvoffs[i], len(params.finvoffs)));
        tag = '_scale-' + str(params.finscales[i]) + '_hoff-' + "{:3.2f}".format(params.finhoffs[i]) + '_voff-' + "{:3.2f}".format(params.finvoffs[i]) + FILEEXT;
        outf = params.outdir + '/' + params.vidbase + tag;
        vws[i] = cv2.VideoWriter( outf, params.fourcc, params.orig_fps, (params.outsizepx_hw[1], params.outsizepx_hw[0]) );
        print("Writing to file [{}]".format(outf));
        params.outfnames[i] = outf;

    if( params.finvstartpxs[i] < 0 or params.finvendpxs[i] < 0 or params.finhstartpxs[i] < 0 or params.finhendpxs[i] < 0 ):
        print("Error, something is <0!!!!? ");
        exit(1);
        
    subframe = frame[ params.finvstartpxs[i]:params.finvendpxs[i], params.finhstartpxs[i]:params.finhendpxs[i], : ];
    resized = cv2.resize( subframe, (params.outsizepx_hw[1], params.outsizepx_hw[0]) );
    vws[i].write( resized );
    return;
    




def spatial_subclips_singlevid( vidpath, outdir, outsizepx, scales ):
    
    vidbase = vidpath.split('/')[-1];

    print("I think basename of video is [{}]".format(vidbase));
    if( '' == vidbase ):
        print("Vid base empty");
        exit(1);


    print("Will output to outdir [{}]".format(outdir));


    try:
        os.makedirs(outdir); #REV: mkdir -p
    except OSError:
        print ("Creation of outdir [{}] failed!".format(outdir));
    else:
        print ("Successfully created outdir [{}]!".format(outdir));

    outsizepx_hw = [ int(outsizepx[1]), int(outsizepx[0]) ];

    

    #REV: test.
    orig_w = 1000;
    orig_h = 700;

    cap = cv2.VideoCapture( vidpath );

    if( cap.isOpened() ):
        orig_w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));  # float
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); # float
        orig_fps = cap.get(cv2.CAP_PROP_FPS);
        orig_nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT));
    else:
        print("Could not open video file [{}]".format(vidpath));

    orig_shape_hw = [orig_h, orig_w]; #REV: note we maintain numpy matrix ordering of rows, columns.

    #REV: what to do when output video aspect is opposite of input? I.e. wid>hei vs hei>wid?
    #REV: scale will be relative to the lesser INPUT dimension
    if( orig_shape_hw[0] < orig_shape_hw[1] ):
        mindimidx = 0;
    else:
        mindimidx = 1;

    minsizepx = orig_shape_hw[int(mindimidx)];

    finscales=[];
    finhoffs=[];
    finvoffs=[];
    finhstartpxs=[];
    finhendpxs=[];
    finvstartpxs=[];
    finvendpxs=[];

    for scale in scales:
        print("Doing for scale {} (min overlap {})".format(scale[0], scale[1]));
        print("Input image is WID/HEI: {} x {}".format(  orig_shape_hw[1], orig_shape_hw[0] ) );
        print("Target output WID/HEI: {} x {}    (w/h aspect={})".format( outsizepx_hw[1], outsizepx_hw[0], outsizepx_hw[1]/outsizepx_hw[0]));
        sizeratio = scale[0];
        minoverlap = scale[1];
        if( sizeratio > 1.0 or minoverlap >= 1.0 ):
            print("ERROR, size ratio > 1 or minoverlap >= 1");
            exit(1);

        #REV: size in pixels of "smaller" dimension of output (will scale other dimension of output based on output aspect ratio)
        targpx = int((minsizepx * sizeratio) + 0.5); #Assume int conversion will floor

        targsizepx_hw = [0,0]

        targsizepx_hw[mindimidx] = targpx;
        otheridx = (mindimidx+1) % 2;
        targsizepx_hw[otheridx] = int( targpx * (outsizepx[mindimidx]/outsizepx[otheridx]) + 0.5 );

        print("Will produce output image of WID/HEI:  {} x {}   (w/h aspect={})".format( targsizepx_hw[1], targsizepx_hw[0], targsizepx_hw[1]/targsizepx_hw[0] ) );

        
        dims=2;
        noffsets = [0, 0];
        offsets_px = [[], []];
        for d in range(dims):
            if( targsizepx_hw[d] > orig_shape_hw[d] ):
                print("WARNING: VID {}  scale {}    target size is *GREATER* than size for (rows,cols) dimension [{}] (target {}, video source {} px)".format(vidpath, scale, d, targsizepx_hw[d], orig_shape_hw[d]));
                noffsets[d]=0;
                offsets_px[d] = [];
                continue;
            elif( targsizepx_hw[d] == orig_shape_hw[d] ):
                noffsets[d] = 1;
                offsets_px[d] = [0];
            else:
                noffsets[d] = 2;
                #REV: calculate partition/tiling of noffsets guys of of extent targsizepx_hw[d] in orig_shape_hw[d]
                shiftregion_px = orig_shape_hw[d] - targsizepx_hw[d];
                shifts_rel = np.array(range(noffsets[d]))/max(range(noffsets[d])); #e.g. 0, 1
                shifts_px = np.array(shiftregion_px * shifts_rel + 0.5).astype(int);
                shift_px_per = shifts_px[1] - shifts_px[0]; # note: minus shifts_px[0], but that is always 0.
                overlap_px = targsizepx_hw[d] - shift_px_per;
                overlap_ratio = overlap_px / targsizepx_hw[d];
                
                offsets_px[d] = shifts_px
                
                while( overlap_ratio < minoverlap ):
                    noffsets[d] += 1;
                    shiftregion_px = orig_shape_hw[d] - targsizepx_hw[d];
                    shifts_rel = np.array(range(noffsets[d]))/max(range(noffsets[d])); #e.g. 0, 1
                    shifts_px = np.array(shiftregion_px * shifts_rel + 0.5).astype(int);
                    shift_px_per = shifts_px[1] - shifts_px[0]; # note: minus shifts_px[0], but that is always 0.
                    overlap_px = targsizepx_hw[d] - shift_px_per;
                    overlap_ratio = overlap_px / targsizepx_hw[d];
                    
                    offsets_px[d] = shifts_px;

            print("Dimension {}: Will use {} spatial offsets. Offsets: {}".format( d, noffsets[d], offsets_px[d] ) );

        for voff0 in offsets_px[0]:
            for hoff1 in offsets_px[1]:
                vstart = int(voff0 + 0.5);
                vend = int(voff0 +  targsizepx_hw[0] + 0.5);
                hstart = int(hoff1 + 0.5);
                hend = int(hoff1 +  targsizepx_hw[1] + 0.5);
                
                print("Will spatially subsample from Width: [{}, {}]   Height: [{}, {}]     WID/HEI={} x {}".format( hstart, hend, vstart, vend, hend-hstart, vend-vstart ) );
                
                if( vstart < 0 or vend < 0 or hstart < 0 or hend < 0 ):
                    print("ERROR: oops <0?");
                    exit(1);
                

                #REV: name output file. Sample and add to that CV::VIDEO_WRITER
                #REV: oh, it's not relative? Have to re-calculate from pixels. Offset is pixel offset * width of original.
                hoffrat = hoff1/orig_shape_hw[1];
                voffrat = voff0/orig_shape_hw[0];

                finscales.append( sizeratio );
                finhoffs.append( hoffrat );
                finvoffs.append( voffrat );

                finhstartpxs.append(hstart);
                finhendpxs.append(hend);
                finvstartpxs.append(vstart);
                finvendpxs.append(vend);

    
    fourcc = cv2.VideoWriter_fourcc(*fourcc_string)
    
    outfnames=[ None for i in range(len(finscales)) ];

    p = paramclass();
    p.finscales=finscales;
    p.finhoffs=finhoffs;
    p.finvoffs=finvoffs;
    p.outdir=outdir;
    p.vidbase=vidbase;
    p.vidpath=vidpath;
    p.fourcc=fourcc;
    p.orig_fps=orig_fps;
    p.outsizepx_hw=outsizepx_hw;
    p.finvstartpxs=finvstartpxs;
    p.finvendpxs=finvendpxs;
    p.finhstartpxs=finhstartpxs;
    p.finhendpxs=finhendpxs;
    p.outfnames=outfnames;
    
    myvws = [ None for i in range(len(finscales)) ];

    
    nframes=0;
    REPORT_SKIP=300;
    if( cap.isOpened() ):
        ret, myframe = cap.read( );
        
        while( True == ret ):
            for i in range(len(finscales)) :
                extract_and_add_subvids( i, frame=myframe, params=p, vws=myvws );
            #results = pool.map( functools.partial( extract_and_add_subvids, frame=myframe, params=p ), range(len(finscales)) );
            
            if( nframes % REPORT_SKIP == 0 ):
                print("Frame [{} / {} ({:4.1f} %)] (Video {})".format(nframes, orig_nframes, 100.0*(nframes/float(orig_nframes)), vidbase));
            
            ret, myframe = cap.read();
            nframes+=1;
            # END while True == ret

        print("FINISHED. Processed total of {} frames into {} subvideos".format( nframes, len(finscales)) );
        #for fname in outfnames:
        #    print("{}".format(fname));

        # END if( cap is opened );
    else:
        print("Couldn't open video capture [{}].");

    
    for vw in myvws:
        vw.release();
#REV: I would very much like to parallelize this





if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Spatially Sub-Sample Single Video');

    parser.add_argument('--input', metavar='INPUT_VID', nargs=1, required=True,
                        help='The full (preferably absolute) path including the filename of video file to process.');
    
    parser.add_argument('--outdir', metavar='OUTPUT_DIR', nargs=1, required=True,
                        help='The full (preferably absolute) path of the directory to which output videos will be written.');

    #WID HEI
    parser.add_argument('--outsizepx', metavar=('WID', 'HEI'), type=int, nargs=2, required=True, help='Width and Height (in pixels) of output videos to be produced');

    #SCALE MINOVERLAP
    parser.add_argument('--addscale', metavar=('SCALE', 'MINOVERLAP'), type=float, action="append", nargs=2, required=True, help='SCALE: real value in range (0, 1]. Scales of smaller of width/height of input, outputs will be sampled as proportion of that value (e.g. 0.5 is one-half of height if height is smaller than width in original dimension. Width will be determined by aspect ratio requested in --outsizepx WID HEI. MINOVERLAP: Real valued minimum overlap of output videos tiling each spatial dimension. For example, at scale 1, for a width-larger video, there will only be one height offset. However, if width is 1000 and output width is 500, 2 width offset outputs will overlap 0.0 (one from [0, 499], one from [500, 999]). 3 width offsets will overlap 0.50 (250/500), because: [0, 499], [250, 749], [500, 999]. For 0.33 overlap, also 3. Will use 1 only in case where outputdim=inputdim, otherwise start with 2 and add until threshold is reached.');

    args = vars(parser.parse_args()); #REV: sys.argv by default
    print(args);
    
    #REV: faster to just use ffmpeg? Raw from the shell script? Nasty to calculate minimum overlap etc.
    
    
    _vidpath = args['input'][0];
    _outdir = args['outdir'][0];
    _outsizepx = args['outsizepx'];
    _scales = args['addscale'];
    
    spatial_subclips_singlevid( _vidpath, _outdir, _outsizepx, _scales );



#REV: automatically generate a subsampling of "original" and "examples" of various TMO outputs. Have user select (specify) which are most
#"appropriate" looking (i.e. scaled to be inside desired luminance). Hopefully there will be no crossovers...? I.e. overall brighter videos
#getting dimmer than dimmer videos getting brighter than the luminance corrected brighter ones. May happen due to subjective color percpetion
#of brightness haha. There has got to be a way to automatically correct brightness absolutely to fixed scale...probably using TMO?
#REV: surely it can recognize that mean pixels are really dark, and brighten it... ;/ Without "pretending" it is shown on a really dim/bright
#REV: projector like I have to do haha. Simple brightening software in photoshop etc. is nasty. Does it really matter?
#REV: meh, my way is "best" :) Hopefully not much change from adaptation within.

#1) Open input video (fail if doesn't exist). OPENCV
#2) Get wid/hei of input video (pix).
#3) hei_wid_ratio_input = hei/wid (e.g. 0.75). 750/1000
#4) wid_hei_ratio_input = wid/hei (e.g. 1.33333) 1000/750
#5) smalldim=min( blah.shape[:2] ) (assume 3 dims, 3rd for color with 3 size)
#5) For SCALE, figure out number of offsets in horiz and vert direction. For full cross product, generate
#   FILENAME_SCALE_HOFFSET_VOFFSET.mp4, and subsample it.

#ffmpeg -i in.mp4 -filter:v "crop=out_w:out_h:x:y" out.mp4
#    out_w is the width of the output rectangle
#    out_h is the height of the output rectangle
#    x and y specify the top left corner of the output rectangle
#ffplay -i input -vf "crop=in_w:in_h-40"
#REV: will work?
#ffmpeg -i input -vf "crop=w:h:x:y" output
#ffplay -i input -vf "crop=w:h:x:y" output

#REV: also, should I autocrop first? :) cropdetect, etc.? In case there are black borders on video edges? But, don't really care heh.


#N) Make unique fname for sub-sampled output vid, check whether I can create in output dir (if not, error out). If it already exists, warn user?
