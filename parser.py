import argparse
import math


def _integer_between(minimum, maximum):
    def convert(value):
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be an integer") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return number
    return convert


def _finite_delay(value, *, positive):
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a finite number") from exc
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise argparse.ArgumentTypeError("must be positive and finite" if positive else "must be non-negative and finite")
    return number


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description="Multi-Protocol Traceroute Tool")
    parser.add_argument("input_file", help="Text file with destination IPs or hostnames")
    parser.add_argument("-m", "--max_ttl", type=_integer_between(1, 255), default=30, help="Last TTL (default: 30)")
    parser.add_argument("-M", "--min_ttl", type=_integer_between(1, 255), default=1, help="First TTL (default: 1)")
    parser.add_argument("-p", "--port", type=_integer_between(1, 65535), default=80, help="UDP/TCP destination port (default: 80)")
    parser.add_argument("-q", "--queries", type=_integer_between(1, 2147483647), default=3, help="Three-protocol series per hop (default: 3)")
    parser.add_argument("-t", "--timeout", type=lambda v: _finite_delay(v, positive=True), default=2.0, help="Per-probe timeout in seconds (default: 2)")
    parser.add_argument("-s", "--size", type=_integer_between(0, 65495), default=56, help="Payload bytes excluding headers (default: 56)")
    parser.add_argument("-w", "--wait", type=lambda v: _finite_delay(v, positive=False), default=0.1, help="Delay after each probe in seconds (default: 0.1)")
    parser.add_argument("-n", "--no-dns", action="store_true", help="Skip reverse DNS; target hostnames still require forward resolution")
    args = parser.parse_args(argv)
    if args.min_ttl > args.max_ttl:
        parser.error("--min_ttl must not exceed --max_ttl")
    return args
