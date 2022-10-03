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

    2. For each path, randomly select an AS to connect to and set the path,
    as well as the path for the other AS.

    3. Based on the gained info, decide router paths as well.

    4. ???

    5. profit $$$
    """
    # check if there are any user set paths we must respect first
    if any(network_data["router_paths"].values()):
        for router, paths in network_data["router_paths"].items():
            this_router_as = [
                i
                for i in network_data["AS_contained_routers"]
                if router in network_data["AS_contained_routers"][i]
            ][0]

            for j in paths:
                path_router_as = [
                    i
                    for i in network_data["AS_contained_routers"]
                    if j in network_data["AS_contained_routers"][i]
                ][0]

                network_data["AS_paths"][this_router_as].add(path_router_as)
                network_data["AS_paths"][path_router_as].add(this_router_as)

    # generate a list of choices for AS paths
    for i in range(as_num):
        tmp_list = list(range(as_num))
        tmp_list.remove(i)

        # pick a random number of paths for the AS in question
        choice_range = as_num - (1 + len(network_data["AS_paths"][f"AS{i+1}"]))
        if choice_range < 2:
            continue
        num_of_paths = random.randrange(1, choice_range)

        # pick a random AS to path to
        for j in range(num_of_paths):
            rnd_path = random.choice(tmp_list)
            network_data["AS_paths"][f"AS{i+1}"].add(f"AS{rnd_path+1}")
            network_data["AS_paths"][f"AS{rnd_path+1}"].add(f"AS{i+1}")
            tmp_list.remove(rnd_path)

    # tmp data we will need to set the router paths
    tmp_data = {
        "counters": defaultdict(int),
        "viable_choices": defaultdict(list),
    }

    for i in range(as_num):
        tmp_data["counters"][f"AS{i+1}"] = 0
        tmp_data["viable_choices"][f"AS{i+1}"] = list(
            network_data["AS_paths"][f"AS{i+1}"]
        )

    for router, path in network_data["router_paths"].items():
        if path:
            """
            prob not what we want to do, since this will lead to errors
            in the algorithm. possible options i see are an additional loop
            to go over the already existing paths fist and set up the remainder
            of the choices for the algo to run, or some additional logic here
            that takes care of the pre-assigned routes... hmm
            """
            continue

        this_router_as = [
            i
            for i in network_data["AS_contained_routers"]
            if router in network_data["AS_contained_routers"][i]
        ][0]

        # look into the tmp data, which AS needs to still be connected
        # and clean up the tmp list to keep track of what is left still
        as_choice = tmp_data["viable_choices"][this_router_as][0]
        tmp_data["viable_choices"][this_router_as].remove(as_choice)
        tmp_data["viable_choices"][as_choice].remove(this_router_as)

        # calculate the counter value and then increase it
        as_count = tmp_data["counters"][as_choice] % len(
            network_data["AS_contained_routers"][as_choice]
        )
        # this is bad bad bad, can lead to int overflow,
        # but I'm too lazy to make it properly rn
        tmp_data["counters"][as_choice] += 1

        # add the chosen router into the list, and add this router to
        # the chosen one's
        router_choice = network_data["AS_contained_routers"][as_choice][as_count]
        path.add(router_choice)
        network_data["router_paths"][router_choice].add(router)

        print(
            f"{router} router, AS it belongs to is {this_router_as}, "
            f"existing paths are {path}"
        )

        pprint(tmp_data)
        pprint(network_data["router_paths"])

    pprint(network_data)


def print_path_table(net_dict):
    """
    Prints the data table for the custom paths
    """
    for key, item in list(net_dict["router_paths"].items()):
        if item:
            paths_str = f"{key}:\t{item}".expandtabs(8)
        else:
            paths_str = f"{key}:\tNone".expandtabs(8)
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
        "AS_contained_routers": defaultdict(list),
        "AS_paths": defaultdict(set),
        "router_paths": {},
    }

    # distribute the routers to their corresponding AS, based on simple modulo arithmetics
    for i in range(router_num):
        as_location = i % as_num

        network_dict["AS_contained_routers"][f"AS{as_location+1}"].append(f"R{i+1}")
        network_dict["router_paths"][f"R{i+1}"] = set()

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
                f"Possible choices: {list(network_dict['router_paths'])}\n"
                "You can exit the customisation at any point by selecting Q.\n"
            )
            .upper()
            .replace(" ", "")
        )
        # exit or drop incorrect input
        if router_of_choice == "Q":
            loop = False
            continue

        if router_of_choice not in network_dict["router_paths"]:
            print("Incorrect value chosen. Aborting customization...\n")
            continue

        tmp_choice_list = list(network_dict["router_paths"])
        tmp_choice_list.remove(router_of_choice)
        choice_path = input(
            f"To which routers would you like your router to have a path?\n"
            f"Possible choices: {tmp_choice_list}\n"
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
            for i in network_dict["AS_contained_routers"]
            if router_of_choice in network_dict["AS_contained_routers"][i]
        ][0]

        # if any element in paths is also in the AS of the chosen router, we have some
        # overlapping in paths that we do not want, skip the choice made
        if bool(set(paths) & set(network_dict["AS_contained_routers"][router_as])):
            print("Incorrect value chosen. Aborting customization...\n")
            continue

        # if paths.issubset(tmp_paths):
        #     print("Path(s) already contained. Aborting customization...\n")
        #     continue
        for item in paths:
            network_dict["router_paths"][item].add(router_of_choice)

        network_dict["router_paths"][router_of_choice].update(set(paths))
        print_path_table(network_dict)

    return network_dict


def start_simulation():
    """
    Handles the simulation process and the creation of necessary objects.
    """
