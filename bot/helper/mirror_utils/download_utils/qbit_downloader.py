# Implement By - @anasty17 (https://github.com/breakdowns/slam-mirrorbot/commit/0bfba523f095ab1dccad431d72561e0e002e7a59)
# (c) https://github.com/breakdowns/slam-mirrorbot
# All rights reserved

import os
import random
import string
import time
import logging
import shutil

import qbittorrentapi as qba
from fnmatch import fnmatch
from urllib.parse import urlparse, parse_qs
from torrentool.api import Torrent
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from bot import download_dict, download_dict_lock, BASE_URL, dispatcher, get_client, TORRENT_DIRECT_LIMIT, TAR_UNZIP_LIMIT
from bot.helper.mirror_utils.status_utils.qbit_download_status import QbDownloadStatus
from bot.helper.telegram_helper.message_utils import *
from bot.helper.ext_utils.bot_utils import setInterval, new_thread, MirrorStatus, getDownloadByGid, get_readable_file_size, check_limit
from bot.helper.telegram_helper import button_build

LOGGER = logging.getLogger(__name__)


class qbittorrent:


    def __init__(self):
        self.update_interval = 2
        self.meta_time = time.time()
        self.stalled_time = time.time()
        self.checked = False

    @new_thread
    def add_torrent(self, link, dire, listener, qbitsel):
        self.client = get_client()
        self.listener = listener
        self.dire = dire
        self.qbitsel = qbitsel
        is_file = False
        count = 0
        pincode = ""
        try:
            if os.path.exists(link):
                is_file = True
                self.ext_hash = get_hash_file(link)
            else:
                self.ext_hash = get_hash_magnet(link)
            tor_info = self.client.torrents_info(torrent_hashes=self.ext_hash)
            if len(tor_info) > 0:
                sendMessage("This torrent is already in list.", listener.bot, listener.update)
                return
            if is_file:
                op = self.client.torrents_add(torrent_files=[link], save_path=dire)
                os.remove(link)
            else:
                op = self.client.torrents_add(link, save_path=dire)
            if op.lower() == "ok.":
                tor_info = self.client.torrents_info(torrent_hashes=self.ext_hash)
                if len(tor_info) == 0:
                    while True:
                        if time.time() - self.meta_time >= 300:
                            sendMessage("The torrent was not added. report when u see this error", listener.bot, listener.update)
                            return False
                        tor_info = self.client.torrents_info(torrent_hashes=self.ext_hash)
                        if len(tor_info) > 0:
                            break
            else:
                sendMessage("This is an unsupported/invalid link.", listener.bot, listener.update)
                return
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=14))
            with download_dict_lock:
                download_dict[listener.uid] = QbDownloadStatus(gid, listener, self.ext_hash, self.client)
            tor_info = tor_info[0]
            LOGGER.info(f"QbitDownload started: {tor_info.name}")
            self.updater = setInterval(self.update_interval, self.update)
            if BASE_URL is not None and qbitsel:
                if is_file:
                    self.client.torrents_pause(torrent_hashes=self.ext_hash)
                else:
                    meta = sendMessage("Downloading Metadata...Please wait then you can select files or mirror torrent file if it have low seeders", listener.bot, listener.update)
                    while True:
                            tor_info = self.client.torrents_info(torrent_hashes=self.ext_hash)
                            if len(tor_info) == 0:
                                deleteMessage(listener.bot, meta)
                                return False
                            try:
                                tor_info = tor_info[0]
                                if tor_info.state == "metaDL" or tor_info.state == "checkingResumeData":
                                    time.sleep(0.5)
                                else:
                                    self.client.torrents_pause(torrent_hashes=self.ext_hash)
                                    deleteMessage(listener.bot, meta)
                                    break
                            except:
                                deleteMessage(listener.bot, meta)
                                return False
                for n in str(self.ext_hash):
                    if n.isdigit():
                        pincode += str(n)
                        count += 1
                    if count == 4:
                        break
                URL = f"{BASE_URL}/slam/files/{self.ext_hash}"
                pindata = f"pin {gid} {pincode}"
                donedata = f"done {gid} {self.ext_hash}"
                buttons = button_build.ButtonMaker()
                buttons.buildbutton("Select Files", URL)
                buttons.sbutton("Pincode", pindata)
                buttons.sbutton("Done Selecting", donedata)
                QBBUTTONS = InlineKeyboardMarkup(buttons.build_menu(2))
                msg = "Your download paused. Choose files then press Done Selecting button to start downloading."
                sendMarkup(msg, listener.bot, listener.update, QBBUTTONS)
            else:
                sendStatusMessage(listener.update, listener.bot)
        except qba.UnsupportedMediaType415Error as e:
            LOGGER.error(str(e))
            sendMessage("This is an unsupported/invalid link. {str(e)}", listener.bot, listener.update)
        except Exception as e:
            LOGGER.error(str(e))
            sendMessage(str(e), listener.bot, listener.update)
            self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)


    def update(self):
        tor_info = self.client.torrents_info(torrent_hashes=self.ext_hash)
        if len(tor_info) == 0:
            self.updater.cancel()
            return
        try:
            tor_info = tor_info[0]
            if tor_info.state == "metaDL":
                self.stalled_time = time.time()
                if time.time() - self.meta_time >= 600:
                    self.listener.onDownloadError("Dead Torrent!")
                    self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)
                    self.updater.cancel()
                    return
            elif tor_info.state == "downloading":
                self.stalled_time = time.time()
                if (TORRENT_DIRECT_LIMIT is not None or TAR_UNZIP_LIMIT is not None) and not self.checked:
                    if self.listener.isTar or self.listener.extract:
                        is_tar_ext = True
                        mssg = f'Tar/Unzip limit is {TAR_UNZIP_LIMIT}'
                    else:
                        is_tar_ext = False
                        mssg = f'Torrent/Direct limit is {TORRENT_DIRECT_LIMIT}'
                    size = tor_info.size
                    result = check_limit(size, TORRENT_DIRECT_LIMIT, TAR_UNZIP_LIMIT, is_tar_ext)
                    self.checked = True
                    if result:
                        self.listener.onDownloadError(f"{mssg}.\nYour File/Folder size is {get_readable_file_size(size)}")
                        self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)
                        self.updater.cancel()
                        return
            elif tor_info.state == "stalledDL":
                if time.time() - self.stalled_time >= 900:
                    self.listener.onDownloadError("Dead Torrent!")
                    self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)
                    self.updater.cancel()
                    return
            elif tor_info.state == "error":
                self.listener.onDownloadError("Error. IDK why, report in support group")
                self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)
                self.updater.cancel()
                return
            elif tor_info.state == "uploading" or tor_info.state.lower().endswith("up"):
                self.client.torrents_pause(torrent_hashes=self.ext_hash)
                if self.qbitsel:
                    for dirpath, subdir, files in os.walk(f"{self.dire}", topdown=False):
                        for file in files:
                            if fnmatch(file, "*.!qB"):
                                os.remove(os.path.join(dirpath, file))
                        for folder in subdir:
                            if fnmatch(folder, ".unwanted"):
                                shutil.rmtree(os.path.join(dirpath, folder))
                        if not os.listdir(dirpath):
                            os.rmdir(dirpath)
                self.listener.onDownloadComplete()
                self.client.torrents_delete(torrent_hashes=self.ext_hash, delete_files=True)
                self.updater.cancel()
        except:
            self.updater.cancel()


def get_confirm(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split(" ")
    qdl = getDownloadByGid(data[1])
    if qdl is not None:
        if user_id != qdl.listener.message.from_user.id:
            query.answer(text="Don't waste your time!", show_alert=True)
            return
        if data[0] == "pin":
            query.answer(text=data[2], show_alert=True)
        elif data[0] == "done":
            query.answer()
            qdl.client.torrents_resume(torrent_hashes=data[2])
            sendStatusMessage(qdl.listener.update, qdl.listener.bot)
            query.message.delete()
    else:
        query.answer(text="This task has been cancelled!", show_alert=True)
        query.message.delete()


def get_hash_magnet(mgt):
    if mgt.startswith('magnet:'):
        _, _, _, _, query, _ = urlparse(mgt)

    qs = parse_qs(query)
    v = qs.get('xt', None)
    
    if v == None or v == []:
        LOGGER.error('Invalid magnet URI: no "xt" query parameter.')
        return False
        
    v = v[0]
    if not v.startswith('urn:btih:'):
        LOGGER.error('Invalid magnet URI: "xt" value not valid for BitTorrent.')
        return False

    mgt = v[len('urn:btih:'):]
    return mgt.lower()


def get_hash_file(path):
    tr = Torrent.from_file(path)
    mgt = tr.magnet_link
    return get_hash_magnet(mgt)


pin_handler = CallbackQueryHandler(get_confirm, pattern="pin", run_async=True)
done_handler = CallbackQueryHandler(get_confirm, pattern="done", run_async=True)
dispatcher.add_handler(pin_handler)
dispatcher.add_handler(done_handler)
