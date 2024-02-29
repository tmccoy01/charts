from osgeo import gdal

gdal.Open()


def xy_gt(x, y, gt) -> list:
    return gt[0] + x*gt[1] + y*gt[2], gt[3] + x*gt[4] + y*gt[5]


def get_res(sr, cksrs, width, height, minx, miny, maxx, maxy, gt) -> list:
    srck = gdal.osr.SpatialReference()
