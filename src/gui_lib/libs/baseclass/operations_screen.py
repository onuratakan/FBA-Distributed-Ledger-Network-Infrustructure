#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import os
from hashlib import sha256

from kivy.metrics import dp

from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFlatButton
from kivymd.uix.datatables import MDDataTable
from kivymd_extensions.sweetalert import SweetAlert

from kivy.core.clipboard import Clipboard

from transactions.send_coin import send_coin
from transactions.save_to_my_transaction import GetMyTransaction

from blockchain.block.get_block import GetBlock

from wallet.wallet import Wallet_Import

from lib.settings_system import the_settings
from lib.export import export_the_transactions

from config import MY_TRANSACTION_EXPORT_PATH

class OperationScreen(MDScreen):
    pass

class Send_Coin_Box(MDGridLayout):
    cols = 2


class Transaction_History_Box(MDGridLayout):
    cols = 1


class OperationBox(MDGridLayout):
    cols = 2
    send_coin_dialog = None
    export_transaction_csv_dialog = None
    transaction_history_dialog = None
    FONT_PATH = f"{os.environ['DECENTRA_ROOT']}/gui_lib/fonts/"


    def show_send_coin_dialog(self):
        if not self.send_coin_dialog:
            self.send_coin_dialog = SweetAlert(
                title="Send Coin",
                type="custom",
                auto_dismiss=False,
                content_cls=Send_Coin_Box(),
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_press=self.dismiss_send_coin_dialog,
                        font_size= "18sp",
                        font_name= self.FONT_PATH + "RobotoCondensed-Bold",
                    ),
                    MDFlatButton(
                        text="OK",
                        on_press=self.sent_the_coins,
                        font_size= "18sp",
                        font_name= self.FONT_PATH + "RobotoCondensed-Bold",
                    ),
                ],
            )
        self.send_coin_dialog.open()


    def get_send_coin_dialog_text(self):
        text_list = []
        for obj in self.send_coin_dialog.content_cls.children:
            for sub_obj in obj.children:
                text_list.append(sub_obj.text)

                sub_obj.text = ""

        return text_list
    def sent_the_coins(self,widget):


        text_list = self.get_send_coin_dialog_text()
        receiver_adress = text_list[2]
        amount = text_list[1]


        if not float(amount) < GetBlock().minumum_transfer_amount:
            if Wallet_Import(int(the_settings()["wallet"]),2) == sha256(text_list[0].encode("utf-8")).hexdigest():
                send_coin(float(amount), receiver_adress, text_list[0])
            else:
                SweetAlert().fire(
                    "Password is not correct",
                    type='failure',
                )                
            del text_list

        

        self.send_coin_dialog.dismiss()
    def dismiss_send_coin_dialog(self,widget):
        self.get_send_coin_dialog_text()

        self.send_coin_dialog.dismiss()

    def send_coin(self):
        self.show_send_coin_dialog()



    def export_transaction_csv(self):
        transactions = GetMyTransaction()
        if not len(transactions) == 0:
            Clipboard.copy(MY_TRANSACTION_EXPORT_PATH)
            SweetAlert().fire(
                f"CSV file created in {MY_TRANSACTION_EXPORT_PATH} directory, The directory has been copied to your clipboard.",
                type='success',
            )
        else:
            SweetAlert().fire(
                "You have not a transaction",
                type='failure',
            )

    def dismiss_transaction_history_dialog(self,widget):
        self.transaction_history_dialog.dismiss()

    def transaction_history(self):
        if export_the_transactions():
            self.transaction_history_dialog = SweetAlert(
                  title="Send Coin",
                  type="custom",
                  auto_dismiss=False,
                  content_cls=Transaction_History_Box(),
                  buttons=[
                      MDFlatButton(
                          text="OK",
                          on_press=self.dismiss_transaction_history_dialog,
                          font_size= "18sp",
                          font_name= self.FONT_PATH + "RobotoCondensed-Bold",
                      ),
                  ],
              )
            self.transaction_history_dialog.open()
        else:
            SweetAlert().fire(
                "You have not a transaction",
                type='failure',
            )                     
        