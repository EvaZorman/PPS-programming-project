"""
Handle the processing of the simulations after the environment
has been set up.
"""
import random
from collections import defaultdict
from pprint import pprint


def generate_routing_paths(as_num, network_data):
    """
    Randomly assign paths from one AS to another, expect if the user specified
    some routes. Then we respect those choices and randomly generate the rest.

    1. Randomly select number of paths an AS will have, based on
    num. of AS's - (1 + num. of already determined paths) = num. of paths

    2. for each path, randomly select an AS to connect to and set the path,
    as well as the path for the other AS

    3. ???

    4. profit $$$
    """
    # check if there are any user set paths we must respect
    if any(network_data["routers"]["paths"].values()):
        for router, paths in network_data["routers"]["paths"].items():
            this_router_as = [
                i
                for i in network_data["AS"]["AS_contained_routers"]
                if router in network_data["AS"]["AS_contained_routers"][i]
            ][0]

            for j in paths:
                path_router_as = [
                    i
                    for i in network_data["AS"]["AS_contained_routers"]
                    if j in network_data["AS"]["AS_contained_routers"][i]
                ][0]

                network_data["AS"]["paths"][this_router_as].add(path_router_as)
                network_data["AS"]["paths"][path_router_as].add(this_router_as)

    for i in range(as_num):
        # generate a list of possible choices for paths
        tmp_list = list(range(as_num))
        tmp_list.remove(i)

        # pick a random number of paths for the AS in question
        choice_range = as_num - (1 + len(network_data["AS"]["paths"][f"AS{i+1}"]))
        if choice_range < 2:
            continue
        num_of_paths = random.randrange(1, choice_range)

        # pick a random AS to path to
        for j in range(num_of_paths):
            rnd_path = random.choice(tmp_list)
            network_data["AS"]["paths"][f"AS{i+1}"].add(f"AS{rnd_path+1}")
            network_data["AS"]["paths"][f"AS{rnd_path+1}"].add(f"AS{i+1}")
            tmp_list.remove(rnd_path)

    pprint(network_data)


def print_path_table(net_dict):
    """
    Prints the data table for the custom paths
    """
    for key, item in list(net_dict["routers"]["paths"].items()):
        paths_str = f"{key}:\t{item}".expandtabs(8)
        print(paths_str)

    print()


def setup_as_routers(as_num, router_num):
    """
    Distributes the routers to the different AS's and polls the user for any specific
    routes they might wish for.
    """
    print(
        "By default, each AS will be connected to other random AS's.Hence the network \n"
        "topology will be different each simulation, unless configured otherwise.\n"
    )

    network_dict = {
        "AS": {
            "AS_contained_routers": defaultdict(list),
            "paths": defaultdict(set),
        },
        "routers": {"paths": {}},
    }

    # distribute the routers to their corresponding AS, based on simple modulo arithmetics
    for i in range(router_num):
        as_location = i % as_num
        network_dict["AS"]["AS_contained_routers"][f"AS{as_location+1}"].append(
            f"R{i+1}"
        )

        # create empty path sets for each router
        network_dict["routers"]["paths"][f"R{i+1}"] = []

    custom_paths = input(
        "Do you wish to set any specific routes for any of the routers that will be created? Y/N\n"
    ).replace(" ", "")
    if custom_paths.upper() == "N":
        return network_dict

    if custom_paths.upper() != "Y":
        print("Wrong answer :O Aborting...")
        return network_dict

    loop = True
    while loop:
        # Get the router to customise its path
        router_of_choice = (
            input(
                f"Which router's path would you like to customise?\n"
                f"Possible choices: {list(network_dict['routers']['paths'])}\n"
                "You can exit the customisation at any point by selecting Q.\n"
            )
            .upper()
            .replace(" ", "")
        )
        # exit or drop incorrect input
        if router_of_choice == "Q":
            loop = False
            continue

        if router_of_choice not in network_dict["routers"]["paths"]:
            print("Incorrect value chosen. Aborting customization...\n")
            continue

        choice_path = input(
            f"To which routers would you like your router to have a path?\n"
            f"Possible choices: {list(network_dict['routers']['paths'])}\n"
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
            for i in network_dict["AS"]["AS_contained_routers"]
            if router_of_choice in network_dict["AS"]["AS_contained_routers"][i]
        ]

        # if any element in paths is also in the AS of the chosen router, we have some
        # overlapping in paths that we do not want, skip the choice made
        if bool(
            set(paths) & set(network_dict["AS"]["AS_contained_routers"][router_as[0]])
        ):
            print("Incorrect value chosen. Aborting customization...\n")
            continue

        tmp_paths = set(network_dict["routers"]["paths"][router_of_choice])

        if set(paths).issubset(tmp_paths):
            print("Path(s) already contained. Aborting customization...\n")
            continue

        tmp_paths.update(set(paths))
        network_dict["routers"]["paths"][router_of_choice] = list(tmp_paths)

        print_path_table(network_dict)

    return network_dict


def start_simulation():
    """
    Handles the simulation process and the creation of necessary objects.
    """
