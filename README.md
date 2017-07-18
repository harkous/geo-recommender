# Nearby People Recommender 

A project that illustrates building a [scalable, geo-based recommender system](https://www.youtube.com/watch?v=toX1EpxVSHU). It is built using an in-memory store with k-d trees, involves realistic data generation, and has a persistent storage mode with redis. The web GUI is implemented with the MEAN stack. 

## Goal
The goal of this project is to build a system that allows people to find "others nearby who are similar to them" based on certain criteria. Consider that each person has a record specifying the name, latitude, longitude and age. The system takes such a record as an input and returns a list of 10 similar people who are nearby.

The challenge is to make this system scalable enough so that it can handle 10-100 million entries and return the answer to the above query in 1 second for more than 95% of the queries. The returned people do not have to be the closest, but they should be reasonably close.

In what comes below, I describe the steps taken and the instructions to build the required recommender system, whhich relies on an in-memory datastore. The application backend and algorithm have been coded in Python. For the GUI, I developed a web app using JS, HTML, CSS. I cover the data generation phase, which I strived to make as realistic as possible in order to best simulate the real world.


## Application Demo (GUI)

At the beginning, it makes sense to show how the final application looks like. You can view the application in action in this video: https://www.youtube.com/watch?v=toX1EpxVSHU

[![Demo Video](http://img.youtube.com/vi/toX1EpxVSHU/0.jpg)](http://www.youtube.com/watch?v=toX1EpxVSHU)

The application provides the following features:

* Automatic recommendation computation:
    * Whenever the user changes the fields on the right (latitude, longitude, age), the home location adjusts, and the recommendations are automatically fetched from the server.
* Draggable home location:
    * The user can change the home location by dragging the marker on the map. The recommendation are automatically refetched and displayed.
* Clickable markers for knowing the recommendations:
    * The user can click on the markers around to check their profile picture, name, and age.
* Automatic Bounding of recommended friends within visible region




## Data Generation

Moving to the data behind this application, I collected the needed resources for producing realistic ages, names, and geographical coordinates. Then I generated **N** data samples for each of them independently. The data resources are present in the directory `sources_data`.



### Age

For the age, I produce samples based on the **world age distribution from 2015**, obtained from the [site of the U.S. Census Bureau](https://www.census.gov/idb/worldpopinfo.html). I exclude from this data the population with age ranges: (0-4, 5-9, 10-14, 15-19) as I assume this is an application not meant for children.  The last age range in my data is (100-104). Then I generate **N** random samples, weighted by the percentage of population in each range.

Obviously, one can go for a more elaborate version where age statistics are obtained per country. But this approximation is suitable for the purposes of this task.

### Names

For the names, I obtained the top 1000 male first names, the top 1000 female first names, and 88799 last names from the  [**Frequently Occurring Surnames from Census 1990**](http://www.census.gov/topics/population/genealogy/data/1990_census/1990_census_namefiles.html) dataset obtained from the U.S. Census Bureau.Then I combined the first names' data together as we will not distinguish by gender in our dataset. I generate **N** random samples by joining first names with last names at random. 

Evidently, I assumed that the names are all English-sounding, which is not very accurate (at least till 2016 🤔). However,  the main task would not be affected significantly by a different people-naming strategy. So that is sufficient for now.

### Locations

I believe that the most important part of data generation is producing realistic coordinates where real people are likely to live. I aimed at achieving two properties: 

1. Obtaining **coordinates of habitable areas**, obviously avoiding the water and snow bodies as much as possible
2. Sampling from these areas according to a **realistic population density**

This problem needs actual data about population as one cannot realistically determine the population of an area solely by relying on its geography. For that, I used one of the largest available datasets provided by NASA's [Socioeconomic Data and Applications Center (sedac)](http://sedac.ciesin.columbia.edu/). The dataset is the [“Gridded Population of the World, Version 4 (GPWv4): Population Count”](http://sedac.ciesin.columbia.edu/data/set/gpw-v4-population-count) (year 2015). It provides estimates for the number of people in each grid cell. A grid cell has an area of is 1 square kilometer. The grids cover the whole earth area.

Originally, the data was in `GeoTIFF` format. After learning a bit about this format and GIS data processing, I converted this format to a readable text (more precisely called XYZ format) with the coordinates of each grid cell and the population estimate in that grid. For that I used [QGIS](http://www.qgis.org/en/site/), an open source tool for processing  geospatial information. This data then looked like this:

```
#latitude,longitude,population_estimate
68.9583333333424235,33.1250000000014495,647.4014892578125
68.9583333333424235,33.2083333333347639,579.65362548828125
68.9583333333424235,33.2916666666681067,449.114715576171875
68.8750000000090807,32.9583333333347639,480.373565673828125
68.8750000000090807,33.0416666666681067,649.36285400390625
68.8750000000090807,33.1250000000014495,649.36279296875
```

To get an idea on how this data looks like on the map, see the following figure where I label with red dots the grids of habitable areas (even those with extremely low density):

![Habitable Areas](/resources/habitable_areas.png?raw=true "Habitable Areas")


To get an idea about the **population density** in these areas, check the following image that I generated using QGIS (darker reds imply higher population)

![Population Density](/resources/population_density.png?raw=true "Population Density")


For sampling efficiency, I excluded grids with populations of 100 or less people. I ended up with 129907 distinct coordinates. I generated N random samples from these coordinates. In order to avoid that people in each grid are in the same exact position, I added a random offset factor to the coordinates sampled in each grid. Due to the spherical nature of earth, this factor is a function of the coordinates of each grid center. Then my final data looked like this:


```
#latitude,longitude,latitude_offset,longitude_offset,population_estimate
68.958333,33.125000,0.017966,0.050039,647.401489
68.958333,33.208333,0.017966,0.050039,579.653625
68.958333,33.291667,0.017966,0.050039,449.114716
68.875000,32.958333,0.017966,0.049850,480.373566
68.875000,33.041667,0.017966,0.049850,649.362854
68.875000,33.125000,0.017966,0.049850,649.362793
```



## In Memory Data Store Creation

In order to achieve high speed lookups, I had to create an index for multi-dimensional searches. For that, I chose to build a **k-d-tree** based index. I selected this structure over alternatives such as r-trees or quadtrees because it is more suited for in-memory databases. It still has the features of Search, Insert, and Delete in O(log n) time in average. It requires O(n) space.

### Construction

The algorithm is documented in the code. 

I would like to mention here some specific decisions I took:


* Instead of computing the median of large arrays, I computed the median of a random sample 10,000 items for arrays larger than 50,000 (I found that these were the values below which there is no gain from taking a random sample). This significantly improved the speed by around 50% with N=10,000,000. 
* Instead of creating a 3D index with the latitude, longitude, and age, I chose to create a 2D index with the latitude and longitude only. In the algorithm, I only add to the results' queue candidates who are within the age range of the user **(currently +/- 5 years).**
* Instead of destroying the data when the applications stops, I added an option for persistence. This is achieved via a redis backend. Although this option works well for smaller databases (i.e., in the range of a few millions), scaling it appeared to be a challenge in the given time. So the support for persistence is there, but this is not turned on by default.


### Running Time: 
Below are the the results of profiling the recommender over 1000 runs on a machine with 1400 MHz CPUs (index construction is done on a single core). The device had enough memory to support the data and the overhead created (with 100 million records, memory consumption was peaking at 50 GB RAM). As the RAM was not the main target in this task, I did not dedicate a considerable part for doing so.

| N               | Average Running Time (sec)   | Running Time Percentage > 1 sec   |
| -------------   |:-------------:| -----:|
| 10,000,000      | 0.036 |     0%
| 30,000,000      | 0.107      |  0% |
| 50,000,000      | 0.155      |  0% |
| 100,000,000     | 0.198      |    0.6% |


## Running the Code

### Requirements' Installation:


For installing the basic packages, you will need **python3**. You will need [redis](https://redis.io) for persistence mode. Precisely, I tested with Python 3.4.3 and Python 3.5.1. For redis, I tested with version 2.6.9.

Then you can run the following script from the root of this project to install the requirements and setup the environment. This might take some time, depending on your environment (especially numpy and scipy packages):

```
bash install.sh
source venv/bin/activate
```



### Data Generation:

You can run the following script in order to generate data of size 1,000,000:

```
python data_generation/realistic_data_generator.py -s 1000000
```

### Data Store:

You can run the store as a simple server by launching the following script (make sure you are in the local python virtual environment (you can activate it using: `source venv/bin/activate`)

```
# run a server completely in memory (without persistence) with data size 1000000
python data_store/kd_tree_store.py -s 1000000  
```

Alternatively, you can run the server with persistence (using redis):

```
python data_store/kd_tree_store.py -s 1000000 --redis_mode
```

You can also choose to rebuild the index for redis via the parameter` --rebuild_index` and choose the port to run on via the `port` parameter (default is 5001)

### Testing the REST API:

```
#query recommendations for latitude of 43.1433, longitude of 23.41674 and age of 2
curl "localhost:5001/query?latitude=43.1433&longitude=23.41674&age=20"
 
```

### Profiling the Performance
You can obtain statistics on the performance of the server with respect to the nearest neighbor queries by running:

```
# num_loops is the number of queries to run. 
# num_neighbors is how many neighbors are needed. 
# age_proximity: is the maximum difference between the user age and results' ages 
curl "localhost:5001/profile?num_loops=100&num_neighbors=10&age_proximity=5"
```



### GUI Requirements and Setup:

I created another installation file for installing the gui, to keep things separate. You can run the following script that will install nodejs and the project requirements. It will also serve the app on port 3000 (if this port is already occupied, it will select another one and it will display this url when it's done).

```
bash gui_install.sh
```

The next time you want to launch the gui, you can simply do the following:

```
bash run_gui.sh
```

You can then go to your browser, where you will see an interface that looks like this:

![Application Screenshot](/resources/app_screenshot.png?raw=true "Application Screenshot")

The application structure is based on the [angular-material-mapping](https://github.com/ojlamb/angular-material-mapping) boilerplate but has been significantly changed to support the required functionalities.

**Note:** The current setup assumes that the gui and the data store servers are running on the same machine and the user is browsing the page from the same machine too. It is possible to change this by modifying the `apiUrl` inside the file `RecommenderService.js`  (currently it queries  `localhost:5001`). For example, one can change it to `server.com:5001` if the store is running on that machine.


## Limitations 
Below are some known issues:

* The application needs unit tests. 
* The redis version should be changed to support loading indices with different sizes at the same time (currently previous indices are overwritten)
