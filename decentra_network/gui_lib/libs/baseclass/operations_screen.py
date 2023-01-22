#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from hashlib import sha256

from kivy.core.clipboard import Clipboard
from kivymd.uix.bottomsheet import MDListBottomSheet
from kivymd.uix.button import MDFlatButton
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.screen import MDScreen
from kivymd_extensions.sweetalert import SweetAlert

from decentra_network.blockchain.block.get_block import GetBlock
from decentra_network.blockchain.block.save_block import SaveBlock
from decentra_network.config import MY_TRANSACTION_EXPORT_PATH
from decentra_network.lib.export import export_the_transactions
from decentra_network.lib.settings_system import the_settings
from decentra_network.transactions.my_transactions.get_my_transaction import \
    GetMyTransaction
from decentra_network.transactions.my_transactions.save_to_my_transaction import \
    SavetoMyTransaction
from decentra_network.transactions.send import send
from decentra_network.wallet.wallet_import import wallet_import
from decentra_network.lib.sign import sign
from decentra_network.lib.verify import verify

class OperationScreen(MDScreen):
    pass


class Send_Coin_Box(MDGridLayout):
    cols = 2

class Sign_Box(MDGridLayout):
    cols = 2
class Verify_Box(MDGridLayout):
    cols = 2

class OperationBox(MDGridLayout):
    cols = 2
    send_coin_dialog = None
    sign_dialog = None
    verify_dialog = None
    export_transaction_csv_dialog = None
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
                        font_size="18sp",
                        font_name=f"{self.FONT_PATH}Poppins-Bold",
                    ),
                    MDFlatButton(
                        text="OK",
                        on_press=self.sent_the_coins,
                        font_size="18sp",
                        font_name=f"{self.FONT_PATH}Poppins-Bold",
                    ),
                ],
            )

        self.send_coin_dialog.open()

    def show_sign_dialog(self):
        if not self.sign_dialog:
            self.sign_dialog = SweetAlert(
                title="Sign Data",
                type="custom",
                auto_dismiss=False,
                content_cls=Sign_Box(),
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_press=self.dismiss_sign_dialog,
                        font_size="18sp",
                        font_name=f"{self.FONT_PATH}Poppins-Bold",
                    ),
                    MDFlatButton(
                        text="OK",
                        on_press=self.sign_the_data,
                        font_size="18sp",
                        font_name=f"{self.FONT_PATH}Poppins-Bold",
                    ),
                ],
            )

        self.sign_dialog.open()

    def show_verify_dialog(self):
        if not self.verify_dialog:
            self.verify_dialog = SweetAlert(
                title="Verify Signed Data",
                type="custom",
                auto_dismiss=False,
                content_cls=Verify_Box(),
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_press=self.dismiss_verify_dialog,
                        font_size="18sp",
                        font_name=f"{self.FONT_PATH}Poppins-Bold",
                    ),
                    MDFlatButton(
                        text="OK",
                        on_press=self.verify_the_data,
                        font_size="18sp",
                        font_name=f"{self.FONT_PATH}Poppins-Bold",
                    ),
                ],
            )

        self.verify_dialog.open()


    def get_send_coin_dialog_text(self):
        text_list = []
        for obj in self.send_coin_dialog.content_cls.children:
            for sub_obj in obj.children:
                text_list.append(sub_obj.text)

                sub_obj.text = ""

        return text_list


    def get_sign_dialog_text(self):
        text_list = []
        for obj in self.sign_dialog.content_cls.children:
            for sub_obj in obj.children:
                text_list.append(sub_obj.text)

                sub_obj.text = ""

        return text_list

    def get_verify_dialog_text(self):
        text_list = []
        for obj in self.verify_dialog.content_cls.children:
            for sub_obj in obj.children:
                text_list.append(sub_obj.text)

                sub_obj.text = ""

        return text_list

    def sent_the_coins(self, widget):
        the_block = GetBlock()

        text_list = self.get_send_coin_dialog_text()
        receiver_adress = text_list[3]
        amount = text_list[2]
        data = text_list[1]

        if float(amount) >= the_block.minumum_transfer_amount:
            if (wallet_import(int(the_settings()["wallet"]), 2) == sha256(
                    text_list[0].encode("utf-8")).hexdigest()):
                block = the_block
                send_tx = send(
                    text_list[0],
                    receiver_adress,
                    amount=float(amount),
                    data=str(data),
                    block=block,
                )
                if send_tx != False:

                    from decentra_network.node.server.server import server

                    if server.Server is None:
                        SweetAlert().fire(
                            "Please start the node server",
                            type="failure",
                        )
                        return False

                    SavetoMyTransaction(send_tx, sended=True)
                    server.send_transaction(send_tx)
                    SaveBlock(block)
            else:
                SweetAlert().fire(
                    "Password is not correct",
                    type="failure",
                )
            del text_list

        self.send_coin_dialog.dismiss()


    def sign_the_data(self, widget):


        text_list = self.get_sign_dialog_text()

        data = text_list[1]
        path = sign(data, text_list[0])

        Clipboard.copy(path)


        SweetAlert().fire(
                            f"Signed data file created in {path}, The file has been copied to your clipboard.",
                            type="success",
                        )

        del text_list

        self.sign_dialog.dismiss()

    def verify_the_data(self, widget):


        text_list = self.get_verify_dialog_text()

        path = text_list[0]
        result = verify(path)

        if result == True:
            SweetAlert().fire(
                            "Data is verified",
                            type="success",
                        )
        else:
            SweetAlert().fire(
                            "Data is not verified",
                            type="failure",
                        )


        self.verify_dialog.dismiss()

    def dismiss_send_coin_dialog(self, widget):
        self.get_send_coin_dialog_text()

        self.send_coin_dialog.dismiss()

    def dismiss_sign_dialog(self, widget):
        self.get_sign_dialog_text()

        self.sign_dialog.dismiss()

    def dismiss_verify_dialog(self, widget):
        self.get_verify_dialog_text()

        self.verify_dialog.dismiss()

    def send_coin(self):
        try:
            GetBlock()
        except FileNotFoundError:
            SweetAlert().fire(
                "Please connect to an network.",
                type="failure",
            )
            return False
        self.show_send_coin_dialog()


    def sign(self):
        self.show_sign_dialog()

    def verify(self):
        self.show_verify_dialog()

    def export_transaction_csv(self):
        if export_the_transactions():
            Clipboard.copy(MY_TRANSACTION_EXPORT_PATH)
            SweetAlert().fire(
                f"CSV file created in {MY_TRANSACTION_EXPORT_PATH} directory, The directory has been copied to your clipboard.",
                type="success",
            )
        else:
            SweetAlert().fire(
                "You have not a transaction",
                type="failure",
            )

    def callback_for_transaction_history_items(self, widget):
        pass

    def transaction_history(self):
        transactions = GetMyTransaction()
        if len(transactions) != 0:
            bottom_sheet_menu = MDListBottomSheet(radius=25, radius_from="top")
            data = {
                tx[0]:
                f"{tx[0].toUser} | {str(tx[0].amount)} | {str(tx[0].transaction_fee)} | {str(tx[1])}"
                for tx in transactions
            }

            for item in data.items():
                bottom_sheet_menu.add_item(
                    item[1],
                    lambda x, y=item[0]: self.
                    callback_for_transaction_history_items(y),
                )
            bottom_sheet_menu.open()
        else:
            SweetAlert().fire(
                "You have not a transaction",
                type="failure",
            )
