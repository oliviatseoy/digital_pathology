#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import argparse
import os
import sys
import math
from pathlib import Path
from datetime import datetime
import openslide
from PIL import Image


# In[ ]:


def get_reduction_factor(level):
    """"
    level 0: 1024 px, reduction factor=0
    level 1: 512 px , reduction factor=2
    level 2: 256 px , reduction factor=4
    level 3: 128 px , reduction factor=8
    level 4: 64 px  , reduction factor=16
    """
    return int(math.pow(2, level))

def is_whole_image_black(img):
    if img.mode == "RGBA":
        # Quick alpha check
        if img.getchannel("A").getextrema() == (0, 0):
            return True
    # Convert to grayscale and check if darkest and brightest are both 0
    gray_img = img.convert("L")
    return gray_img.getextrema() == (0, 0)

def get_image_file_extension(file_format):
    if file_format in ("JPEG", "JPEG-low"):
        return "jpg"
    elif file_format == "TIFF":
        return "tiff"
    elif file_format == "PNG":
        return "png"
    return None

def main(args):
    #------------------------------------------
    # Check inputs and create output directory
    #------------------------------------------
    # Check if input MRXS exists
    if not Path(args.mrxs).exists():
        sys.exit(f"ERROR: Input MRSX file [{args.mrxs}] does not exist!")

    # Check if output directory exist
    if not Path(args.outdir).is_dir():
        sys.exit(f"ERROR: Output folder [{args.outdir}] does not exist!")

    # In output directory, create folder named args.output_image_prefix.
    output_folder = Path(args.outdir) / args.op
    if output_folder.is_dir():
        sys.exit(f"ERROR: Output directory [{output_folder} already exist!")
    os.mkdir(output_folder)

    #------------------------------------------
    # Main
    #------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Open MRXS
    slide = openslide.OpenSlide(args.mrxs)

    log_entries = {}
    log_entries['mrxs'] = args.mrxs
    log_entries['output_directory'] = str(output_folder)
    log_entries['patch_size'] = args.patch_size
    log_entries['image_format'] = args.output_image_format
    log_entries['level_count'] = slide.level_count
    for level in range(slide.level_count):
        log_entries[f"dimension_lv{level}"] = slide.level_dimensions[level]

    LEVEL_HIGHEST_RES = 0
    ROI_UPPER_LEFT_LV0 = (0, 0)
    ROI_LOWER_RIGHT_LV0 = slide.dimensions
    ROI_size_x = ROI_LOWER_RIGHT_LV0[0] - ROI_UPPER_LEFT_LV0[0]
    ROI_size_y = ROI_LOWER_RIGHT_LV0[1] - ROI_UPPER_LEFT_LV0[1]

    # image level for screening black image
    level_reduced = 4
    reduction_factor = get_reduction_factor(level_reduced)

    # Number of image patches
    num_row = math.ceil(ROI_size_y / args.patch_size)
    num_column = math.ceil(ROI_size_x / args.patch_size)
    num_patches = num_row * num_column
    log_entries['num_row'] = num_row
    log_entries['num_column'] = num_column
    log_entries['num_patches'] = num_patches

    # Zero-pad patch and region idx
    zeropad_row = len(str(num_row))
    zeropad_column = len(str(num_column))

    num_patch_black = 0 
    num_patch_xblack = 0 

    lst_image_stat = []
    for row_idx, y in enumerate(range(ROI_UPPER_LEFT_LV0[1], ROI_LOWER_RIGHT_LV0[1], args.patch_size)):
        for col_idx, x in enumerate(range(ROI_UPPER_LEFT_LV0[0], ROI_LOWER_RIGHT_LV0[0], args.patch_size)):
            image_prefix = f"{args.op}.{row_idx:0{zeropad_row}d}_{col_idx:0{zeropad_column}d}.{y}_{x}"

            # Valid patch size
            patch_size_x = min(args.patch_size, slide.dimensions[0] - x)
            patch_size_y = min(args.patch_size, slide.dimensions[1] - y)

            # Skip if the image patch is fully transparent / black at lower resolution
            patch_size_x_reduced = math.floor(patch_size_x / reduction_factor)
            patch_size_y_reduced = math.floor(patch_size_y / reduction_factor)
            img_reduced = slide.read_region((x,y), level_reduced, (patch_size_x_reduced, patch_size_y_reduced)) 
            is_black = None
            if is_whole_image_black(img_reduced):
                is_black = True
                num_patch_black += 1
                image_name = '.'
            else:
                is_black = False
                num_patch_xblack += 1 

                # Obtain the image patch in highest resoluion
                ## OpenSlide.region_region: (x,y) is the top left pixel in the level 0 reference frame
                img_region = slide.read_region((x,y), LEVEL_HIGHEST_RES, (patch_size_x, patch_size_y)) 
                assert img_region.getbands() == ('R', 'G', 'B', 'A')

                # Pad the image with black border if the image region is smaller the patch size
                if (patch_size_x < args.patch_size) or (patch_size_y < args.patch_size):
                    img_padded = Image.new("RGBA", (args.patch_size, args.patch_size), (0, 0, 0, 0)) # Fully transparent black pixels
                    img_padded.paste(img_region, (0, 0)) # Paste the original image
                    img_region = img_padded

                # Save image to file
                ext = get_image_file_extension(args.output_image_format)
                image_name = f"{args.outdir}/{args.op}/{image_prefix}.{ext}"
                if args.output_image_format in ("JPEG", "JPEG-low"): #RGB
                    img_region = img_region.convert("RGB") # Convert RGBA to RGB
                    if args.output_image_format == "JPEG":
                        img_region.save(image_name, format='JPEG', quality=100, subsampling=0)
                    elif args.output_image_format == "JPEG-low":
                        img_region.save(image_name, format='JPEG')            
                elif args.output_image_format == "TIFF": #RGBA
                    img_region.save(image_name, format='TIFF')
                elif args.output_image_format == "PNG": #RGBA
                    img_region.save(image_name, format='PNG')
                else:
                    raise ValueError("Output format not supported.")
            lst_image_stat.append((image_name, row_idx, col_idx, y, x, patch_size_y, patch_size_x, int(is_black)))
        log_entries['num_black_patch'] = num_patch_black
        log_entries['num_non_black_patch'] = num_patch_xblack
    slide.close()

    #------------------------------------------
    # Write log file
    #------------------------------------------
    with open(f"{args.op}.image_patches.{timestamp}.log", 'w', encoding="utf-8") as fout:
        fout.write("Logs: MRXS to image patches\n")
        fout.write("[Summary]\n")
        fout.write(f"Timestamp\t{timestamp}\n")
        for k,v in log_entries.items():
            fout.write(f"{k}\t{v}\n")
        fout.write("\n[Patch information]\n")
        fout.write("\t".join(['image_name', 'row', 'column', 'x_offset', 'y_offset', 'patch_size_y', 'patch_size_x', 'is_black']) + '\n')
        for (image_prefix, row_idx, col_idx, y, x, patch_size_y, patch_size_x, is_black) in lst_image_stat:
            fout.write(f"{image_prefix}\t{row_idx}\t{col_idx}\t{y}\t{x}\t{patch_size_y}\t{patch_size_x}\t{is_black}\n")

if __name__ == "__main__":
    # ~/anaconda3/envs/openslide/bin/python
    parser = argparse.ArgumentParser(description="Crop Whole Slide Image in image patches")
    parser.add_argument("--mrxs", required=True)
    parser.add_argument("--op", required=True)
    parser.add_argument("--patch_size", type=int, required=True, help="Image patch size (e.g. 1024px)")
    parser.add_argument("--output_image_format", required=True, choices=['JPEG', 'TIFF', 'PNG', 'JPEG-low'])
    parser.add_argument("--outdir", required=True, help="output directory should exist.")
    #arguments = parser.parse_args('--mrxs /NetApp/users/deeplearn/Projects/marrow_morphology/raw_3dhistech/25H0340173-20x-EDF.mrxs --op haha --patch_size 1024 --output_image_format JPEG-low --outdir /NetApp/users/deeplearn/Projects/marrow_morphology/image_3dhistech/'.split())
    arguments = parser.parse_args()
    main(arguments)


# 
