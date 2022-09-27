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
from collections import defaultdict
from pprint import pprint

from simulation import start_simulation


def parse_args():
    parser = argparse.ArgumentParser(
        description="A scalable and customizable simulator of inter-AS routing using BGP "
        "protocol."
    )
    parser.add_argument(
        "--as-number",
        type=int,
        help="The number of AS systems to be used in the simulation.",
        default=5,
    )
    parser.add_argument(
        "--router-number",
        type=int,
        help="The number of routers within each AS to be used in the simulation.",
        default=10,
    )
    return parser.parse_args()


def print_path_table(net_dict):
    for key, item in list(net_dict["paths"].items()):
        paths_str = f"{key}:\t{item}".expandtabs(8)
        print(paths_str)

    print()
    return


def setup_router_paths(as_num, router_num):
    print(
        "By default, each AS will be connected to other random AS's.Hence the network \n"
        "topology will be different each simulation, unless configured otherwise.\n"
    )

    network_dict = {
        "AS_topology": defaultdict(list),
        "paths": {},
    }

    # distribute the routers to their corresponding AS, based on simple modulo arithmetics
    for i in range(router_num):
        as_location = i % as_num
        network_dict["AS_topology"][f"A{as_location+1}"].append(f"R{i+1}")

        # create empty path sets for each router
        network_dict["paths"][f"R{i+1}"] = []

    custom_paths = input(
        "Do you wish to set any specific routes for any of the routers that will be created? Y/N\n"
    )
    if custom_paths.upper() == "N":
        return network_dict

    if custom_paths.upper() != "Y":
        print("Wrong answer :O")
        return None

    loop = True
    while loop:
        # Get the router to customise its path
        router_of_choice = input(
            f"Which router's path would you like to customise?\n"
            f"Possible choices: {list(network_dict['paths'])}\n"
            "You can exit the customisation at any point by selecting Q.\n"
        ).upper()
        # exit or drop incorrect input
        if router_of_choice == "Q":
            loop = False
            continue

        elif router_of_choice not in network_dict["paths"]:
            print("Incorrect value chosen. Aborting customization...\n")
            continue

        choice_path = input(
            f"To which routers would you like your router to have a path?\n"
            f"Possible choices: {list(network_dict['paths'])}\n"
            "You can also set a list of routes you wish to add, e.g. <r1 r2 r4>.\n"
            "You can exit the customisation at any point by selecting Q.\n"
        ).upper()

        paths = choice_path.split(" ")

        if "Q" in paths:
            loop = False
            continue

        # get the AS of the chosen router
        router_as = [
            i
            for i in network_dict["AS_topology"]
            if router_of_choice in network_dict["AS_topology"][i]
        ]

        # if any element in paths is also in the AS of the chosen router, we have some
        # overlapping in paths that we do not want, skip the choice made
        if bool(set(paths) & set(network_dict["AS_topology"][router_as[0]])):
            print("Incorrect value chosen. Aborting customization...\n")
            continue

        tmp_paths = set(network_dict["paths"][router_of_choice])

        if set(paths).issubset(tmp_paths):
            print("Path(s) already contained. Aborting customization...\n")
            continue

        tmp_paths.update(set(paths))
        network_dict["paths"][router_of_choice] = list(tmp_paths)

        print_path_table(network_dict)

    return network_dict


def generate_routing_paths(as_number, router_number, custom_paths=None):
    """
    Do we want to make all the routers be able to talk to each router in the AS
    and only have custom paths if the user says so, or do we randomise the paths
    originally and only give specific paths if the user wants them... Hmmm
    """
    pass


def main():
    args = parse_args()
    print(
        "Welcome to our scalable and customizable simulator of AS routing using "
        "the BGP-4 protocol.\nThe current network topology is the following: \n"
        f"\t Number of AS's: {args.as_number}\n"
        f"\t Number of routers: {args.router_number}"
    )

    custom_paths = setup_router_paths(args.as_number, args.router_number)
    if not custom_paths:
        generate_routing_paths(args.as_number, args.router_number)
    else:
        generate_routing_paths(args.as_number, args.router_number, custom_paths)

    start_simulation()


if __name__ == "__main__":
    main()
