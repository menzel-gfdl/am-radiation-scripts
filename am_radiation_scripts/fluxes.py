from collections import namedtuple, OrderedDict

from netCDF4 import Dataset

from .maps import Figure, global_mean, Map
from .metrics import DerivedMetric, MetricsDataset


class Fluxes(MetricsDataset):
    # Helper dictionaries.
    regimes = {"longwave": "l", "shortwave": "s"}
    sky = {
        "all": "",
        "clean": "af",
        "clean-clear": "csaf",
        "clear": "cs",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.vertical[0].getncattr("positive").lower() == "down":
            self.toa = 0
            self.surface = -1
        else:
            self.toa = -1
            self.surface = 0

    def flux(self, regime, direction, conditions, location=None):
        directions = {"down": "d", "up": "u"}
        flux = self.dataset.variables[f"r{self.regimes[regime]}{directions[direction]}{self.sky[conditions]}"]
        if location is None:
            return DerivedMetric(flux[...], flux.dimensions, flux.getncattr("units"))
        dimensions = list(flux.dimensions)
        if not self.is_vertical(dimensions[1]):
            raise ValueError("The second slowest dimension must be a vertical dimension.")
        data = flux[:, getattr(self, location), ...]
        dimensions.remove(dimensions[1])
        units = flux.getncattr("units")
        return DerivedMetric(data, dimensions, units)

    def flux_down(self, regime, conditions, location=None):
        return self.flux(regime, "down", conditions, location)

    def flux_up(self, regime, conditions, location=None):
        return self.flux(regime, "up", conditions, location)

    def toa_energy_balance(self, regime, conditions):
        """Calculates the difference between the energy entering and leaving the
           top of the atmosphere.

        Args:
            regime: Spectral regime (i.e., longwave or shortwave.
            conditions: Sky conditions.
        """
        up = self.flux_up(regime, conditions, location="toa")
        data = self.flux_down(regime, conditions, location="toa")[...] - up[...]
        return DerivedMetric(data, up.dimensions, up.units)

    def atmospheric_divergence(self, regime, conditions):
        """Calculates the difference between the energy entering and leaving the atmosphere.

        Args:
            regime: Spectral regime (i.e., longwave or shortwave.
            conditions: Sky conditions.
        """
        surface_down = self.flux_down(regime, conditions, location="surface")
        surface_up = self.flux_up(regime, conditions, location="surface")
        toa_down = self.flux_down(regime, conditions, location="toa")
        toa_up = self.flux_up(regime, conditions, location="toa")
        data = toa_down[...] + surface_up[...] - (toa_up[...] + surface_down[...])
        return DerivedMetric(data, toa_up.dimensions, toa_up.units)

    def heating_rate(self, regime, conditions):
        heating = self.dataset.variables[f"tntr{self.regimes[regime]}{self.sky[conditions]}"]
        units, factor = heating.getncattr("units"), 1
        if units == "K s-1":
            units, factor = "K day-1", 34*3600
        return DerivedMetric(heating[...]*factor, heating.dimensions, units)


def case_list():
    Case = namedtuple("Case", ["data", "baseline", "title"])
    return [Case("clean-clear", None, "Clean-clear Sky"),
            Case("clean", "clean-clear", "Cloud Effects"),
            Case("all", "clean", "Aerosol Effects"),
            Case("all", None, "All Sky")]


def quad_maps(fluxes, metric, regime, title, location=None, pdf=None, map_method="lon_lat_map"):
    """Create a figure containing (2 x 2) maps, where when the first three are summed
       they produce the fourth.

    Args:
        fluxes: Fluxes object.
        metric: String name of a Fluxes method.
        regime: String describing the spectral range (longwave or shortwave).
        title: String title for the figure.
        location: String vertical location for the metric (toa or surface).
        pdf: PdfPages object to write the output to.
        map_method: String describing which type of maps to
                    create (lon_lat_map or zonal_mean_map).

    Returns:
        OrderedDict of DerivedMetric objects.
    """
    figure = Figure(num_rows=2, num_columns=2, title=title)
    output = OrderedDict()
    for i, case in enumerate(case_list()):
        name = f"{case.data} {metric.replace('_', ' ')}"
        args = [x for x in [regime, case.data, location] if x is not None]
        derived_metric = getattr(fluxes, metric)(*args)
        if case.baseline is not None:
            args = [x for x in [regime, case.baseline, location] if x is not None]
            baseline = getattr(fluxes, metric)(*args)
            derived_metric.data[...] -= baseline.data[...]
        fluxes.add_metric(name, derived_metric)
        map = getattr(fluxes, map_method)(name)
        if isinstance(map, Map):
            title = f"{case.title} [Mean: {global_mean(map.data, map.y_data):.2f}]"
            figure.add_map(map=map, title=title, position=i + 1)
        else:
            title = f"{case.title}"
            figure.add_line_plot(map, title=title, position=i + 1)
        output[case.title] = derived_metric
#   figure.display()
    if pdf is not None:
        pdf.savefig(figure.figure)
    return output

def net_maps(fluxes, lw_metric, sw_metric, title, pdf=None, map_method="lon_lat_map"):
    figure = Figure(num_rows=2, num_columns=2, title=title)
    for i, case in enumerate(case_list()):
        name = f"{case.data} net"
        lw, sw = lw_metric[case.title], sw_metric[case.title]
        derived_metric = DerivedMetric(lw[...] + sw[...], lw.dimensions, lw.units)
        fluxes.add_metric(name, derived_metric)
        map = getattr(fluxes, map_method)(name)
        if isinstance(map, Map):
            title = f"{case.title} [Mean: {global_mean(map.data, map.y_data):.2f}]"
            figure.add_map(map=map, title=title, position=i + 1)
        else:
            title = f"{case.title}"
            figure.add_line_plot(map, title=title, position=i + 1)
#   figure.display()
    if pdf is not None:
        pdf.savefig(figure.figure)


def flux_figures(dataset, pdf=None):
    with Dataset(dataset) as dataset:
        fluxes = Fluxes(dataset)
        lw_energy_balance = quad_maps(fluxes, "flux_up", "longwave",
                                      "Out-going TOA Longwave Radiation", "toa", pdf)
        quad_maps(fluxes, "flux_down", "longwave",
                  "Downard Surface Longwave Radiation", "surface", pdf)
        quad_maps(fluxes, "flux_up", "shortwave",
                  "Out-going TOA Shortwave Radiation", "toa", pdf)
        quad_maps(fluxes, "flux_down", "shortwave",
                  "Downward Surface Shortwave Radiation", "surface", pdf)
        sw_energy_balance = quad_maps(fluxes, "toa_energy_balance", "shortwave",
                                      "TOA Shortwave Energy Balance", pdf=pdf)
        net_maps(fluxes, lw_energy_balance, sw_energy_balance, "TOA Energy Balance", pdf=pdf)
        lw_divergence = quad_maps(fluxes, "atmospheric_divergence", "longwave",
                                  "Longwave Atmospheric Divergence", pdf=pdf)
        sw_divergence = quad_maps(fluxes, "atmospheric_divergence", "shortwave",
                                  "Shortwave Atmospheric Divergence", pdf=pdf)
        net_maps(fluxes, lw_divergence, sw_divergence, "Atmospheric Divergence", pdf=pdf)
        lw_heating = quad_maps(fluxes, "heating_rate", "longwave", "Longwave Radiative Heating Rate",
                               pdf=pdf, map_method="zonal_mean_map")
        sw_heating = quad_maps(fluxes, "heating_rate", "shortwave", "Shortwave Radiative Heating Rate",
                               pdf=pdf, map_method="zonal_mean_map")
        net_maps(fluxes, lw_heating, sw_heating, "Atmospheric Heating Rate",
                 pdf=pdf, map_method="zonal_mean_map")
        lw_heating = quad_maps(fluxes, "heating_rate", "longwave",
                               "Global Mean Longwave Radiative Heating Rate",
                               pdf=pdf, map_method="global_mean_vertical_plot")
        sw_heating = quad_maps(fluxes, "heating_rate", "shortwave",
                               "Global Mean Shortwave Radiative Heating Rate",
                               pdf=pdf, map_method="global_mean_vertical_plot")
        net_maps(fluxes, lw_heating, sw_heating, "Global Mean Radiative Heating Rate",
                 pdf=pdf, map_method="global_mean_vertical_plot")


if __name__ == "__main__":
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages("output-fluxes.pdf") as pdf:
        flux_figures("../../20000101.rad_fluxes.nc", pdf)
