import cv2
import imageio
import time
from threading import Thread


class GIFCreator:

    def __init__(self, size=5, pause=0):
        self._image_buffer = []
        self._size = size
        self._pause = pause

        self._last = 0

        self.thread = None

    def __del__(self):
        if self.thread is not None and self.thread.isAlive():
            self.thread.join()

    def update(self, image):
        t = time.time()
        print(t - self._last, self._pause)
        if t - self._last > self._pause:
            self._image_buffer.append(image)
            self._last = t

    def save_to(self, path):
        # imageio.mimsave(path, self._image_buffer)
        self.thread = Thread(target=self._save, args=(path,))
        self.thread.start()

    def _save(self, path):
        # imageio.mimsave(path, self._image_buffer)
        with imageio.get_writer(path, mode='I') as writer:
            for img in self._image_buffer:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                writer.append_data(img_rgb)

    @property
    def images(self):
        return self._image_buffer

    def is_full(self):
        return len(self._image_buffer) >= self._size

    def __len__(self):
        return self._image_buffer.__len__()
