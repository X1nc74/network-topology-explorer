import sys
from parser import parse_arguments
from tracer import run_trace
from exporter import save_results

def main():
    args = parse_arguments()
    try:
        with open(args.input_file, 'r') as f:
            targets = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: File {args.input_file} not found.")
        sys.exit(1)

    all_results = {}

    print(f"Starting Multi-Protocol Traceroute on {len(targets)} targets...")
    
    for target in targets:
        print(f"\nTracing: {target}")
        results = run_trace(target, args)
        all_results[target] = results

    save_results(all_results, "output/results.txt", "output/results.json")
    print(f"\nDone! Results saved to output/ directory.")

if __name__ == "__main__":
    main()