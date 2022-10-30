"""
Handle the processing of the simulations after the environment
has been set up.
"""
import random
from collections import defaultdict
from pprint import pprint
from threading import Thread
from time import sleep

from messages import BGPMessage, VotingMessage
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


def user_customisations(router_dict, router_paths):
    """
    Polls the user for any specific table changes they might want.
    """
    # for router in router_list:
    #     # advertise default prefixes
    #     ip_prefix = [f"100.{router.name}.{router.name}.0/24"]
    #     path_attr = {
    #         "ORIGIN": router.name,
    #         "NEXT_HOP": router.ip,
    #         "MED": None,
    #         "LOCAL_PREF": None,
    #         "WEIGHT": None,
    #         "AS_PATH": str(router.name),
    #     }
    #     router.advertise_ip_prefix(path_attr, ip_prefix)

    customisation_loop = True
    help_message = (
        "To see the constructed routing tables, write p <AS number>\n"
        "To advertise a specific IP prefix, write a <AS number>\n"
        "To customise a table of a specific router, write c <AS number>\n"
        "To start voting for a specific router, write v <AS number>\n"
        "To have the commands printed again, write h\n"
        "To exit the customisation, write q"
    )
    print(help_message)

    while customisation_loop:
        action = input().upper()
        action_list = action.split()

        if len(action_list) != 2:
            print("Badly formed input. Aborting...")
            continue

        if "Q" in action_list:
            customisation_loop = False
            continue

        if "H" in action_list:
            print(help_message)
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

        if "V" in action_list:
            # starts the voting process for router X
            try:
                router_num = int(action_list[1])
                if router_num < 1 or router_num > len(router_dict.keys()):
                    print("Invalid AS number")
                    continue

                router_dict[str(router_num)].start_voting(router_paths[str(router_num)])
            except ValueError:
                print("AS number not valid. Aborting...")
            continue

        if "A" in action_list:
            # print the routing table for router X
            try:
                router_num = int(action_list[1])
                if router_num < 1 or router_num > len(router_dict.keys()):
                    print("Invalid AS number")
                    continue

                custom_prefix = input(f"If you wish to create a custom IP prefix path to advertise, "
                                      f"pass it as a list of attributes of <Network, MED, "
                                      f"Loc_Pref, Weight>\n").replace(" ", "").split(",")

                if len(custom_prefix) == 4:
                    ip_prefix = [custom_prefix[0]]
                    path_attr = {
                        "ORIGIN": router_num,
                        "NEXT_HOP": router_dict[str(router_num)].ip,
                        "MED": custom_prefix[1],
                        "LOCAL_PREF": custom_prefix[2],
                        "WEIGHT": custom_prefix[3],
                        "AS_PATH": str(router_num),
                    }
                    router_dict[str(router_num)].advertise_ip_prefix(path_attr, ip_prefix)
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
                choice_value = input(f"The possible choices are: {choices}. Pick which value to change. "
                              f"You can only state the initial letter.").split()
                if len(choice_value) != 1 or set(choice_value).issubset(set(choices)):
                    print("Incorrect value choice. Aborting...")
                    continue

                actual_value = input("What would you like your new value to be?")
                router.update_voting_value(row, choice_value, actual_value)
            except ValueError:
                print("AS number not valid. Aborting...")
            continue
    return


def setup_simulation(routes):
    """
    Handles the simulation process and the creation of necessary objects.
    """
    router_dict = {}

    pprint(routes)

    for as_choice, paths in routes.items():
        router_num = as_choice.strip("AS")
        router_dict[router_num] = Router(router_num, f"50.{router_num}.0.1", int(router_num), paths)

    # start the control and data plane listener that will run as long as the
    # main program is running, unless if we explicitly end them
    listener_threads = start_listeners(router_dict)

    # setup the TCP connections for each router based on their routes
    router_paths = {
            name.strip("AS"): paths
            for name, paths in routes.items()
        }
    for r_name, r_obj in router_dict.items():
        # sets up the initial connection and does all the necessary BGP exchanges to
        # make sure the routers are in Established mode
        for peer in router_paths[r_name]:
            r_obj.bgp_send(peer, BGPMessage(r_obj.name))

    # Waiting for all the BGP setup to complete
    for r_name, r_obj in router_dict.items():
        while not r_obj.setup_complete:
            sleep(1)

    # so now we have working routers that have all their dedicated routes connected
    # and are in Established state within the BGP protocol. We now want to have each
    # AS and router have their own ip prefix to which their packets will go. The IP
    # prefixes will be set to a 100.<as number>.0.0/16 prefix by default.
    #
    # If a user wants to add additional prefixes to a router, enable them to do so
    # after we've set up the default state
    for r_name, r_obj in router_dict.items():
        ip_prefix = [f"100.{r_name}.{r_name}.0/24"]
        path_attr = {
            "ORIGIN": r_name,
            "NEXT_HOP": r_obj.ip,
            "MED": None,
            "LOCAL_PREF": None,
            "WEIGHT": None,
            "AS_PATH": r_name,
        }
        r_obj.advertise_ip_prefix(path_attr, ip_prefix)
        sleep(10)

    user_customisations(router_dict, router_paths)

    """
    TODO:
        - timers need to be added, or we can maybe use the scheduler
        - create an ip packet and send it!
        
    Optional:
        - see if we can simulate errors like shutting down a router etc.
    """

    sleep(5)
    # stop_listeners(task_list=listener_threads, router_list=router_list)
    # sys.exit()


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
