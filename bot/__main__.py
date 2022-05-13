import shutil, psutil
import signal
import os
import asyncio

from pyrogram import idle
from bot import app
from sys import executable

from telegram import ParseMode
from telegram.ext import CommandHandler
from wserver import start_server_async
from bot import bot, IMAGE_URL, dispatcher, updater, botStartTime, IGNORE_PENDING_REQUESTS, IS_VPS, SERVER_PORT, OWNER_ID, AUTHORIZED_CHATS
from bot.helper.ext_utils import fs_utils
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import *
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper import button_build
from .modules import authorize, list, cancel_mirror, mirror_status, mirror, clone, watch, shell, eval, torrent_search, delete, speedtest, count, config, updates


def stats(update, context):
    currentTime = get_readable_time(time.time() - botStartTime)
    total, used, free = shutil.disk_usage('.')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
    recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
    cpuUsage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    stats = f'<b>╭──「⭕️ BOT STATISTICS ⭕️」</b>\n' \
            f'<b>│</b>\n' \
            f'<b>├  ⏰ Bot Uptime : {currentTime}</b>\n' \
            f'<b>├  💾 Total Disk Space : {total}</b>\n' \
            f'<b>├  📀 Total Used Space : {used}</b>\n' \
            f'<b>├  💿 Total Free Space : {free}</b>\n' \
            f'<b>├  🔼 Total Upload : {sent}</b>\n' \
            f'<b>├  🔽 Total Download : {recv}</b>\n' \
            f'<b>├  🖥️ CPU : {cpuUsage}%</b>\n' \
            f'<b>├  🎮 RAM : {memory}%</b>\n' \
            f'<b>├  💽 DISK : {disk}%</b>\n' \
            f'<b>│</b>\n' \
            f'<b>╰──「 🚸 @AT_BOTs 🚸 」</b>'
    update.effective_message.reply_photo(IMAGE_URL, stats, parse_mode=ParseMode.HTML)


def start(update, context):
    start_string = f'''
This bot can mirror all your links to Google Drive!
Type /{BotCommands.HelpCommand} to get a list of available commands
'''
    buttons = button_build.ButtonMaker()
    buttons.buildbutton("Repo", "https://github.com/ayushteke/slam_aria_mirror_bot")
    buttons.buildbutton("Channel", "https://t.me/AT_BOTs")
    reply_markup = InlineKeyboardMarkup(buttons.build_menu(2))
    LOGGER.info('UID: {} - UN: {} - MSG: {}'.format(update.message.chat.id, update.message.chat.username, update.message.text))
    uptime = get_readable_time((time.time() - botStartTime))
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        if update.message.chat.type == "private" :
            sendMessage(f"Hey I'm Alive 🙂\nSince: <code>{uptime}</code>", context.bot, update)
        else :
            sendMarkup(IMAGE_URL, start_string, context.bot, update, reply_markup)
    else :
        sendMarkup(f"Oops! You are not allowed to use me.</b>.", context.bot, update, reply_markup)


def restart(update, context):
    restart_message = sendMessage("Restarting, Please wait!", context.bot, update)
    # Save restart message object in order to reply to it after restarting
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    fs_utils.clean_all()
    os.execl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time.time() * 1000))
    reply = sendMessage("Starting Ping", context.bot, update)
    end_time = int(round(time.time() * 1000))
    editMessage(f'{end_time - start_time} ms', reply)


def log(update, context):
    sendLogFile(context.bot, update)


def bot_help(update, context):
    help_string_adm = f'''
/{BotCommands.HelpCommand}: To get this message
/{BotCommands.MirrorCommand} [download_url][magnet_link]: Start mirroring the link to Google Drive. Use /{BotCommands.MirrorCommand} qb to mirror with qBittorrent, and use /{BotCommands.MirrorCommand} qbs to select files before downloading
/{BotCommands.TarMirrorCommand} [download_url][magnet_link]: Start mirroring and upload the archived (.tar) version of the download
/{BotCommands.ZipMirrorCommand} [download_url][magnet_link]: Start mirroring and upload the archived (.zip) version of the download
/{BotCommands.UnzipMirrorCommand} [download_url][magnet_link]: Starts mirroring and if downloaded file is any archive, extracts it to Google Drive
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive Links
/{BotCommands.DeleteCommand} [drive_url]: Delete file from Google Drive (Only Owner & Sudo)
/{BotCommands.WatchCommand} [youtube-dl supported link]: Mirror through youtube-dl. Click /{BotCommands.WatchCommand} for more help
/{BotCommands.TarWatchCommand} [youtube-dl supported link]: Mirror through youtube-dl and tar before uploading
/{BotCommands.CancelMirror}: Reply to the message by which the download was initiated and that download will be cancelled
/{BotCommands.CancelAllCommand}: Cancel all running tasks
/{BotCommands.ListCommand} [search term]: Searches the search term in the Google Drive, If found replies with the link
/{BotCommands.StatusCommand}: Shows a status of all the downloads
/{BotCommands.StatsCommand}: Show Stats of the machine the bot is hosted on
/{BotCommands.PingCommand}: Check how long it takes to Ping the Bot
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Can only be invoked by Owner & Sudo of the bot)
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Can only be invoked by Owner & Sudo of the bot)
/{BotCommands.AuthorizedUsersCommand}: Show authorized users (Only Owner & Sudo)
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner)
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner)
/{BotCommands.RestartCommand}: Restart the bot
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports
/{BotCommands.ConfigMenuCommand}: Get Info Menu about bot config (Owner Only)
/{BotCommands.UpdateCommand}: Update Bot from Upstream Repo (Owner Only)
/{BotCommands.SpeedCommand}: Check Internet Speed of the Host
/{BotCommands.ShellCommand}: Run commands in Shell (Terminal)
/{BotCommands.ExecHelpCommand}: Get help for Executor module (Only Owner)
/{BotCommands.GDTOTCommand}: Send GDTOT link along with command
'''

    help_string = f'''
/{BotCommands.HelpCommand}: To get this message
/{BotCommands.MirrorCommand} [download_url][magnet_link]: Start mirroring the link to Google Drive. Use /{BotCommands.MirrorCommand} qb to mirror with qBittorrent, and use /{BotCommands.MirrorCommand} qbs to select files before downloading
/{BotCommands.TarMirrorCommand} [download_url][magnet_link]: Start mirroring and upload the archived (.tar) version of the download
/{BotCommands.ZipMirrorCommand} [download_url][magnet_link]: Start mirroring and upload the archived (.zip) version of the download
/{BotCommands.UnzipMirrorCommand} [download_url][magnet_link]: Starts mirroring and if downloaded file is any archive, extracts it to Google Drive
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive Links
/{BotCommands.WatchCommand} [youtube-dl supported link]: Mirror through youtube-dl. Click /{BotCommands.WatchCommand} for more help
/{BotCommands.TarWatchCommand} [youtube-dl supported link]: Mirror through youtube-dl and tar before uploading
/{BotCommands.CancelMirror}: Reply to the message by which the download was initiated and that download will be cancelled
/{BotCommands.ListCommand} [search term]: Searches the search term in the Google Drive, If found replies with the link
/{BotCommands.StatusCommand}: Shows a status of all the downloads
/{BotCommands.StatsCommand}: Show Stats of the machine the bot is hosted on
/{BotCommands.PingCommand}: Check how long it takes to Ping the Bot
/{BotCommands.GDTOTCommand}: Send GDTOT link along with command
'''

    if CustomFilters.sudo_user(update) or CustomFilters.owner_filter(update):
        sendMessage(help_string_adm, context.bot, update)
    else:
        sendMessage(help_string, context.bot, update)


botcmds = [
        (f'{BotCommands.HelpCommand}','Get Detailed Help'),
        (f'{BotCommands.MirrorCommand}', 'Start Mirroring'),
        (f'{BotCommands.TarMirrorCommand}','Start mirroring and upload as .tar'),
        (f'{BotCommands.UnzipMirrorCommand}','Extract files'),
        (f'{BotCommands.ZipMirrorCommand}','Start mirroring and upload as .zip'),
        (f'{BotCommands.CloneCommand}','Copy file/folder to Drive'),
        (f'{BotCommands.CountCommand}','Count file/folder of Drive link'),
        (f'{BotCommands.DeleteCommand}','Delete file from Drive'),
        (f'{BotCommands.WatchCommand}','Mirror Youtube-dl support link'),
        (f'{BotCommands.TarWatchCommand}','Mirror Youtube playlist link as .tar'),
        (f'{BotCommands.CancelMirror}','Cancel a task'),
        (f'{BotCommands.CancelAllCommand}','Cancel all tasks'),
        (f'{BotCommands.ListCommand}','Searches files in Drive'),
        (f'{BotCommands.StatusCommand}','Get Mirror Status message'),
        (f'{BotCommands.StatsCommand}','Bot Usage Stats'),
        (f'{BotCommands.PingCommand}','Ping the Bot'),
        (f'{BotCommands.RestartCommand}','Restart the bot [owner/sudo only]'),
        (f'{BotCommands.LogCommand}','Get the Bot Log [owner/sudo only]'),
        (f'{BotCommands.GDTOTCommand}: Send GDTOT link along with command')
    ]


def main():
    fs_utils.start_cleanup()
    if IS_VPS:
        asyncio.get_event_loop().run_until_complete(start_server_async(PORT))
    # Check if the bot is restarting
    if os.path.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text("Restarted successfully!", chat_id, msg_id)
        os.remove(".restartmsg")
    elif OWNER_ID:
        try:
            text = "<b>Bot Restarted!</b>"
            bot.sendMessage(chat_id=OWNER_ID, text=text, parse_mode=ParseMode.HTML)
            if AUTHORIZED_CHATS:
                for i in AUTHORIZED_CHATS:
                    bot.sendMessage(chat_id=i, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            LOGGER.warning(e)
    
    bot.set_my_commands(botcmds)

    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand,
                                  bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand,
                                   stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("Bot Started!")
    signal.signal(signal.SIGINT, fs_utils.exit_clean_up)

app.start()
main()
idle()
