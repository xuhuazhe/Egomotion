export DILATION="/home/hxu/Reconstruction/bundler_sfm/data/dilation"
start=$SECONDS
for i in /home/hxu/Reconstruction/bundler_sfm/data/videos/testdir/downsample/
do
export DATASETS=$i
python ${DILATION}/test.py joint \
--work_dir ${i}output \
--image_list $DATASETS/images.txt \
--weights $DILATION/pretrained/dilation10_cityscapes.caffemodel \
--layers 10 \
--classes 19 \
--input_size 732 \
--gpu 0
done
duration=$(( SECONDS - start ))