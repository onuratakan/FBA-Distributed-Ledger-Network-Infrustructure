#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import urllib.request, json
import time
import argparse
import sys


class Decentra_Network_Local:

    def __init__(self, number_of_nodes = 3):
        self.number_of_nodes = number_of_nodes - 1
        time.sleep(1)
        self.creating_the_wallets()
        self.starting_the_nodest()
        self.unl_nodes_settting()
        self.connecting_the_nodes()
        self.creating_the_block()
        time.sleep(15)

    def creating_the_wallets(self):

        create_wallet_1 = json.loads(urllib.request.urlopen("http://localhost:8000/wallet/create/123").read().decode())
        for i in range(self.number_of_nodes):
            create_wallet_2 = json.loads(urllib.request.urlopen(f"http://localhost:80{i+1}0/wallet/create/123").read().decode())

    def starting_the_nodest(self):

        node_start_1 = json.loads(urllib.request.urlopen("http://localhost:8000/node/start/0.0.0.0/7999").read().decode())
        for i in range(self.number_of_nodes):
            node_start_2 = json.loads(urllib.request.urlopen(f"http://localhost:80{i+1}0/node/start/0.0.0.0/800{i+1}").read().decode())

    def unl_nodes_settting(self):

        node_id_1 = json.loads(urllib.request.urlopen("http://localhost:8000/node/id").read().decode())
        for i in range(self.number_of_nodes):
            urllib.request.urlopen(f"http://localhost:80{i+1}0/node/newunl/?{node_id_1}")
        
        for i in range(self.number_of_nodes):
            node_id_2 = json.loads(urllib.request.urlopen(f"http://localhost:80{i+1}0/node/id").read().decode())
            urllib.request.urlopen(f"http://localhost:8000/node/newunl/?{node_id_2}")
            for i_n in range(self.number_of_nodes):
                if not i == i_n:
                    urllib.request.urlopen(f"http://localhost:80{i_n+1}0/node/newunl/?{node_id_2}")

    def connecting_the_nodes(self):

        for i in range(self.number_of_nodes):
            urllib.request.urlopen(f"http://localhost:8000/node/connect/0.0.0.0/800{i+1}")
        
        for i in range(self.number_of_nodes):
            for i_n in range(self.number_of_nodes):
                if not i == i_n:
                    urllib.request.urlopen(f"http://localhost:80{i+1}0/node/connect/localhost/800{i_n+1}")
                    time.sleep(1)

    def creating_the_block(self):

        urllib.request.urlopen("http://localhost:8000/settings/test/on")
        urllib.request.urlopen("http://localhost:8000/settings/debug/on")
        for i in range(self.number_of_nodes):
            urllib.request.urlopen(f"http://localhost:80{i+1}0/settings/debug/on")
        urllib.request.urlopen("http://localhost:8000/block/get")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="This is an open source decentralized application network. In this network, you can develop and publish decentralized applications.")


    parser.add_argument('-nn', '--nodenumber', type=int,
                        help='Change Wallet')

    
    args = parser.parse_args()


    if len(sys.argv) < 2:
        parser.print_help()

    if not args.nodenumber is None:
        Decentra_Network_Local(args.nodenumber)
