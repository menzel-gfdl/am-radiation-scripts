from argparse import ArgumentParser
from os import listdir
from os.path import join
from re import escape, match

from matplotlib.backends.backend_pdf import PdfPages

from am_radiation_scripts import aerosol_maps, cloud_amount_maps, flux_figures


def find_dataset(name, directory):
    for filename in listdir(directory):
        if match(r"[0-9]+\." + escape(name) + r"\.nc", filename):
            return join(directory, filename)
    raise ValueError(f"could not find file associated with {name}.")


def main():
    parser = ArgumentParser(description="Radiation analysis report.")
    parser.add_argument("directory", help="Path to input data directory")
    parser.add_argument("output", help="Name of output pdf", default="out.pdf")
    args = parser.parse_args()

    with PdfPages(args.output) as pdf:
        flux_figures(find_dataset("rad_fluxes", args.directory), pdf=pdf)
        cloud_amount_maps(find_dataset("rad_clouds", args.directory), pdf=pdf)
        aerosol_maps(find_dataset("rad_aerosol", args.directory), pdf)

if __name__ == "__main__":
    main()
