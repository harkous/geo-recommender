from math import radians, cos, sin, asin, sqrt, pi


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers.
    return c * r


def get_geo_offsets(lat, lon):
    """Computes the  offsets for latitude and longitude, given a specific distance
    Based on http://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters

    Args:
        lat:
        lon:
        dn:
        de:

    Returns:

    """
    # distances to move in meters to the north and the east
    dn=2000
    de=2000

    # Earth’s radius, sphere
    R = 6378137

    # Coordinate offsets in radians
    dLat = dn / R
    dLon = de / (R * cos(pi * lat / 180))

    # OffsetPosition, decimal degrees
    latO = dLat * 180 / pi
    lonO =  dLon * 180 / pi

    if lat+latO > 90:
        latO = 0
    elif lat +latO < -90:
        latO = 0

    if lon +lonO > 180:
        lonO = 0
    elif lon + lonO < -180:
        lonO = 0

    return (latO, lonO)


if __name__ == '__main__':
    print(haversine_distance(170.7486, 3.9864, 11.8205375, -136.681743))
    print(get_geo_offsets(12, 10.0))
