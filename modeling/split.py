import os
import numpy as np
import sys
import subprocess

group_name = sys.argv[1]
source_path = sys.argv[2]
test_path = sys.argv[3]
train_path = sys.argv[4]
percent = float(sys.argv[5])

images = os.listdir(source_path + '/' + group_name)
images = [f for f in images if (f.find('.jpg') > -1) or (f.find('.jpeg') > -1)]

index = int(len(images) * percent)
np.random.seed(333)
np.random.shuffle(images)
train, test = images[:index], images[index:]

for images in train:
    subprocess.call(['cp', '/'.join([source_path, group_name, images]), '/'.join([train_path, group_name, images])])

for images in test:
    subprocess.call(['cp', '/'.join([source_path, group_name, images]), '/'.join([test_path, group_name, images])])
