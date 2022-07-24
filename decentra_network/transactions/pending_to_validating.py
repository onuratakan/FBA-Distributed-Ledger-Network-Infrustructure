#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

from decentra_network.transactions.pending.get_pending import GetPending
from decentra_network.transactions.pending.delete_pending import DeletePending


def PendingtoValidating(block):
    """
    Adds transactions to the verification list
    if there are suitable conditions.
    """

    if (
        len(block.validating_list) < block.max_tx_number
    ):
        if block.raund_2_starting_time is None and not (time.time() - block.raund_1_starting_time) > (block.raund_1_time / 2):
            for tx in GetPending():
                if len(block.validating_list) < block.max_tx_number:
                    block.validating_list.append(tx)
                    DeletePending(tx)
