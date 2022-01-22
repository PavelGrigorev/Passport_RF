# -*- coding: utf-8 -*-
"""Untitled1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1yyBwtkxfN0JOs-QOI4IVshvK8m808kMA
"""

# Commented out IPython magic to ensure Python compatibility.
import tensorflow as tf
import tensorflow.keras.models as M
import tensorflow.keras.layers as L
import tensorflow.keras.optimizers as O
import tensorflow.keras.losses as Loss
import tensorflow.keras.backend as K
import tensorflow.keras.utils as U

import albumentations as albu

import os, sys, time
import numpy as np
import cv2
#import trdg.generators as G
from PIL import Image
from IPython.display import display
import json

import matplotlib.pyplot as plt
# %matplotlib inline

chars = ' 0123456789АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ.-'
char_index = dict((chr, idx) for idx, chr in enumerate(chars))
index_char = dict((idx, chr) for idx, chr in enumerate(chars))

PATH_WEIGHT = 'weights/model_7.h5'
max_h = 64


# https://arxiv.org/pdf/1507.05717.pdf
# https://github.com/kutvonenaki/simple_ocr
# https://github.com/MaybeShewill-CV/CRNN_Tensorflow

def create_model(input_shape, dictionary_size, use_lstm=False):
  input = x = L.Input(input_shape)
  x = L.Conv2D(8, 3, activation='relu', padding='same')(x)
  x = L.Conv2D(16, 3, activation='relu', padding='same')(x)
  x = L.MaxPool2D()(x)

  x = L.Conv2D(32, 3, activation='relu', padding='same')(x)
  x = L.Conv2D(64, 3, activation='relu', padding='same')(x)
  x = L.MaxPool2D()(x)

  x = L.TimeDistributed(L.Flatten())(x)

  #x = L.Dense(512, activation='relu')(x)
  x = L.Dense(128, activation='relu')(x)

  if use_lstm:
    x = L.Bidirectional(L.LSTM(64, return_sequences=True))(x)
    x = L.Bidirectional(L.LSTM(64, return_sequences=True))(x)

  x = L.Dense(dictionary_size + 1, activation='softmax')(x)
  return M.Model(input, x)

model = create_model((None, max_h, 3), len(chars), True)
model.load_weights(PATH_WEIGHT)

def prepare_image(image, width, height):
    w = image.width + 4 - (image.width % 4)
    resized_image = Image.new(image.mode, (width, height), (255, 255, 255)) # белый фон
    resized_image.paste(image.resize((w, height)), (0, 0)) # Вставляем в верхний левый угол
    resized_image = np.array(resized_image).transpose((1, 0, 2)) / 255.0
    return resized_image

#### Проверка Модели

def OCR_predict(image_path, bbox_):
  test_image = cv2.imread(image_path)[..., ::-1]
    
  bc_images = [] # Будет содержать обрезанные картинки
  idx_list = [] # Будет содержать индексы для дальнейшей обработки
  IDX_DEL = (0, 11) # Удаляем фото и подпись

  for bbox in bbox_:

    if bbox[0] in IDX_DEL: continue
    
    y1, x1, y2, x2 = bbox[1]
    try:
      
      image_crop = Image.fromarray(test_image[x1:x2, y1:y2])
      
      if bbox[0] == 10: # Если картинка с серией
        image_crop = image_crop.rotate(90, expand=True)

      bc_images.append(image_crop)
      idx_list.append(bbox[0])
    except: 
      print(image_path)
      continue


  max_w = max([image.width for image in bc_images])

  bc = np.array([prepare_image(image, max_w, max_h) for image in bc_images])

  pred_probs = model.predict(bc)
  input_length = np.array([bc.shape[1] // 4] * bc.shape[0])
  pred_tensor, _ = K.ctc_decode(pred_probs, input_length, greedy=True)
  pred_labels = K.get_value(pred_tensor[0])
  predictions = [''.join([index_char[i] for i in word if i != -1]) for word in pred_labels.tolist()]

  return predictions, idx_list
