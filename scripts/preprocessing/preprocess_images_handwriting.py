#!/usr/bin/env python

"""
MIT License

Copyright (c) 2016 Harvard NLP

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Preprocess images for ease of training
import sys, os, argparse, json, glob, logging
import numpy as np
from PIL import Image
sys.path.insert(0, '%s'%os.path.join(os.path.dirname(__file__), '../utils/'))
from image_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

HANDWRITING_DATA_BASEDIR = '../../images/'

def process_args(args):
    parser = argparse.ArgumentParser(description='Process images for ease of training. Crop images to get rid of the background. For a cropped image of size (w,h), we pad it with PAD_TOP, PAD_BOTTOM, PAD_LEFT, PAD_RIGHT, and the result is of size (w+PAD_LEFT+PAD_RIGHT, h+PAD_TOP+PAD_BOTTOM. Then we see which bucket it falls into and pad them with whitespace to match the smallest bucket that can hold it. Finally, downsample images.')

    parser.add_argument('--input-dir', dest='input_dir',
                        type=str, required=True,
                        help=('Input directory containing orginal images.'
                        ))
    parser.add_argument('--output-dir', dest='output_dir',
                        type=str, required=True,
                        help=('Output directory to put processed images.'
                        ))
    parser.add_argument('--num-threads', dest='num_threads',
                        type=int, default=4,
                        help=('Number of threads, default=4.'
                        ))
    parser.add_argument('--crop-blank-default-size', dest='crop_blank_default_size',
                        type=str, default='[600,60]',
                        help=('If an image is blank, this is the size of the cropped image, should be a Json string. Default=(600,60).'
                        ))
    parser.add_argument('--pad-size', dest='pad_size',
                        type=str, default='[8,8,8,8]',
                        help=('We pad the cropped image to the top, left, bottom, right with whitespace of size PAD_TOP, PAD_LEFT, PAD_BOTTOM, PAD_RIGHT, should be a Json string. Default=(8,8,8,8).'
                        ))
    parser.add_argument('--buckets', dest='buckets',
                        type=str, default='[[240,100], [320,80], [400,80],[400,100], [480,80], [480,100], [560,80], [560,100], [640,80],[640,100], [720,80], [720,100], [720,120], [720, 200], [800,100],[800,320], [1000,200]]',
                        help=('Bucket sizes used for grouping. Should be a Json string. Note that this denotes the bucket size after padding and before downsampling.'
                        ))
    parser.add_argument('--downsample-ratio', dest='downsample_ratio',
                        type=float, default=2.,
                        help=('The ratio of downsampling, default=2.0.'
                        ))
    parser.add_argument('--log-path', dest="log_path",
                        type=str, default='log.txt',
                        help=('Log file path, default=log.txt'
                        ))
    parser.add_argument('--postfix', dest='postfix',
                        type=str, default='.png',
                        help=('The format of images, default=".png".'
                        ))
    parameters = parser.parse_args(args)
    return parameters

def main_parallel(l):
    filename, postfix, output_filename, crop_blank_default_size, pad_size, buckets, downsample_ratio = l
    postfix_length = len(postfix)
    status = crop_image(filename, output_filename, crop_blank_default_size)
    if not status:
        logging.info('%s is blank, crop a white image of default size!'%filename)
    status = pad_group_image(output_filename, output_filename, pad_size, buckets)
    if not status:
        logging.info('%s (after cropping and padding) is larger than the largest provided bucket size, left unchanged!'%filename)
	os.remove(output_filename)
	return
    status = downsample_image(output_filename, output_filename, downsample_ratio)

def get_filenames_from_csv(path_to_csv):
  lines = open(path_to_csv, "r").readlines()
  paths = []
  for i, l in enumerate(lines):
    if i == 0:
      continue
    paths.append(HANDWRITING_DATA_BASEDIR + l[:l.index("|")])
  return paths

def main(args):
    parameters = process_args(args)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s',
        filename=parameters.log_path)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info('Script being executed: %s'%__file__)

    output_dir = parameters.output_dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    input_dir = parameters.input_dir
    postfix = parameters.postfix
    crop_blank_default_size = json.loads(parameters.crop_blank_default_size)
    pad_size = json.loads(parameters.pad_size)
    buckets = json.loads(parameters.buckets)
    downsample_ratio = parameters.downsample_ratio
    
    filenames = get_filenames_from_csv(HANDWRITING_DATA_BASEDIR + "data/image_path_label.csv")
    #filenames = glob.glob(os.path.join(input_dir, '*'+postfix))
    logging.info('Creating pool with %d threads'%parameters.num_threads)
    pool = ThreadPool(parameters.num_threads)
    logging.info('Jobs running...')
    #results = pool.map(main_parallel, [(filename, postfix, os.path.join(output_dir, filename[len(HANDWRITING_DATA_BASEDIR):]), crop_blank_default_size, pad_size, buckets, downsample_ratio) for filename in filenames])
    results = pool.map(main_parallel, [(filename, postfix, os.path.join(output_dir, os.path.basename(filename)), crop_blank_default_size, pad_size, buckets, downsample_ratio) for filename in filenames])

    pool.close()
    pool.join()

if __name__ == '__main__':
    main(sys.argv[1:])
    logging.info('Jobs finished')