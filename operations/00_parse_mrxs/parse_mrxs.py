#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import openslide
from PIL import Image
import os
import argparse

def main(args):
    with openslide.OpenSlide(args.mrxs_file_path) as slide:
        if args.command == "size":
            size_x, size_y = slide.dimensions
            print(f"{size_x},{size_y}")
        elif args.command == "label_image":
            if 'label' in slide.associated_images:
                # Get the label image as a PIL Image object
                label_image = slide.associated_images['label']
                if args.rotate:
                    label_image = label_image.rotate(180)
                file_ext = os.path.splitext(args.output_label_path)[1].lower()
                if file_ext in ('.jpg', '.jpeg'):
                    label_image = label_image.convert("RGB")
                    label_image.save(args.output_label_path, format="JPEG")
                elif file_ext in ('tif', 'tiff'):
                    label_image.save(args.output_label_path, format="TIFF")
                else:
                    raise ValueError("Output file extention is not supported.")
            else:
                raise ValueError("No 'label' image found in the MRXS file's associated images.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Common arguments
    parser.add_argument("mrxs_file_path")
    subparser = parser.add_subparsers(dest="command", required=True)
    # Get slide size
    parser_size = subparser.add_parser("size", help="Get slide dimensions")
    # Get label image
    parser_label = subparser.add_parser("label_image", help="Save label image")
    parser_label.add_argument("output_label_path")
    parser_label.add_argument("--rotate", action='store_true')
    arguments = parser.parse_args()
    main(arguments)

