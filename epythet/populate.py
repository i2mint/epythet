from wads.populate import *

if __name__ == '__main__':
    import argh  # TODO: replace by argparse, or require argh in epythet?

    argh.dispatch_command(populate_pkg_dir)
