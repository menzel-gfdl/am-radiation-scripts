from numpy import mean

from .maps import global_mean, GlobalMeanVerticalPlot, LonLatMap, ZonalMeanMap


def grid(dataset, axis):
    """Finds the dimensions in the dataset using the axis attribute.

    Args:
        dataset: netCDF Dataset object.
        axis: String axis identifier.

    Returns:
        netCDF Variable object.
    """
    dims = []
    for value in dataset.variables.values():
        if len(value.dimensions) == 1 and "axis" in value.ncattrs() and \
           value.getncattr("axis").lower() == axis.lower():
            dims.append(value)
    if len(dims) == 0:
        raise ValueError("no grid variables found.")
    return dims


class DerivedMetric(object):
    """Helper class to calculate metrics.

    Attributes:
        data: Numpy data array.
        dimensions: Tuple of dimension names.
        units: String units description.
    """
    def __init__(self, data, dimensions, units):
        self.data = data
        self.dimensions = dimensions
        self.units = units

    def getncattr(self, name):
        return getattr(self, name)

    def __getitem__(self, key):
        return self.data[key]


class MetricsDataset(object):
    """Calculates metric maps and plots from model output datasets.

    Attributes:
        dataset: netCDF4 Dataset object.
        latitude: netCDF4 Variable object for the latitude dimension.
        longitude: netCDF4 Variable object for the longitude dimension.
        time: netCDF4 Variable object for the time dimension.
        vertical: List of netCDF Variable objects for the vertical dimensions.
    """
    def __init__(self, dataset):
        self.dataset = dataset
        self.time = grid(dataset, "t")[0]
        self.longitude = grid(dataset, "x")[0]
        self.latitude = grid(dataset, "y")[0]
        try:
            self.vertical = grid(dataset, "z")
        except ValueError:
            self.vertical = []

    def add_metric(self, metric_name, variable, time_method="average", time_index=0):
        """Adds a new variable to the MetricsDataset.

        Args:
            metric_name: Name the metric will be given.
            variable: String, netCDF4 Variable, or DerivedMetric object that will be
                      added to the dataset.
            time_method: String describing how the time dimension will be handled.
            time_index: Index of the time dimension to use if the time_method is set
                        to instantaneous.

        Raises:
            ValueError if time is not the slowest varying variable dimension or an
            invalid time_method value is used.
        """
        if isinstance(variable, str):
            data = self.dataset.variables[variable]
        else:
            data = variable
        dimensions = list(data.dimensions)
        units = data.getncattr("units")

        if time_method == "average":
            data = mean(data[...], axis=dimensions.index(self.time.name))
            dimensions.remove(self.time.name)
        elif time_method == "instantaneous":
            if dimensions.index(self.time.name) != 0:
                raise ValueError("time must be the slowest varying dimension.")
            data = data[time_index, ...]
            dimensions.remove(self.time.name)
        elif time_method == "time series":
            data = global_mean(data, self.latitude)
            dimensions = tuple(x for x in dimensions if not
                               (x == self.longitude.name or x == self.latitude.name))
        else:
            raise ValueError("A valid time_method must be specified.")

        setattr(self, metric_name, DerivedMetric(data, tuple(dimensions), units))

    def find_vertical(self, name):
        """Finds a vertical dimension in the dataset by name.

        Args:
            name: String name of the dimension.

        Returns:
            netCDF4 Variable object for the dimension.

        Raises:
            ValueError if the dimension is not found.
        """
        for dim in self.vertical:
            if name == dim.name:
                return dim
        raise ValueError("Could not find the vertical dimension.")

    def is_vertical(self, name):
        """Checks if an input dimension is a vertical dimension.

        Args:
            name: String name of the dimension.

        Returns:
            True if the variable is a vertical dimension or else False.
        """
        try:
            _ = self.find_vertical(name)
            return True
        except ValueError:
            return False

    def lon_lat_map(self, name):
        """Creates a longitude-latitude map for a metric.

        Args:
            name: String name of the metric.

        Returns:
            LonLatMap object describing the map.

        Raises:
            ValueError if the metric dimensions are not compatible with a
            longitude-latitude map.
        """
        metric = getattr(self, name)
        if metric.dimensions != (self.latitude.name, self.longitude.name):
            raise ValueError("Invalid dimensions for a lon-lat map.")
        return LonLatMap(getattr(self, name), self.longitude, self.latitude)

    def zonal_mean_map(self, name):
        """Creates a zonal-mean map for a metric.

        Args:
            name: String name of the metric.

        Returns:
            ZonalMeanMap object describing the map.

        Raises:
            ValueError if the metric dimensions are not compatible with a
            zonal-mean map.
        """
        metric = getattr(self, name)
        if len(metric.dimensions) == 3 and \
           metric.dimensions[-2:] == (self.latitude.name, self.longitude.name):
            y = self.find_vertical(metric.dimensions[0])
            return ZonalMeanMap(metric, self.latitude, y, ylabel=y.getncattr("units"),
                                invert_y_axis=y.getncattr("positive").lower() == "down")
        raise ValueError("Invalid dimensions for a zonal-mean map.")

    def global_mean_vertical_plot(self, name):
        """Creates a global mean versus height line plot for a metric.

        Args:
            name: String name of the metric.

        Returns:
            GlobalMeanVerticalPlot object describing the plot.

        Raises:
            ValueError if the metric dimensions are not compatible with a
            global mean versus height plot.
        """
        metric = getattr(self, name)
        if len(metric.dimensions) == 3 and  \
           metric.dimensions[-2:] == (self.latitude.name, self.longitude.name):
            y = self.find_vertical(metric.dimensions[0])
            return GlobalMeanVerticalPlot(y, y.getncattr("units"),
                                          global_mean(metric.data[...], self.latitude[...]),
                                          metric.getncattr("units"))
        raise ValueError("Invalid dimensions for a global mean line plot.")
