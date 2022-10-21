"""
Handle the processing of the simulations after the environment
has been set up.
"""
import random
import sys
from collections import defaultdict
from pprint import pprint
from threading import Thread

from router import Router


def generate_routing_paths(as_num, as_paths):
    """
    Randomly assign paths from one AS to another, except if the user specified
    some routes. Then we respect those choices and randomly generate the rest.

    1. Randomly select number of paths an AS will have, based on
    num. of AS's - (1 + num. of already determined paths) = num. of paths

    2. For each path, randomly select an AS to connect to and set the path,
    as well as the path for the other AS.

    3. ???

    4. profit $$$
    """
    # generate a list of choices for AS paths
    for i in range(as_num):
        tmp_list = list(range(as_num))
        tmp_list.remove(i)

        # pick a random number of paths for the AS in question
        choice_range = int(as_num / 3) - 1 + len(as_paths[f"AS{i+1}"])
        if choice_range < 2:
            continue
        num_of_paths = random.randrange(1, choice_range)

        # pick a random AS to path to
        for _ in range(num_of_paths):
            rnd_path = random.choice(tmp_list)
            as_paths[f"AS{i+1}"].add(f"AS{rnd_path+1}")
            as_paths[f"AS{rnd_path+1}"].add(f"AS{i+1}")
            tmp_list.remove(rnd_path)

    return as_paths


def print_path_table(as_dict):
    """
    Prints the data table for the custom paths
    """
    for key, item in as_dict.items():
        if item:
            paths_str = f"{key}:\t{item}".expandtabs(8)
        else:
            paths_str = f"{key}:\tNone".expandtabs(8)
        print(paths_str)

    print()


def setup_as(as_num):
    """
    Polls the user for any specific routes they might wish for.
    """
    print(
        "By default, each AS will be connected to other random AS's.Hence the network \n"
        "topology will be different each simulation, unless configured otherwise.\n"
    )

    as_paths = defaultdict()

    for i in range(as_num):
        as_paths[f"AS{i+1}"] = set()

    custom_paths = input(
        "Do you wish to set any specific routes for any of the AS's that will be created? Y/N\n"
    ).replace(" ", "")
    if custom_paths.upper() == "N":
        return as_paths

    if custom_paths.upper() != "Y":
        print("Wrong answer :O Aborting...")
        return as_paths

    loop = True
    while loop:
        # Get the AS to customise its path
        as_of_choice = (
            input(
                f"Which AS's path would you like to customise?\n"
                f"Possible choices: {list(as_paths)}\n"
                "You can exit the customisation at any point by selecting Q.\n"
            )
            .upper()
            .replace(" ", "")
        )

        # exit or drop incorrect input
        if as_of_choice == "Q":
            loop = False
            continue

        if as_of_choice not in as_paths:
            print("Incorrect value chosen. Aborting customization...\n")
            continue

        tmp_choice_list = list(as_paths)
        tmp_choice_list.remove(as_of_choice)
        choice_path = input(
            f"To which AS would you like to have a path to?\n"
            f"Possible choices: {tmp_choice_list}\n"
            "You can also set a list of AS's you wish to add, e.g. <as1 as2 as4>.\n"
            "You can exit the customisation at any point by selecting Q.\n"
        ).upper()

        paths = choice_path.split(" ")

        if "Q" in paths:
            loop = False
            continue

        for item in paths:
            if item not in as_paths:
                continue

            as_paths[item].add(as_of_choice)
            as_paths[as_of_choice].update(set(paths))

        print_path_table(as_paths)

    return as_paths


def setup_simulation(routes):
    """
    Handles the simulation process and the creation of necessary objects.
    """
    pprint(routes)
    router_list = []

    for as_choice, paths in routes.items():
        router_num = as_choice.strip("AS")
        router_list.append(
            Router(f"R{router_num}", f"100.{router_num}.0.1", int(router_num), paths)
        )

    # start the control and data plane listener that will run as long as the
    # main program is running, unless if we explicitly end them
    listener_threads = start_listeners(router_list)

    # setup the TCP connections for each router based on their routes
    router_paths = list(routes.values())
    for router in router_list:
        router.initiate_connections(router_paths[router_list.index(router)])

    print("here we are")

    stop_listeners(task_list=listener_threads, router_list=router_list)
    sys.exit()


def start_listeners(router_list):
    """
    Starts BGP listeners in the background by multi-threading.
    """
    thread_list = []
    for r in router_list:
        t = Thread(target=r.start)
        thread_list.append(t)
        t.daemon = True
        t.start()

    return thread_list


def stop_listeners(task_list, router_list):
    """
    Stops BGP listeners and the background threads.
    """
    for router in router_list:
        router.stop()

    for t in task_list:
        t.join(2)


def start_speakers():
    pass
