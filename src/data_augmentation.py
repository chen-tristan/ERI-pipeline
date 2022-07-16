import os

import numpy as np
import PIL.Image
from osgeo import gdal

from skimage.transform import resize, rotate


def chip_is_empty(img):
    """
    Check if region contains a label
    """
    labels_unique = np.unique(img)
    if 0 in labels_unique and len(labels_unique) == 1:
        return True
    else:
        return False

def get_rotated(image):
    """
    Return rotated images at 90, 180, 270
    """
    images = []
    for angle in [90, 180, 270]:
        image_rotate = rotate(image, angle, preserve_range=True)
        images.append(image_rotate)
    return images


def get_flipped(image):
    """
    Return flipped images (horizontal and vertical flip)
    """
    horizontal_flip = image[:, ::-1]
    vertical_flip = image[::-1, :]
    return [horizontal_flip, vertical_flip]


def load_file(path, resizeTo=None):
    """
    Read .tif file
    """
    dataSource = gdal.Open(path)
    if (dataSource is not None):
        bands = []
        for index in range(1, dataSource.RasterCount + 1):
            band = dataSource.GetRasterBand(index).ReadAsArray()
            if (resizeTo):
                band = resize(band, resizeTo, preserve_range=True, anti_aliasing=True).astype(np.int16)
            bands.append(band)
        image = np.dstack(bands)
        return image
    else:
        return None


def save_image(data, path, area_name, x, y, augment_num = 0):
    """
    Save chip as a .tif
    """
    im = PIL.Image.fromarray((data * 255).astype(np.uint8))
    im.save(f'{path}{area_name}_{x}_{y}_{augment_num}_mosaic.tif')


def save_label(data, path, area_name, x, y, augment_num = 0):
    """
    Save label as a .tif
    """
    data_fixed = np.squeeze(data, axis=2)
    im = PIL.Image.fromarray(data_fixed)
    im.save(f'{path}{area_name}_{x}_{y}_{augment_num}_labels.tif')


def sliding_window(image, step=(256, 256), window_size=(512, 512)):
    """
    Generator for each chip the sliding window
    """
    image_cols = image.shape[1]
    image_rows = image.shape[0]
    for y in range(0, image_rows, step[0]):
        for x in range(0, image_cols, step[1]):
            window = image[ y:y + window_size[0], x:x + window_size[1]]

            # Edge cases: shifts chip origin back if reaches end of image
            size = window.shape
            origin_x = x
            origin_y = y

            if size[1] != window_size[1]  and  size[0] != window_size[0]:
                origin_x = image_cols - window_size[1]
                origin_y = image_rows - window_size[0]
                window = image[origin_y : image_rows, origin_x : image_cols]
            elif size[1] != window_size[1]:
                origin_x = image_cols - window_size[1]
                window = image[ y:y + window_size[0], origin_x : image_cols]
            elif size[0] != window_size[0]:
                origin_y = image_rows - window_size[0]
                window = image[origin_y : image_rows, x:x + window_size[1]]

            yield (x, y, window)


def gen_data(images_dir, labels_dir, output_path, chip_size=256, channels=4, augment=False):
    """
    Split and augment data
    """
    image_names = os.listdir(images_dir)
    label_names = os.listdir(labels_dir)

    count_raw = 0
    count_augmented = 0
    for i in range(len(image_names)):
        file_name = os.path.splitext(image_names[i])[0]

        image_data = load_file(images_dir + image_names[i])
        image_labels = load_file(labels_dir + label_names[i])

        # print(image_data.shape, image_labels.shape)

        # image_labels = resize(image_labels, (image_data.shape[0], image_data.shape[1]), preserve_range=True, anti_aliasing=True).astype(np.int8)
        image = np.dstack([image_data, image_labels])

        for (x, y, window) in sliding_window(image):
            print("Augmenting:", file_name, x, y)
            data = np.array(window[:, :, : channels], dtype=np.int16)
            labels = np.array(window[:, :, -1:], dtype=np.int16)

            if chip_is_empty(labels):
                continue
            
            # data = normalize(data)
            labels_unique = np.unique(labels)

            image_raw = np.dstack([data, labels])
            img_augmented = [image_raw]

            if augment:
                img_augmented.extend(get_rotated(image_raw))
                flipped = []
                for img in img_augmented:
                    flipped.extend(get_flipped(img))
                img_augmented.extend(flipped)

            for i in range(len(img_augmented)):
                count_augmented += 1
                new_data = img_augmented[i][:,:,:channels]
                new_label = np.rint(img_augmented[i][:,:,-1:])

                np.clip(new_label, 0, None, out=new_label)

                # TODO: add make the folder if doesn't exist 
                save_image(new_data, output_path, file_name, x, y, i)
                save_label(new_label, output_path, file_name, x, y, i)
            
            count_raw += 1

    print('Raw Total: ', count_raw)
    print('Augmented Total: ', count_augmented)
    return


if __name__ == "__main__":
    # Turn these into args, absolute path
    # Directory for raw images
    images_dir = 'C:/nav/ds-capstone-ERI/src/raw_data/images/'
    # Directory for raw labels
    labels_dir = 'C:/nav/ds-capstone-ERI/src/raw_data/labels/'
    # Directory to put split/augmented images and labels
    output_path = 'C:/nav/ds-capstone-ERI/src/data/'
    
    gen_data(images_dir, labels_dir, output_path, augment=True)
