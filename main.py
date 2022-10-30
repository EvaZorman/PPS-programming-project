"""
Main entrypoint of the project.

A general instruction for the project is that the topology of the
network needs to be dynamic and flexible. The user can decide how
will the network be assembled, and any other route preferences. This
will be handled by the following steps:

1. The network settings can be changed using command line arguments
2. Some sort of UI will need to make sure the data is displayed and
understandable to the user
"""
import argparse

from simulation import (
    generate_routing_paths,
    setup_as,
    setup_simulation,
)


def parse_args():
    """
    Parse arguments for the main program.
    """
    parser = argparse.ArgumentParser(
        description="A scalable and customizable simulator of AS routing using BGP-4 "
        "protocol."
    )
    parser.add_argument(
        "--as-number",
        type=int,
        help="The number of AS systems to be used in the simulation.",
        default=10,
    )
    parser.add_argument(
        "--run-preset",
        action="store_true",
        help="The number of AS systems to be used in the simulation.",
    )
    return parser.parse_args()


def main():
    """
    Entrypoint for the simulation program.
    """
    args = parse_args()
    print(
        "Welcome to our scalable and customizable simulator of AS routing using "
        "the BGP-4 protocol.\nThe current network topology is the following: \n"
        f"\t Number of AS's: {args.as_number}\n".expandtabs(2)
    )

    if args.run_preset:
        print("This is a test setup which will always have the same network topology!")
        routes = {
            "AS1": {4, 7},
            "AS10": {5},
            "AS2": {9, 3, 7},
            "AS3": {8, 2, 5, 7},
            "AS4": {1, 5, 7},
            "AS5": {10, 3, 4},
            "AS6": {7},
            "AS7": {1, 2, 3, 4, 6},
            "AS8": {3},
            "AS9": {2},
        }
        setup_simulation(routes)
    else:
        as_data = setup_as(args.as_number)
        routes = generate_routing_paths(args.as_number, as_data)
        setup_simulation(routes)


if __name__ == "__main__":
    main()
