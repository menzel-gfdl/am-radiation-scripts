from netCDF4 import Dataset

from .maps import Figure
from .metrics import MetricsDataset


def aerosol_maps(path, pdf=None):
    """Creates the aerosol mass figures.

    Args:
        path: Path to the model dataset.
        output: Path to the output pdf.
    """
    with Dataset(path, mode="r") as dataset:
        aerosol_data = MetricsDataset(dataset)

        names = [name for name in dataset.variables.keys() if name.endswith("_col")]
        for name in names:
            figure = Figure(num_rows=1, num_columns=2)
            for i, aerosol in enumerate([name.rstrip("_col"), name]):
                aerosol_data.add_metric(aerosol, aerosol)
                if "_col" in aerosol:
                    aerosol_map = aerosol_data.lon_lat_map(aerosol)
                    aerosol = f"column-integrated {aerosol.rstrip('_col')}"
                else:
                    aerosol_map = aerosol_data.zonal_mean_map(aerosol)
                figure.add_map(aerosol_map, aerosol, i + 1)
#           figure.display()
            if pdf is not None:
                pdf.savefig(figure.figure)


if __name__ == "__main__":
    from matplotlib.backends.backend_pdf import PdfPages
    aerosol_maps("20000101.rad_aerosol.nc", pdf)
