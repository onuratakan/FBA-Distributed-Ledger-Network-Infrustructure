#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import contextlib
import copy
import json
import os
import random
import socket
import time
from hashlib import sha256
from shutil import move
from threading import Thread

from naruno.accounts.save_accounts import accounts_db
from naruno.blockchain.block.block_main import Block
from naruno.blockchain.block.blocks_hash import blockshash_db
from naruno.blockchain.block.change_transaction_fee import ChangeTransactionFee
from naruno.blockchain.block.get_block import GetBlock
from naruno.blockchain.block.save_block import SaveBlock
from naruno.config import CONNECTED_NODES_PATH
from naruno.config import LOADING_ACCOUNTS_PATH
from naruno.config import LOADING_BLOCK_PATH
from naruno.config import LOADING_BLOCKSHASH_PART_PATH
from naruno.config import LOADING_BLOCKSHASH_PATH
from naruno.config import PENDING_TRANSACTIONS_PATH
from naruno.config import TEMP_ACCOUNTS_PATH
from naruno.config import TEMP_BLOCK_PATH
from naruno.config import TEMP_BLOCKSHASH_PART_PATH
from naruno.config import TEMP_BLOCKSHASH_PATH
from naruno.lib.config_system import get_config
from naruno.lib.kot import KOT
from naruno.lib.log import get_logger
from naruno.node.client.client import client
from naruno.node.unl import Unl
from naruno.transactions.get_transaction import GetTransaction
from naruno.transactions.transaction import Transaction
from naruno.wallet.ellipticcurve.ecdsa import Ecdsa
from naruno.wallet.ellipticcurve.privateKey import PrivateKey
from naruno.wallet.ellipticcurve.publicKey import PublicKey
from naruno.wallet.ellipticcurve.signature import Signature
from naruno.wallet.wallet_import import wallet_import

from naruno.node.get_candidate_blocks import self_candidates

connectednodes_db = KOT("connectednodes",
                        folder=get_config()["main_folder"] + "/db")

a_block = Block("onur")
buffer_size = 6525 + int(
    (a_block.max_data_size // a_block.max_tx_number) * 1.5)


class server(Thread):
    Server = None
    id = wallet_import(0, 0)

    def __init__(
        self,
        host,
        port,
        save_messages=False,
        test=False,
        custom_variables=False,
        custom_TEMP_BLOCK_PATH=None,
        custom_TEMP_ACCOUNTS_PATH=None,
        custom_TEMP_BLOCKSHASH_PATH=None,
        custom_TEMP_BLOCKSHASH_PART_PATH=None,
        custom_LOADING_BLOCK_PATH=None,
        custom_LOADING_ACCOUNTS_PATH=None,
        custom_LOADING_BLOCKSHASH_PATH=None,
        custom_LOADING_BLOCKSHASH_PART_PATH=None,
        custom_CONNECTED_NODES_PATH=None,
        custom_PENDING_TRANSACTIONS_PATH=None,
        time_control=None,
        custom_id=None,
    ):
        Thread.__init__(self)
        self.running = True

        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)

        self.clients = []
        self.sync_clients = []

        self.messages = []
        self.our_messages = []
        self.save_messages = save_messages

        self.TEMP_BLOCK_PATH = (TEMP_BLOCK_PATH if custom_TEMP_BLOCK_PATH
                                is None else custom_TEMP_BLOCK_PATH)
        self.TEMP_ACCOUNTS_PATH = (TEMP_ACCOUNTS_PATH
                                   if custom_TEMP_ACCOUNTS_PATH is None else
                                   custom_TEMP_ACCOUNTS_PATH)
        self.TEMP_BLOCKSHASH_PATH = (TEMP_BLOCKSHASH_PATH
                                     if custom_TEMP_BLOCKSHASH_PATH is None
                                     else custom_TEMP_BLOCKSHASH_PATH)
        self.TEMP_BLOCKSHASH_PART_PATH = (
            TEMP_BLOCKSHASH_PART_PATH if custom_TEMP_BLOCKSHASH_PART_PATH
            is None else custom_TEMP_BLOCKSHASH_PART_PATH)
        self.LOADING_BLOCK_PATH = (LOADING_BLOCK_PATH
                                   if custom_LOADING_BLOCK_PATH is None else
                                   custom_LOADING_BLOCK_PATH)
        self.LOADING_ACCOUNTS_PATH = (LOADING_ACCOUNTS_PATH
                                      if custom_LOADING_ACCOUNTS_PATH is None
                                      else custom_LOADING_ACCOUNTS_PATH)
        self.LOADING_BLOCKSHASH_PATH = (LOADING_BLOCKSHASH_PATH if
                                        custom_LOADING_BLOCKSHASH_PATH is None
                                        else custom_LOADING_BLOCKSHASH_PATH)
        self.LOADING_BLOCKSHASH_PART_PATH = (
            LOADING_BLOCKSHASH_PART_PATH if custom_LOADING_BLOCKSHASH_PART_PATH
            is None else custom_LOADING_BLOCKSHASH_PART_PATH)

        self.CONNECTED_NODES_PATH = (None if custom_CONNECTED_NODES_PATH
                                     is None else custom_CONNECTED_NODES_PATH)

        self.PENDING_TRANSACTIONS_PATH = (
            PENDING_TRANSACTIONS_PATH if custom_PENDING_TRANSACTIONS_PATH
            is None else custom_PENDING_TRANSACTIONS_PATH)

        self.custom_variables = custom_variables

        self.time_control = 10 if time_control is None else time_control

        if custom_id is not None:
            self.id = custom_id
        else:
            self.id = server.id

        self.logger = get_logger(f"NODE_{self.host}_{self.port}")

        self.logger.info(f"Server started as {server.id}")

        self.logger.debug("Save messages: " + str(save_messages))
        self.logger.debug("Test mode: " + str(test))


        self.send_busy = []

        if not test:
            self.__class__.Server = self
            self.start()

    def check_connected(self, host, port):
        for a_client in self.clients:
            if a_client.host == host and a_client.port == port:
                return True

        return False

    def run(self):
        self.logger.info("Server ear started")
        self.sock.settimeout(10.0)
        while self.running:
            with contextlib.suppress(socket.timeout):
                conn, addr = self.sock.accept()
                self.logger.debug(f"New connection request: {addr}")
                data = conn.recv(1024)
                conn.send(self.id.encode("utf-8"))
                client_id = data.decode("utf-8")
                self.logger.debug(f"New connection id: {client_id}")
                if Unl.node_is_unl(client_id):
                    self.logger.info(f"Confirmed")
                    self.clients.append(client(conn, addr, client_id, self))
                    self.save_connected_node(addr[0], addr[1], client_id)
                else:
                    self.logger.warning(f"Rejected")
            time.sleep(0.01)

    def stop(self):
        self.running = False
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
            (self.host, self.port))
        for c in self.clients:
            c.stop()
        time.sleep(1)
        for c in self.clients:
            c.join()
        self.sock.close()

    def prepare_message(self, data):
        data["id"] = server.id
        data["timestamp"] = str(time.time())
        sign = Ecdsa.sign(
            str(data),
            PrivateKey.fromPem(wallet_import(0, 1)),
        ).toBase64()

        data["signature"] = sign
        return data

    def send(self, data, except_client=None):
        data = self.prepare_message(data)

        for a_client in self.clients:
            if a_client != except_client:
                self.send_client(a_client, data, ready_to_send=True)
        try:
            del data["buffer"]
        except KeyError:
            pass
        return data

    def send_client(self, node, data, ready_to_send=False):
        self.logger.debug(
            f"Sending message: {data} to {node.host}:{node.port}={node.id}")
        if not ready_to_send:
            data = self.prepare_message(data)
        if len(json.dumps(data).encode("utf-8")) < buffer_size:
            data["buffer"] = "0" * (
                (buffer_size - len(json.dumps(data).encode("utf-8"))) - 1
        while node.id in self.send_busy:
            time.sleep(0.01)
        self.send_busy.append(node.id)
        with contextlib.suppress(socket.timeout):
            node.socket.sendall(json.dumps(data).encode("utf-8"))
        self.send_busy.remove(node.id)
        with contextlib.suppress(KeyError):
            del data["buffer"]
        time.sleep(0.02)
        if self.save_messages:
            self.our_messages.append(data)
        return data

    def get_message(self, client, data, hash_of_data=""):
        self.logger.info(
            f"Starting to proccess the message ({hash_of_data}) of {client.id}:{client.host}:{client.port}"
        )
        if self.check_message(data):
            self.logger.debug(f"Message is valid")
            if self.save_messages:
                self.messages.append(data)
            self.direct_message(client, data, hash_of_data)
        else:
            self.logger.error(f"Message is not in a valid format")

    def check_message(self, data):
        if "id" not in data:
            self.logger.error("No id")
            return False
        if "signature" not in data:
            self.logger.error("No signature")
            return False
        if "timestamp" not in data:
            self.logger.error("No timestamp")
            return False
        # the_control = time.time() - float(data["timestamp"])
        # if the_control > self.time_control:
        #    logger.debug("Time control is not true")
        #    return False
        # remove sign from data
        sign = data["signature"]
        del data["signature"]
        message = str(data)
        data["signature"] = sign

        signature_verify = Ecdsa.verify(
            message,
            Signature.fromBase64(sign),
            PublicKey.fromPem(data["id"]),
        )

        if not signature_verify:
            self.logger.error("Signature not valid")
            return False

        return True

    def connect(self, host, port):
        self.logger.info(f"Asking for new node on {host}:{port}")
        connected = self.check_connected(host=host, port=port)
        if not connected:
            self.logger.info(
                "New connection request confirmed trying to connect")
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(10.0)
            addr = (host, port)
            conn.connect(addr)
            conn.send(server.id.encode("utf-8"))
            try:
                client_id = conn.recv(1024).decode("utf-8")
                if Unl.node_is_unl(client_id):
                    self.logger.info(
                        f"Succesfully connected to {client_id} on {host}:{port}"
                    )
                    self.clients.append(client(conn, addr, client_id, self))
                    self.save_connected_node(addr[0], addr[1], client_id)
                    return True
            except socket.timeout:
                self.logger.warning(f"Connection timeout")
                conn.close()
        else:
            self.logger.warning("Already connected")

    @staticmethod
    def get_connected_nodes(custom_CONNECTED_NODES_PATH=None):
        """
        Returns the connected nodes.
        """

        the_pending_list = {}
        all_records = (connectednodes_db.get_all()
                       if custom_CONNECTED_NODES_PATH is None else KOT(
                           "connectednodes" + custom_CONNECTED_NODES_PATH,
                           folder=get_config()["main_folder"] + "/db",
                       ).get_all())
        for entry in all_records:
            loaded_json = all_records[entry]
            the_pending_list[loaded_json["host"] + str(loaded_json["port"]) +
                             loaded_json["id"]] = loaded_json

        return the_pending_list

    def save_connected_node(self, host, port, node_id):
        """
        Saves the connected nodes.
        """

        node_list = {}
        node_list["id"] = node_id
        node_list["host"] = host
        node_list["port"] = port

        node_id = sha256(
            (node_id + host + str(port)).encode("utf-8")).hexdigest()

        connectednodes_db.set(
            node_id, node_list) if self.CONNECTED_NODES_PATH is None else KOT(
                "connectednodes" + self.CONNECTED_NODES_PATH,
                folder=get_config()["main_folder"] + "/db",
            ).set(node_id, node_list)

    @staticmethod
    def connectionfrommixdb(custom_server=None,
                            custom_CONNECTED_NODES_PATH=None):
        """
        Connects to the mixdb.
        """
        the_server = server.Server if custom_server is None else custom_server
        the_CONNECTED_NODES_PATH = (the_server.CONNECTED_NODES_PATH
                                    if custom_CONNECTED_NODES_PATH is None else
                                    custom_CONNECTED_NODES_PATH)
        node_list = the_server.get_connected_nodes(
            custom_CONNECTED_NODES_PATH=the_CONNECTED_NODES_PATH)
        for element in node_list:
            with contextlib.suppress(Exception):
                the_server.connect(
                    node_list[element]["host"],
                    node_list[element]["port"],
                )

    def connected_node_delete(self, node):
        """
        Deletes a connected node.
        """

        node_id = sha256((node["id"] + node["host"] +
                          str(node["port"])).encode("utf-8")).hexdigest()
        connectednodes_db.delete(
            node_id) if self.CONNECTED_NODES_PATH is None else KOT(
                "connectednodes" + self.CONNECTED_NODES_PATH,
                folder=get_config()["main_folder"] + "/db",
            ).delete(node_id)

    def direct_message(self, node, data, hash_of_data):
        if "sendmefullblock" == data["action"]:
            self.send_block_to_other_nodes(node, hash_of_data=hash_of_data)

        if "fullblock" == data["action"]:
            self.get_full_chain(data, node, hash_of_data=hash_of_data)

        if "fullaccounts" == data["action"]:
            self.get_full_accounts(data, node, hash_of_data=hash_of_data)

        if "fullblockshash" == data["action"]:
            self.get_full_blockshash(data, node, hash_of_data=hash_of_data)

        if "fullblockshash_part" == data["action"]:
            self.get_full_blockshash_part(data,
                                          node,
                                          hash_of_data=hash_of_data)

        if "transactionrequest" == data["action"]:
            self.get_transaction(data, node, hash_of_data=hash_of_data)

        if "myblock" == data["action"]:
            self.get_candidate_block(data, node, hash_of_data=hash_of_data)

        if "myblockhash" == data["action"]:
            self.get_candidate_block_hash(data,
                                          node,
                                          hash_of_data=hash_of_data)

    def send_me_full_block(self, node=None):
        the_node = node if node is not None else random.choice(self.clients)
        self.logger.info(
            f"Sending sendmefullblock to {the_node.id}:{the_node.host}:{the_node.port}"
        )
        self.send_client(the_node, {"action": "sendmefullblock"})

    def send_my_block(self, block: Block):
        self.logger.info(f"Sending my block to all nodes")
        system = self_candidates(block)

        the_wait_time = (system.round_1_time - system.consensus_timer*2) / system.max_tx_number

        new_list = []

        signature_list = []

        for element in system.validating_list:
            tx_json = element.dump_json()
            new_list.append(tx_json)
            signature_list.append(element.signature)

        first_element = [new_list[0]] if len(new_list) > 0 else []

        data = {
            "action": "myblock",
            "transaction": first_element,
            "total_length": len(new_list),
            "sequence_number":
            system.sequence_number + system.empty_block_number,
            "adding": False,
        }

        self.send(data)
        time.sleep(the_wait_time)

        if len(new_list) > 1:
            for element in new_list[1:]:
                data = {
                    "action": "myblock",
                    "transaction": [element],
                    "total_length": len(new_list),
                    "sequence_number":
                    system.sequence_number + system.empty_block_number,
                    "adding": True,
                }

                self.send(data)
                time.sleep(the_wait_time)

    def send_my_block_hash(self, block):
        self.logger.info(f"Sending my block hash to all nodes")
         
        system = self_candidates(block)

        data = {
            "action": "myblockhash",
            "hash": system.hash,
            "previous_hash": system.previous_hash,
            "sequence_number":
            system.sequence_number + system.empty_block_number,
        }

        self.send(data)

    def get_candidate_block(self, data, node: client, hash_of_data=""):
        self.logger.info(f"Getting candidate block with {hash_of_data}")
        self.logger.debug(
            f"Getting candidate block from {node.id}:{node.host}:{node.port}")
        if node.candidate_block is None:
            node.candidate_block = data
            return
        if data["sequence_number"] > node.candidate_block["sequence_number"]:
            if len(node.candidate_block_history) >= 5:
                node.candidate_block_history.pop(0)

            node.candidate_block_history.append(copy.copy(
                node.candidate_block))
            node.candidate_block = data
        else:
            if node.candidate_block["total_length"] <= data["total_length"]:
                if node.candidate_block["total_length"] == data[
                        "total_length"]:
                    if data["adding"]:
                        node.candidate_block["transaction"].append(
                            data["transaction"][0])
                    else:
                        node.candidate_block = data
                else:
                    node.candidate_block = data

    def get_candidate_block_hash(self, data, node: client, hash_of_data=""):
        self.logger.info(f"Getting candidate block hash with {hash_of_data}")
        if node.candidate_block_hash is None:
            node.candidate_block_hash = data
            return

        data["sender"] = node.id

        if data["sequence_number"] > node.candidate_block_hash[
                "sequence_number"]:
            if len(node.candidate_block_hash_history) >= 5:
                node.candidate_block_hash_history.pop(0)

            node.candidate_block_hash_history.append(
                copy.copy(node.candidate_block_hash))
            node.candidate_block_hash = data
        else:
            #if len(node.candidate_block_hash["hash"]) <= len(data["hash"]):
            node.candidate_block_hash = data

    def send_full_chain(self, node=None):
        log_text = ("Sending full chain" if node is None else
                    f"Sending full chain to {node.id}:{node.host}:{node.port}")
        self.logger.info(log_text)
        file = open(self.TEMP_BLOCK_PATH, "rb")
        SendData = file.read(1024)
        while SendData:
            data = {
                "action": "fullblock",
                "byte": (SendData.decode(encoding="iso-8859-1")),
            }
            if node is None:
                self.send(data)
            else:
                self.send_client(node, data)

            SendData = file.read(1024)

            if not SendData:
                data = {
                    "action": "fullblock",
                    "byte": "end",
                }
                if node is None:
                    self.send(data)
                else:
                    self.send_client(node, data)

    def send_full_accounts(self, node=None):
        the_TEMP_ACCOUNTS_PATH = self.TEMP_ACCOUNTS_PATH
        file = open(the_TEMP_ACCOUNTS_PATH, "rb")
        SendData = file.read(1024)
        while SendData:
            data = {
                "action": "fullaccounts",
                "byte": (SendData.decode(encoding="iso-8859-1")),
            }

            if node is None:
                self.send(data)
            else:
                self.send_client(node, data)

            SendData = file.read(1024)
            if not SendData:
                data = {"action": "fullaccounts", "byte": "end"}
                if node is None:
                    self.send(data)
                else:
                    self.send_client(node, data)

    def send_full_blockshash(self, node=None):
        the_TEMP_BLOCKSHASH_PATH = self.TEMP_BLOCKSHASH_PATH
        file = open(the_TEMP_BLOCKSHASH_PATH, "rb")
        SendData = file.read(1024)
        while SendData:
            data = {
                "action": "fullblockshash",
                "byte": (SendData.decode(encoding="iso-8859-1")),
            }
            if node is None:
                self.send(data)
            else:
                self.send_client(node, data)

            SendData = file.read(1024)

            if not SendData:
                data = {"action": "fullblockshash", "byte": "end"}
                if node is None:
                    self.send(data)
                else:
                    self.send_client(node, data)

    def send_full_blockshash_part(self, node=None):
        the_TEMP_BLOCKSHASH_PART_PATH = self.TEMP_BLOCKSHASH_PART_PATH
        file = open(the_TEMP_BLOCKSHASH_PART_PATH, "rb")
        SendData = file.read(1024)
        while SendData:
            data = {
                "action": "fullblockshash_part",
                "byte": (SendData.decode(encoding="iso-8859-1")),
            }
            if node is None:
                self.send(data)
            else:
                self.send_client(node, data)

            SendData = file.read(1024)

            if not SendData:
                data = {"action": "fullblockshash_part", "byte": "end"}
                if node is None:
                    self.send(data)
                else:
                    self.send_client(node, data)

    def get_full_chain(self, data, node, hash_of_data=""):
        self.logger.info(f"Getting full chain with {hash_of_data}")
        get_ok = False

        if not os.path.exists(self.TEMP_BLOCK_PATH):
            get_ok = True
        else:
            system = GetBlock(custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH)
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:
            if str(data["byte"]) == "end":
                move(self.LOADING_BLOCK_PATH, self.TEMP_BLOCK_PATH)

                from naruno.consensus.consensus_main import consensus_trigger
                from naruno.lib.perpetualtimer import perpetualTimer

                system = GetBlock(custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH,
                                  get_normal_block=True)

                ChangeTransactionFee(system)

                perpetualTimer(system.consensus_timer, consensus_trigger)
                SaveBlock(
                    system,
                    custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH,
                    custom_TEMP_ACCOUNTS_PATH=self.TEMP_ACCOUNTS_PATH,
                    custom_TEMP_BLOCKSHASH_PATH=self.TEMP_BLOCKSHASH_PATH,
                    custom_TEMP_BLOCKSHASH_PART_PATH=self.
                    TEMP_BLOCKSHASH_PART_PATH,
                )

            else:
                os.chdir(get_config()["main_folder"])
                file = open(self.LOADING_BLOCK_PATH, "ab")

                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()

    def get_full_blockshash(self, data, node, hash_of_data=""):
        self.logger.info(f"Getting full blockshash with {hash_of_data}")
        the_TEMP_BLOCKSHASH_PATH = self.TEMP_BLOCKSHASH_PATH
        get_ok = False

        if not os.path.exists(the_TEMP_BLOCKSHASH_PATH):
            get_ok = True
        else:
            system = GetBlock(custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH)
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:
            if str(data["byte"]) == "end":
                blockshash_db.set("blockshash", None)
                with contextlib.suppress(FileNotFoundError):
                    os.remove(the_TEMP_BLOCKSHASH_PATH)
                move(self.LOADING_BLOCKSHASH_PATH, the_TEMP_BLOCKSHASH_PATH)
            else:
                os.chdir(get_config()["main_folder"])
                file = open(self.LOADING_BLOCKSHASH_PATH, "ab")
                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()

    def get_full_blockshash_part(self, data, node, hash_of_data=""):
        self.logger.info(f"Getting full blockshash part with {hash_of_data}")
        the_TEMP_BLOCKSHASH_PART_PATH = self.TEMP_BLOCKSHASH_PART_PATH
        get_ok = False

        if not os.path.exists(the_TEMP_BLOCKSHASH_PART_PATH):
            get_ok = True
        else:
            system = GetBlock(custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH)
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:
            if str(data["byte"]) == "end":
                blockshash_db.set("blockshash_part", None)
                with contextlib.suppress(FileNotFoundError):
                    os.remove(the_TEMP_BLOCKSHASH_PART_PATH)
                move(self.LOADING_BLOCKSHASH_PART_PATH,
                     the_TEMP_BLOCKSHASH_PART_PATH)
            else:
                os.chdir(get_config()["main_folder"])
                file = open(self.LOADING_BLOCKSHASH_PART_PATH, "ab")
                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()

    def get_full_accounts(self, data, node, hash_of_data=""):
        self.logger.info(f"Getting full accounts with {hash_of_data}")
        the_TEMP_ACCOUNTS_PATH = self.TEMP_ACCOUNTS_PATH
        the_LOADING_ACCOUNTS_PATH = self.LOADING_ACCOUNTS_PATH
        get_ok = False

        if not os.path.exists(the_TEMP_ACCOUNTS_PATH):
            get_ok = True
        else:
            system = GetBlock(custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH)
            if node.id == system.dowload_true_block:
                get_ok = True

        if get_ok:
            if str(data["byte"]) == "end":
                accounts_db.set("accounts", None)
                with contextlib.suppress(FileNotFoundError):
                    os.remove(the_TEMP_ACCOUNTS_PATH)
                move(the_LOADING_ACCOUNTS_PATH, the_TEMP_ACCOUNTS_PATH)
            else:
                os.chdir(get_config()["main_folder"])
                file = open(the_LOADING_ACCOUNTS_PATH, "ab")
                file.write((data["byte"].encode(encoding="iso-8859-1")))
                file.close()

    @staticmethod
    def send_transaction(
        tx,
        custom_current_time=None,
        custom_sequence_number=None,
        custom_balance=None,
        except_client=None,
        custom_server=None,
    ):
        """
        Sends the given transaction to UNL nodes.
        """
        if not tx.signature == "NARUNO":
            data = {
                "action": "transactionrequest",
                "sequence_number": tx.sequence_number,
                "txsignature": tx.signature,
                "fromUser": tx.fromUser,
                "to_user": tx.toUser,
                "data": tx.data,
                "amount": tx.amount,
                "transaction_fee": tx.transaction_fee,
                "transaction_time": tx.transaction_time,
                "custom_current_time": custom_current_time,
                "custom_sequence_number": custom_sequence_number,
                "custom_balance": custom_balance,
            }
            the_server = server.Server if custom_server is None else custom_server
            the_server.send(data, except_client=except_client)

    def get_transaction(self, data, node, hash_of_data=""):
        self.logger.info(f"Getting transaction with {hash_of_data}")
        block = GetBlock(custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH)
        the_transaction = Transaction(
            data["sequence_number"],
            data["txsignature"],
            data["fromUser"],
            data["to_user"],
            data["data"],
            data["amount"],
            data["transaction_fee"],
            data["transaction_time"],
        )
        custom_current_time = None
        custom_sequence_number = None
        custom_balance = None
        if self.custom_variables:
            custom_current_time = data["custom_current_time"]
            custom_sequence_number = data["custom_sequence_number"]
            custom_balance = data["custom_balance"]

        if GetTransaction(
                block,
                the_transaction,
                custom_current_time=custom_current_time,
                custom_sequence_number=custom_sequence_number,
                custom_balance=custom_balance,
                custom_PENDING_TRANSACTIONS_PATH=self.
                PENDING_TRANSACTIONS_PATH,
        ):
            server.send_transaction(the_transaction,
                                    except_client=node,
                                    custom_server=self)
            SaveBlock(
                block,
                custom_TEMP_BLOCK_PATH=self.TEMP_BLOCK_PATH,
                custom_TEMP_ACCOUNTS_PATH=self.TEMP_ACCOUNTS_PATH,
                custom_TEMP_BLOCKSHASH_PATH=self.TEMP_BLOCKSHASH_PATH,
                custom_TEMP_BLOCKSHASH_PART_PATH=self.
                TEMP_BLOCKSHASH_PART_PATH,
            )

    def send_block_to_other_nodes(self,
                                  node=None,
                                  sync=False,
                                  hash_of_data=""):
        """
        Sends the block to the other nodes.
        """
        self.logger.info(f"Sending block to other nodes with {hash_of_data}")
        if node is None or sync:
            self.send_full_accounts(node=node)
            self.send_full_blockshash(node=node)
            self.send_full_blockshash_part(node=node)
            self.send_full_chain(node=node)
        else:
            self.sync_clients.append(node)

    def get_ip(self):
        """
        Returns the IP address of the socket in this class.
        """
        ip = self.sock.getsockname()[0]
        return ip
