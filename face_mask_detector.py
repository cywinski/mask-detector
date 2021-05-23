from typing import Optional
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import Sequential
import numpy as np
from dataset import Dataset
import cv2
from parameters import (
    IMG_WIDTH,
    IMG_HEIGHT,
    EPOCHS,
    SCALE_FACTOR,
    MIN_SIZE,
    MIN_NEIGHBORS,
    COLOR_DICT,
    CLASS_NAMES,
)


class FaceMaskDetector:
    def __init__(
        self,
        face_detector_path: str,
        ds: Optional[Dataset] = None,
        model_path: Optional[str] = None,
    ) -> None:
        """

        Args:
            model_path (str): path to trained model
            ds (Dataset): dataset used by model
            face_detector_path (str): path to face detector which will be used
        """

        self._face_detector = cv2.CascadeClassifier(face_detector_path)

        if model_path is not None:
            self._model = keras.models.load_model(model_path)

        if ds:
            self._ds = ds

    def create(self):
        self._create_model()
        self._compile_model()
        self._train_model()

    def _create_model(self) -> None:
        data_augmentation = keras.Sequential(
            [
                layers.experimental.preprocessing.RandomFlip(
                    "horizontal", input_shape=(IMG_HEIGHT, IMG_WIDTH, 3)
                ),
                layers.experimental.preprocessing.RandomRotation(0.1),
                layers.experimental.preprocessing.RandomZoom(0.1),
            ]
        )
        self._model = Sequential(
            [
                data_augmentation,
                layers.experimental.preprocessing.Rescaling(1.0 / 255),
                layers.Conv2D(16, 3, padding="same", activation="relu"),
                layers.MaxPooling2D(),
                layers.Conv2D(32, 3, padding="same", activation="relu"),
                layers.MaxPooling2D(),
                layers.Conv2D(64, 3, padding="same", activation="relu"),
                layers.MaxPooling2D(),
                layers.Dropout(0.2),
                layers.Flatten(),
                layers.Dense(128, activation="relu"),
                layers.Dense(len(CLASS_NAMES)),
            ]
        )

    def _compile_model(self) -> None:
        self._model.compile(
            optimizer="adam",
            loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
            metrics=["accuracy"],
        )

    def _train_model(self) -> None:
        self._history = self._model.fit(
            self._ds.train_ds, validation_data=self._ds.val_ds, epochs=EPOCHS
        )

    def save_model(self, path: str) -> None:
        self._model.save(path, overwrite=True)

    def get_model_summary(self):
        return self._model.summary()

    def _detect_faces(self, img_array):
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        rects = self._face_detector.detectMultiScale(
            gray,
            scaleFactor=SCALE_FACTOR,
            minNeighbors=MIN_NEIGHBORS,
            minSize=MIN_SIZE,
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        return rects

    def _draw_info_on_image(self, img_haar, x, y, w, h, predicted_class, confidence):
        # draw the face bounding box on the image
        cv2.rectangle(img_haar, (x, y), (x + w, y + h), COLOR_DICT[predicted_class], 2)
        cv2.rectangle(
            img_haar, (x, y - 40), (x + w, y), COLOR_DICT[predicted_class], -1
        )
        # draw the text info
        cv2.putText(
            img_haar,
            f"{predicted_class} {confidence:.2f}%",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

    def predict_img(self, img_array: np.array):
        """
        Predicts to which class belongs given image array.

        Predicted class - either 'with_mask' or 'without_mask' string.
        Confidence - percentage of model's confidence of classification.
        """
        # detect faces in image
        rects = self._detect_faces(img_array)
        predicted_class = ""
        confidence = 0.0
        img_haar = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        # loop over the bounding boxes
        for (x, y, w, h) in rects:
            # get only the face area
            face_img = img_haar[y : y + h, x : x + w]
            # resize the face area
            face_img = cv2.resize(face_img, (IMG_WIDTH, IMG_HEIGHT))
            batch = tf.expand_dims(face_img, 0)
            predictions = self._model.predict(batch)
            score = tf.nn.softmax(predictions[0])
            predicted_class = CLASS_NAMES[np.argmax(score)]
            confidence = 100 * np.max(score)
            self._draw_info_on_image(img_haar, x, y, w, h, predicted_class, confidence)

        if len(rects) == 0:
            predicted_class = "no face detected"
            # no faces detected
            textsize = cv2.getTextSize(predicted_class, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[
                0
            ]
            cv2.putText(
                img_haar,
                f"{predicted_class}",
                (
                    (img_haar.shape[1] - textsize[0]) // 2,
                    (img_haar.shape[0] + textsize[1]) // 2,
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 0),
                3,
            )
        return (
            predicted_class,
            float(confidence),
            cv2.cvtColor(img_haar, cv2.COLOR_RGB2BGR),
        )
