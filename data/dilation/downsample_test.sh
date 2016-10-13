export DILATION="/home/hxu/Reconstruction/bundler_sfm/data/dilation"
start=$SECONDS
#export CUDA_VISIBLE_DEVICES=$2
export DATASETS=$1
python ${DILATION}/test.py joint \
--work_dir $1output \
--image_list $DATASETS/images.txt \
--weights $DILATION/pretrained/dilation10_cityscapes.caffemodel \
--layers 10 \
--classes 19 \
--input_size 610 \
--gpu $2
duration=$(( SECONDS - start ))
echo $duration