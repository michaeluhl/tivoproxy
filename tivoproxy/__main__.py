import argparse
import configparser

from tivoproxy.server import PNObjectServer
from tivoproxy.proxy import TiVoProxy


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="server.py")
    parser.add_argument('-c', '--config', action='store', dest='CONFIG_FILE', help='Specify a configuration file.')
    args = parser.parse_args()
    if not hasattr(args, 'CONFIG_FILE'):
        raise ValueError('Value required for Config File.')
    config = configparser.ConfigParser()
    config.read(args.CONFIG_FILE)
    ps = PNObjectServer(config=config,
                        served_class=TiVoProxy)
    ps.run()
