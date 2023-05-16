from netCDF4 import Dataset

from .maps import Figure
from .metrics import MetricsDataset


def cloud_amount_maps(path, pdf=None):
    with Dataset(path, mode="r") as dataset:
        cloud_data = MetricsDataset(dataset)
        figure = Figure(num_rows=2, num_columns=2)
        for i, name in enumerate(["high_cloud_amount", "mid_cloud_amount",
                                  "low_cloud_amount", "total_cloud_amount"]):
            cloud_data.add_metric(name, name)
            cloud_map = cloud_data.lon_lat_map(name)
            figure.add_map(cloud_map, name, i + 1, [0, 1])
#       figure.display()
        if pdf is not None:
            pdf.savefig(figure.figure)


if __name__ == "__main__":
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages("output-report.pdf") as pdf:
        cloud_amount_maps("20000101.rad_clouds.nc", pdf)
