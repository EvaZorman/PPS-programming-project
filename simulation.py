"""
Handle the processing of the simulations after the environment
has been set up.
"""
import logging
import random
import sys
from collections import defaultdict
from pprint import pprint
from threading import Thread
from time import sleep

from ip_packet import IPPacket
from messages import BGPMessage
from router import Router, s_print

logger = logging.getLogger("BGP")


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
            as_paths[f"AS{i+1}"].add(rnd_path + 1)
            as_paths[f"AS{rnd_path+1}"].add(i + 1)
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
        print("Wrong input. Aborting...")
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

            as_paths[item].add(int(as_of_choice.strip("AS")))
            as_paths[as_of_choice].update(
                set([int(path.strip("AS")) for path in paths])
            )

        print_path_table(as_paths)

    return as_paths


def user_customisations(router_dict, router_paths):
    """
    Polls the user for any specific table changes they might want.
    """
    customisation_loop = True
    help_message = (
        "\nTo see the constructed routing tables, write p <AS number>\n"
        "To advertise a specific IP prefix, write a <AS number>\n"
        "To customise a table of a specific router, write c <AS number>\n"
        "To remove a specific table entry, write d <AS number>\n"
        "To craft an IP packet and send it to an initial router, write ip <AS number>\n"
        "To have the commands printed again, write h\n"
        "To exit the customisation, write q"
    )
    print(help_message)

    while customisation_loop:
        action = input().upper()
        action_list = action.split()

        if "H" in action_list:
            print(help_message)
            continue

        if "Q" in action_list:
            customisation_loop = False
            continue

        if len(action_list) != 2:
            print("Badly formed input. Aborting...")
            continue

        if "P" in action_list:
            # print the routing table for router X
            try:
                router_num = int(action_list[1])
                if router_num < 1 or router_num > len(router_dict.keys()):
                    print("Invalid AS number")
                    continue

                router_dict[str(router_num)].print_routing_table()
            except ValueError:
                print("AS number not valid. Aborting...")
            continue

        if "A" in action_list:
            # print the routing table for router X
            try:
                router_num = int(action_list[1])
                if router_num < 1 or router_num > len(router_dict.keys()):
                    s_print("Invalid AS number")
                    continue

                custom_prefix = (
                    input(
                        f"If you wish to create a custom IP prefix path to advertise, "
                        f"pass it as a list of attributes of <Network, MED, "
                        f"Loc_Pref, Weight, Trust_Rate>\n"
                    )
                    .replace(" ", "")
                    .split(",")
                )

                if len(custom_prefix) == 5:
                    ip_prefix = [custom_prefix[0]]
                    path_attr = {
                        "ORIGIN": router_num,
                        "NEXT_HOP": router_dict[str(router_num)].ip,
                        "MED": custom_prefix[1],
                        "LOC_PREF": custom_prefix[2],
                        "WEIGHT": custom_prefix[3],
                        "TRUST_RATE": custom_prefix[4],
                        "AS_PATH": str(router_num),
                    }
                    router_dict[str(router_num)].add_advertised_ip_prefix(ip_prefix)
                    router_dict[str(router_num)].advertise_ip_prefix(
                        path_attr, ip_prefix
                    )
            except ValueError:
                print("AS number not valid. Aborting...")

        if "C" in action.split():
            # print and customise the routing table for router X
            try:
                router_num = int(action_list[1])
                if router_num < 1 or router_num > len(router_dict.keys()):
                    print("Invalid AS number")
                    continue

                router = router_dict[str(router_num)]
                router.print_routing_table()
                row = int(input("Which row would you like to customise?"))
                if row < 0 or row > router.get_routing_table_size():
                    print("Incorrect row value chosen. Aborting...")
                    continue

                choices = ["med", "locpref", "weight", "trustrate"]
                choice_value = input(
                    f"The possible choices are: {choices}.\nPick which value to change. "
                    f"You can only state the initial letter.\n"
                ).split()
                if len(choice_value) != 1 or set(choice_value).issubset(set(choices)):
                    print("Incorrect value choice. Aborting...")
                    continue

                actual_value = input("\nWhat would you like your new value to be?\n")
                router.customise_routing_table(row, choice_value, actual_value)
            except ValueError:
                print("AS number not valid. Aborting...")
            continue

        if "D" in action.split():
            # print and customise the routing table for router X
            try:
                router_num = int(action_list[1])
                if router_num < 1 or router_num > len(router_dict.keys()):
                    print("Invalid AS number")
                    continue

                router = router_dict[str(router_num)]
                router.print_routing_table()
                row = int(input("Which row would you like to delete?"))
                if row < 0 or row > router.get_routing_table_size():
                    print("Incorrect row value chosen. Aborting...")
                    continue

                router.remove_table_entry(row)
            except ValueError:
                print("AS number not valid. Aborting...")
            continue

        if "IP" in action.split():
            # craft an IP packet and send it to initial chosen router
            try:
                router_num = int(action_list[1])
                if router_num < 1 or router_num > len(router_dict.keys()):
                    print("Invalid AS number")
                    continue

                router = router_dict[str(router_num)]

                ip_data = (
                    input(
                        f"If you wish to create a custom IP packet, pass a list of attributes of <Source addr.,"
                        f" Destination addr., Payload>\n"
                    )
                    .replace(" ", "")
                    .split(",")
                )

                ip_packet = IPPacket(24, 5, 60, ip_data[0], ip_data[1], ip_data[2])
                router.data_send(router_num, ip_packet)
            except ValueError:
                print("AS number not valid. Aborting...")
            continue


def setup_simulation(routes):
    """
    Handles the simulation process and the creation of necessary objects.
    """
    router_dict = {}

    s_print(f"Generated network topology for the simulation:")
    pprint(routes)

    for as_choice, paths in routes.items():
        router_num = as_choice.strip("AS")
        router_dict[router_num] = Router(
            router_num, f"50.{router_num}.0.1", int(router_num), paths
        )

    # start the control and data plane listener that will run as long as the
    # main program is running, unless if we explicitly end them
    s_print("Starting listener threads...")
    listener_threads = start_listeners(router_dict)

    # Set up the TCP connections for each router based on their routes
    s_print("Setting up TCP connections and pushing routers into Established mode...")
    router_paths = {name.strip("AS"): paths for name, paths in routes.items()}
    for r_name, r_obj in router_dict.items():
        # sets up the initial connection and does all the necessary BGP exchanges to
        # make sure the routers are in Established mode
        for peer in router_paths[r_name]:
            logger.info(f"Setting up TCP connection with router {peer}...")
            r_obj.bgp_send(peer, BGPMessage(r_obj.name))

    # Waiting for all the BGP setup to complete
    while not all([r_obj.bgp_setup_complete for r_obj in router_dict.values()]):
        sleep(1)

    # We now generate the initial trust and voting values for our neighbours
    # and add them into their respective tables
    s_print(f"Starting the initial trust and voting process for all nodes...")
    for r_name, r_obj in router_dict.items():
        r_obj.setup_complete = False
        logger.info(f"Router {r_name} is starting the voting procedures...")
        r_obj.start_voting(router_paths[r_name])

    # Waiting for all the voting setup to complete
    while not all([r_obj.voting_setup_complete for r_obj in router_dict.values()]):
        sleep(1)

    # so now we have working routers that have all their dedicated routes connected
    # and are in Established state within the BGP protocol. We now want to have each
    # AS and router have their own ip prefix to which their packets will go. The IP
    # prefixes will be set to a 100.<as number>.0.0/16 prefix by default.
    #
    # If a user wants to add additional prefixes to a router, enable them to do so
    # after we've set up the default state
    s_print(f"Starting advertising default IP prefixes...")
    for r_name, r_obj in router_dict.items():
        ip_prefix = [f"100.{r_name}.{r_name}.0/24"]
        path_attr = {
            "ORIGIN": r_name,
            "NEXT_HOP": r_obj.ip,
            "MED": 0,
            "LOC_PREF": 0,
            "WEIGHT": 0,
            "TRUST_RATE": 0,
            "AS_PATH": r_name,
        }
        r_obj.add_advertised_ip_prefix(ip_prefix)
        logger.info(f"Router {r_name} advertising IP prefix of: {ip_prefix}")
        r_obj.advertise_ip_prefix(path_attr, ip_prefix)

    # time for us to do the rest of the trust distribution!
    # s_print(f"Starting to distribute TRUST_RATE messages between all nodes...")
    # for r_name, r_obj in router_dict.items():
    #     logger.info(
    #         f"Router {r_name} is distributing its own trust rates of neighbours..."
    #     )
    #     r_obj.distribute_trust_values(router_paths[r_name])

    # Waiting for all the UPDATE setup to complete
    while not all([r_obj.advertise_setup_complete for r_obj in router_dict.values()]):
        sleep(1)

    # any user customisation is possible here
    user_customisations(router_dict, router_paths)
    sys.exit()


def start_listeners(router_list):
    """
    Starts BGP listeners in the background by multi-threading.
    """
    thread_list = []
    for r_name, r_obj in router_list.items():
        t = Thread(target=r_obj.start)
        thread_list.append(t)
        t.daemon = True
        t.start()

    return thread_list


def stop_listeners(task_list, router_list):
    """
    Stops BGP listeners and the background threads.
    """
    for r_name, r_obj in router_list.values:
        r_obj.stop()

    for t in task_list:
        t.join(2)


def start_speakers():
    pass
