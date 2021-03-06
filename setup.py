from distutils.core import setup

setup(name='geo-recommender',
      version='1.0',
      description='Building a scalable, geo-based recommender system with k-d trees, visualized using the MEAN stack',
      author='Hamza Harkous',
      author_email='hamza.harkous@gmail.com',
      url='https://github.com/harkous/geo-recommender',
      packages=['data_generation', 'data_store','utilities'],
     )