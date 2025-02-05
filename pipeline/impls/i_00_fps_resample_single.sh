#!/bin/bash

#REV: upsample single passed video file (absolute/relative full path) to myfps, output to $outdir/filename.mkv (keeps old ext before .mkv)

vidpath=$1
myfps=$2
outdir=$3

mkdir -p $outdir

vidname=$(basename $vidpath)

EXT=".mkv"

mkdir -p $outdir
upsampled_vid="$outdir""/""$vidname""$EXT"

errdir="$outdir""_output"
mkdir -p $errdir

out="$errdir""/""$vidname""$EXT""_out"
err="$errdir""/""$vidname""$EXT""_err"


#CODEC=ffv1
##CODEC=mp4v
##CODEC=hvec
CODEC=hevc

#REV: Interpolate to target frame rate (upsample usually)
ffmpeg -progress pipe:1 -i $vidpath -filter:v minterpolate -r $myfps -vcodec $CODEC $upsampled_vid 1> $out 2> $err
