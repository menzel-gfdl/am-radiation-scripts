import cartopy.crs as ccrs
from cartopy.util import add_cyclic
import matplotlib.pyplot as plt
from numpy import cos, linspace, mean, pi, sum, unravel_index


def zonal_mean(data, axis=-1):
    """Performs a mean over the longitude dimension.

    Args:
        data: Data array to perform the mean over.
        axis: The index of the latitude dimension.

    Returns:
        Numpy array of zonal mean values.
    """
    return mean(data, axis=axis)


def global_mean(data, latitude):
    """Performs a global mean over the longitude and latitude dimensions.

    Args:
        data: Data array to perform the mean over.
        latitude: Numpy array of latitude values [degrees].

    Returns:
        Numpy array of global mean values.
    """
    weights = cos(2.*pi*latitude/360.)
    return sum(zonal_mean(data)*weights, axis=-1)/sum(weights)


class Map(object):
    def __init__(self, x_data, y_data, data):
        self.x_data = x_data
        self.y_data = y_data
        self.data = data


class LonLatMap(Map):
    def __init__(self, data, longitude, latitude, units=None,
                 projection=ccrs.PlateCarree(), coastlines=True):
        self.data, self.x_data, self.y_data = add_cyclic(data[...], longitude[...], latitude[...])
        self.projection = projection
        self.coastlines = coastlines
        self.xlabel = "Longitude"
        self.ylabel = "Latitude"
        self.data_label = data.getncattr("units")


class ZonalMeanMap(Map):
    def __init__(self, data, latitude, y_data, units=None, ylabel=None, invert_y_axis=False):
        self.data = zonal_mean(data[...])
        self.x_data = latitude[...]
        self.y_data = y_data[...]
        self.invert_y_axis = invert_y_axis
        self.xlabel = "Latitude"
        self.ylabel = y_data.getncattr("units")
        self.data_label = data.getncattr("units")
        self.projection = None


class LinePlot(object):
    def __init__(self, x_data, xlabel, data, ylabel):
        self.x_data = x_data[...]
        self.xlabel = xlabel
        self.data = data[...]
        self.ylabel = ylabel


class GlobalMeanVerticalPlot(LinePlot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.x_data, self.data = self.data, self.x_data
        self.xlabel, self.ylabel = self.ylabel, self.xlabel
        self.invert_y_axis = True


class Figure(object):
    def __init__(self, num_rows=1, num_columns=1, size=(16, 12), title=None):
        """Creates a figure for the input number of plots.

        Args:
            num_rows: Number of rows of plots.
            num_columns: Number of columns of plots.
        """
        self.figure = plt.figure(figsize=size, layout="compressed")
        if title is not None:
            self.figure.suptitle(title.title())
        self.num_rows = num_rows
        self.num_columns = num_columns
        self.plot = [[None for y in range(num_columns)] for x in range(num_rows)]

    def add_map(self, map, title, position=1, colorbar_range=None):
        """Adds a Map object to the figure.

        Args:
            map: Map object.
            position: Position index for the plot in the figure.
        """
        plot = self.figure.add_subplot(self.num_rows, self.num_columns,
                                       position, projection=map.projection)
        if colorbar_range is None:
            levels = 60
        else:
            levels = linspace(colorbar_range[0], colorbar_range[1], 60)
        cs = plot.contourf(map.x_data, map.y_data, map.data, levels=levels,
                           transform=map.projection)
#       plot.colorbar(cs, label=map.data_label, fraction=0.46, pad=0.04)
        self.figure.colorbar(cs, ax=plot, label=map.data_label)
        if isinstance(map, LonLatMap):
            plot.coastlines()
            grid = plot.gridlines(draw_labels=True, dms=True)
            grid.top_labels = False
            grid.right_labels = False
        if isinstance(map, ZonalMeanMap) and map.invert_y_axis:
            plot.invert_yaxis()
        plot.set_title(title.replace("_", " ").title())
        plot.set_xlabel(map.xlabel)
        plot.set_ylabel(map.ylabel)

        # Store the plot in the figure object.
        x, y = self.plot_position_to_indices(position)
        self.plot[x][y] = plot

    def add_line_plot(self, line_plot, title, position=1):
        plot = self.figure.add_subplot(self.num_rows, self.num_columns,
                                       position)
        plot.plot(line_plot.x_data, line_plot.data)
        if isinstance(line_plot, GlobalMeanVerticalPlot) and line_plot.invert_y_axis:
            plot.invert_yaxis()
        plot.set_title(title)
        plot.set_xlabel(line_plot.xlabel)
        plot.set_ylabel(line_plot.ylabel)

        # Store the plot in the figure object.
        x, y = self.plot_position_to_indices(position)
        self.plot[x][y] = plot

    def display(self):
#       self.figure.colorbar(self.cs)
        plt.show()

    def plot_position_to_indices(self, position):
        """Converts from a plot position to its x and y indices.

        Args:
            position: Plot position (from 1 to num_rows*num_columns).

        Returns:
            The x and y indices for the plot.
        """
        return unravel_index(position - 1, (self.num_rows, self.num_columns))
