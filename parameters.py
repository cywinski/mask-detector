import tensorflow as tf

DATA_DIR = "/home/bartosz/code/dataset"  # temporarily needs to be set locally
SAVE_DIR = "./model"
VAL_SPLIT = 0.2
SEED = 123
BATCH_SIZE = 32
IMG_WIDTH = 130
IMG_HEIGHT = 130
AUTOTUNE = tf.data.AUTOTUNE
CLASS_NAMES = ["with_mask", "without_mask"]
EPOCHS = 5
