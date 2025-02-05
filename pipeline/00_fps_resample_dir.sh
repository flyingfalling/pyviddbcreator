#!/bin/bash
#REV: script 0
#REV: resample each video in dir $INDIR to $TARGFPS, renaming to name $OUTDIR/(without file extension)_$FPS_fps.mp4

INDIR=$1
TARGFPS=$2
OUTDIR=$3

flist=$(find $INDIR -mindepth 1 -type f ! -name "." ! -name ".." ! -name "")
echo "Script 00. Video list for upsampling FPS of vids in [$INDIR] to [$TARGFPS], output to [$OUTDIR]:"
#echo $flist

mkdir -p $OUTDIR 

myfunc() {
    f=$1
    bf=$(basename $f)
    fps=$2
    dir=$3
    echo "++++ BEGIN     Upsampling for video [$bf] (PATH=$f  FPS=$fps  DIR=$dir)"
    bash impls/i_00_fps_resample_single.sh $f $fps $dir
    echo "---- FINISHED  Upsampling for video [$bf] (PATH=$f  FPS=$fps  DIR=$dir)"
}

export -f myfunc

#parallel --dry-run myfunc ::: $flist
#N is nice?
#--jobs is number jobs
parallel --jobs 64 myfunc {1} {2} {3} ::: $flist ::: $TARGFPS ::: $OUTDIR

exit

for f in $flist;
do
    bf=$(basename $f)
    echo "Upsampling for video [$bf]"
    #sh impls/i_00_fps_resample_single.sh $f $TARGFPS $OUTDIR
done

echo "Finished upsampling FPS (script 00)."
