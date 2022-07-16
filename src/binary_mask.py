import json, os, glob

import gdal
from PIL import Image, ImageDraw
import numpy as np
import skimage.draw
from matplotlib import pyplot as plt

# Input JSON annotation file
def binary_mask(json_path):
  data = json.load(open(json_path))
  
  labels  = []

  for i in range(len(data)):
    height = data[i]['labels'][0]['original_height']
    width = data[i]['labels'][0]['original_width']

    masklist1 = []
    masklist2 = []
    
    # Get pixel coordinates of ellipse labels
    if 'ellipse' in data[i].keys():
      for j in range(len(data[i]['ellipse'])):
        mask = np.zeros([height, width, 1], dtype=np.uint8)

        temp = data[i]['ellipse'][j]
        # Convert from 0-100 to original width
        # https://labelstud.io/tags/ellipselabels.html
        c_radius = temp['radiusX'] * width / 100
        r_radius = temp['radiusY'] * height / 100
        c = temp['x'] * width / 100
        r = temp['y'] * height / 100
        shape = [height, width]

        # https://github.com/matterport/Mask_RCNN/issues/2154, 
        rr, cc = skimage.draw.ellipse(r, c, r_radius, c_radius, shape=shape, rotation=0.0)

        mask[rr, cc, 0] = 1
        masklist1.append(mask)
    
    # Get pixel coordinates of polygon labels
    if 'polygon' in data[i].keys():
      for j in range(len(data[i]['polygon'])):
        mask = np.zeros([height, width, 1], dtype=np.uint8)
        temp = data[i]['polygon'][j]

        r = np.array(temp['points'])[:, 1] * height / 100
        c = np.array(temp['points'])[:, 0] * width / 100

        rr, cc = skimage.draw.polygon(r, c)

        mask[rr, cc, 0] = 1
        masklist2.append(mask)
    
    # Combine all ellipse and polygon labels
    m1 = sum(masklist1)
    m2 = sum(masklist2)
    m = m1 + m2
    m[m > 1] = 1

    np_img = np.squeeze(m, axis=2)  # axis=2 is channel dimension 
    im = Image.fromarray((np_img * 255).astype(np.uint8))
    labels.append(im)
  
  # Return list of binary masks
  return(labels)

# To save image
# temp = binary_mask('data path')
# temp[0].save('nameoftif.tif')
# because label studio exports the json of all images, change the index of temp to the one that matches yours.
