# two inputs: image_directory, bulder_output

image_folder=$1
bundler_output=$2

# call python file
python plot_point.py $image_folder $bundler_output

image_folder_output=$image_folder"_annotate"

#ffmpeg: images to videos
cd $image_folder_output

# you might want to change -r based on your down sample rate
ffmpeg \
-f image2 \
-i %*.jpg \
-crf 0 \
-preset veryslow \
-threads 16 \
-r 15 \
-vcodec libx264 \
-vf "setpts=8.0*PTS" \
../annotate.mkv

# turn on this if you need
# remove the generated intermediate folder

#cd ..
#rm -r $image_folder_output
