#REV: Applies PySceneDetect to content-based scene separation to single video file and prints output (as PANDA
#     dataframe/csv, and PySceneDetect statistics), to specific output file(s). Does not do actual splitting/re-encoding of scenes, since
#     I will separate them afterwards anyways.

#     For sanity, output the HTML thing too, for easy checking? Where are the images stored...?

#     Single threshold...




import pandas as pd

import math
import numpy as np

#import scenedetect

from scenedetect import VideoManager
from scenedetect import SceneManager
from scenedetect.stats_manager import StatsManager

from scenedetect.detectors import ContentDetector
from scenedetect.detectors import ThresholdDetector

import scenedetect.scene_manager;

import sys
import os

import argparse




#REV: video manager, scene manager, basetime, detector
def detectit( vidman, sceneman, basetime, detector ):
    sceneman.clear_detectors();
    sceneman.clear();
    
    sceneman.add_detector( detector );
    
    vidman.release();
    vidman.reset();
    vidman.set_downscale_factor();
    vidman.start();
    
    sceneman.detect_scenes(frame_source=vidman)
    
    return sceneman.get_scene_list(basetime);
 
def scenes_in_threshold( vidman, sceneman, basetime, detector, minlen_sec, maxlen_sec, threshold_cuts=[] ):
    
    myscenes1 = detectit( vidman, sceneman, basetime, detector );
    retscenes=[];
    retscenesf=[];

    #REV: ok, just append threshold_cuts to my cut list, and re-generate.
    #REV: concat lists.
    #REV: remove duplicates?
    mycuts = sceneman.get_cut_list(basetime);
    allcuts = sorted(mycuts + threshold_cuts);
    #myscenes = scenedetect.scene_manager.get_scenes_from_cuts( allcuts, basetime, vidman.get_duration()[0] );
    myscenes = scenedetect.scene_manager.get_scenes_from_cuts( allcuts, basetime, vidman.get_duration()[0] );

    for s in myscenes:
        mylen = s[1] - s[0];
        #print("Processing scene of length: {} sec".format(mylen));
        #for tc in threshold_cuts:
        #    if( tc > s[0] and tc < s[1] ):
        #        print("Excluding {} {} because slow fade/threshold cut {} lies within it".format( s[0], s[1], tc ) );
        #        continue;
        if( mylen >= minlen_sec and mylen <= maxlen_sec ):
            retscenes.append(s);
            retscenesf.append( [ s[0].get_frames(), s[1].get_frames()] );
            
    return retscenes, retscenesf;


def split_scenes_for_video(vid_path, out_path, contthresh, minlen_sec, maxlen_sec ):
    vidbase = vid_path.split('/')[-1];
    if( vidbase == '' ):
        exit(1);
    
        
    #REV: outdir is basename? Of filename? I.e. do I create it, or do I create a new one inside there (with datetime?).
    try:
        os.makedirs(out_path); #REV: mkdir -p
    except OSError:
        print ("WARNING: Creation of outdir [{}] failed (exists!) -- files will be overwritten".format(out_path));
    else:
        print ("Successfully created outdir [{}]!".format(out_path));

    #print("Video path: {}  (basename: {})  Stats file path (reading): {}       output to {}".format( vid_path, vidbase, stats_path, out_path ) );
    print("Video path: {}  (basename: {}). Output to path (will create if not existing): {}".format( vid_path, vidbase, out_path ) );
    print("Content threshold: {}. Minimum length of clips in seconds: {}  maximum: {}".format(contthresh, minlen_sec, maxlen_sec ));
    
    stats_out_file = out_path + '/stats.csv';
    df_out_file = out_path + '/scenes.csv';
    print("Will output (new) statistics to {}".format(stats_out_file) );
    print("Will output acceptable scenes as PANDA dataframe (CSV) to {}".format(df_out_file) );
    
    
    myvideo_manager = VideoManager( [vid_path] );
    mystats_manager = StatsManager()
    mybase_timecode = myvideo_manager.get_base_timecode()
    myscene_manager = SceneManager(mystats_manager)
    
    threshcuts_list=[];
    threshscenes_list=[];
    
    ################### FIRST, FADE DETECTION -- I.E. NOT CONTENT #####################
    #REV; what does this do?
    dofadedet=False; #REV: does nothing, overwritten anyways
    if( dofadedet ):
        thresh_thresh=12;
        print("Will run Threshold/fade detection first with threshold {}".format(thresh_thresh));

        threshdet = ThresholdDetector( min_scene_len=1 );
        threshscenes_list = detectit( myvideo_manager, myscene_manager, mybase_timecode, threshdet );
        threshcuts_list = myscene_manager.get_cut_list(mybase_timecode);

        print("Got cuts list from thresh: {}".format(threshcuts_list) );

        print("REV: will save stats file.");
        with open(stats_out_file, 'w') as stats_file:
            mystats_manager.save_to_csv(stats_file, mybase_timecode)


    ################## CONTENT DETECTION #################################################
    
    cols = [ 'VID', 'FPS', 'MINLEN_SEC', 'MAXLEN_SEC', 'CONT_THRESH', 'START_FRAME', 'END_FRAME', 'START_SEC', 'END_SEC', 'LEN_FRAMES', 'LEN_SECS' ];
    df = pd.DataFrame( columns=cols );
    
    print("REV: Executing content with threshold: {}".format(contthresh));
    contdet = ContentDetector( threshold=contthresh, min_scene_len=1 );
    times, frames = scenes_in_threshold( myvideo_manager, myscene_manager, mybase_timecode, contdet, minlen_sec, maxlen_sec, threshcuts_list );
    for time, frame in zip(times, frames):
        lensec = time[1].get_seconds() - time[0].get_seconds();
        lenframe = frame[1] - frame[0];
        fps = time[0].get_framerate();
        df.loc[ len(df) ] = [ vidbase, fps, minlen_sec, maxlen_sec, contthresh, frame[0], frame[1], time[0].get_seconds(), time[1].get_seconds(), lenframe, lensec ];
    
    print("REV: will save stats file (again) for content.");
    with open(stats_out_file, 'w') as stats_file:
        mystats_manager.save_to_csv(stats_file, mybase_timecode)
    
    print("REV: will save data frame (scenes) file.");
    df.to_csv(df_out_file);

    return;
    
    
if __name__ == '__main__':
    #REV: do stuff
    parser = argparse.ArgumentParser(description='Split Single Video Scenes with PySceneDetect');

    parser.add_argument('--inputvid', metavar='INPUT_VID', nargs=1, required=True,
                        help='Path and filename of input video to be processed.');

    parser.add_argument('--outdir', metavar='OUTPUT_DIR', nargs=1, required=True,
                        help='The full (preferably absolute) path of the directory to which output files will be written. Will be created.');
    
    parser.add_argument('--content_threshold', type=float, nargs=1, required=True, help='PySceneDetect content threshold (will detect scene split if difference between frames is > threshold, thus higher threshold means rarer scene splitting (more false negative splits), low threshold means more splits (more false positive splits due to normal video motion etc.).');

    parser.add_argument('--minlen_sec', type=float, nargs=1, required=False, help='Minimum length of scenes that will be saved to database (note, this is not passed to PySceneDetect min scene length).');

    parser.add_argument('--maxlen_sec', type=float, nargs=1, required=False, help='Max length of scenes that will be saved to database.');

    #parser.add_argument('--oldstats', nargs=1, required=False, help='Old stats file to read in (content already calculated, scene splitting will be faster?).');
    
    args = vars(parser.parse_args()); #REV: sys.argv by default
    print(args);
    
    #REV: do it.

    vid_path = args['inputvid'][0];
    out_path = args['outdir'][0];
    contthresh = args['content_threshold'][0]; #REV: let him specify multiple? :/

    #REV: output stats to path? Note stats can be re-used for later splitting...right?
    
    minlen_sec = 0;
    if( args['minlen_sec'] ):
        minlen_sec =  args['min_len_sec'];

    maxlen_sec = 100000000;
    if( args['maxlen_sec'] ):
        minlen_sec =  args['max_len_sec'];


    split_scenes_for_video( vid_path, out_path, contthresh, minlen_sec, maxlen_sec );
    
    exit(0);
# END MAIN
        
