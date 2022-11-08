import argparse
import json
import sys

from . import instruments, gnucash, report


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='Commands description', required=True)

    asset_data = subparsers.add_parser('data', help='Shows currency, fee, allocation data for provided list of tickers')
    asset_data.set_defaults(cmd='data')
    asset_data.add_argument('tickers', metavar='ticker', type=str, nargs='+',
                            help='a ticker of an asset to get info for')

    asset_allocation_gnucash = subparsers.add_parser(
        'gnucash-allocation',
        help='Generates allocation report based on GnuCash\'s Security Piechart and allocation data of its components')
    asset_allocation_gnucash.set_defaults(cmd='gnucash-allocation')
    asset_allocation_gnucash.add_argument(
        "-r", "--report-name",
        help="Name of report which contains securities allocation. Default: Securities",
        nargs='?', const=1, type=str,
        default="Securities")

    default_datafile = _get_latest_file()
    if default_datafile is None:
        asset_allocation_gnucash.add_argument("-f", "--datafile", required=True, type=str,
                                              help="GnuCash datafile (.gnucash)")
    else:
        asset_allocation_gnucash.add_argument(
            "-f", "--datafile",
            help="GnuCash datafile (.gnucash). Default: " + default_datafile,
            nargs='?', const=1, type=str,
            default=default_datafile)

    args = parser.parse_args()

    if args.cmd == 'data':
        print(json.dumps(instruments.get_data(args.tickers), indent=2, ensure_ascii=False))
    elif args.cmd == 'gnucash-allocation':
        parsed_gnucash_report = gnucash.get_value_by_instrument(report_name=args.report_name, datafile=args.datafile)
        report.generate(parsed_gnucash_report.value_by_instrument, parsed_gnucash_report.currency)


def _get_latest_file():
    # from https://github.com/sdementen/gnucash-utilities/blob/develop/piecash_utilities/config.py
    if sys.platform.startswith("linux"):
        import subprocess
        try:
            output_dconf = subprocess.check_output(["dconf", "dump", "/org/gnucash/GnuCash/history/"]).decode()
            from configparser import ConfigParser
            conf = ConfigParser()
            conf.read_string(output_dconf)
            return conf["/"]["file0"][1:-1]
        except:
            return None
    else:
        return None


if __name__ == '__main__':
    main()
