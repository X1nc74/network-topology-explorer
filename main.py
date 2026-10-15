import sys
from exporter import save_results
from parser import parse_arguments
from tracer import TraceInterrupted, run_trace


def main(argv=None):
    args = parse_arguments(argv)
    try:
        with open(args.input_file, encoding="utf-8") as file:
            targets = [line.strip() for line in file if line.strip()]
    except OSError as exc:
        print(f"Cannot read target file: {exc}", file=sys.stderr)
        return 1
    if not targets:
        print("The target file contains no destinations.", file=sys.stderr)
        return 1

    all_results = {}
    exit_code = 0
    print(f"Starting Multi-Protocol Traceroute on {len(targets)} targets...")
    try:
        for target in targets:
            print(f"\nTracing: {target}")
            try:
                all_results[target] = run_trace(target, args)
                if any(p.get("status") == "ERROR" for hop in all_results[target] for p in hop["probes"]):
                    exit_code = 1
            except TraceInterrupted as exc:
                all_results[target] = exc.results
                print("\nInterrupted. Saving collected results and stopping.")
                exit_code = 130
                break
            except OSError as exc:
                print(f"Cannot trace {target}: {exc}", file=sys.stderr)
                all_results[target] = []
                exit_code = 1
    except KeyboardInterrupt:
        print("\nInterrupted. Saving completed targets.")
        exit_code = 130
    save_results(all_results, "output/results.txt", "output/results.json")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
