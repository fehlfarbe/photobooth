from setuptools import setup

setup(name='photobooth',
      version='0.0.2',
      install_requires=['gphoto2',
                        'pillow',
                        'numpy',
                        'opencv-contrib-python',
                        'imutils',
                        'flask',
                        'gevent'
                        ]
      )
