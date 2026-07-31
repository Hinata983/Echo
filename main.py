import time
import re
import asyncio
import aiohttp
import discord
from discord import app_commands
import os
import logging
from logging.handlers import RotatingFileHandler
import aiosqlite
import io
import unicodedata

# Discordボットトークン設定
DISCORD_TOKEN                 = 'YOUR_DISCORD_TOKEN'

# マスターユーザーID設定
MASTER_USER_ID                = 1234567890123456789

# 動作設定
MAX_MESSAGES                  = 5000               # Discordメッセージキャッシュ
MAX_MESSAGE_LENGTH            = 1800               # メッセージの最大文字数
COOLDOWN_SECONDS              = 1                  # ユーザーごとの連続送信制限秒数
REPLY_PREVIEW_LENGTH          = 12                 # 返信プレビュー全角文字数
CONFIG_CHANNEL_NAME_LENGTH    = 15                 # コンフィグのチャンネル名最大文字数

DELETE_ON_COOLDOWN            = True               # クールダウン時のメッセージ削除

# ウェブフック設定
WEBHOOK_NAME                  = 'Echo-Webhook'     # 使用するWebhookの名前

# プレフィックス設定
PREFIX_IGNORE                 = (',', '.', '!')    # 無視プレフィックス

# メンション制限
MENTION_RESTRICTION           = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=True)

# 基本情報
BOT_VERSION    = 'v1.0.23-202608B01'
AUTHOR_NAME    = 'Hinata983'
GITHUB_URL     = 'https://github.com/Hinata983/Echo'

# URL正規表現
GENERAL_URL_PATTERN = r'https?://\S+'

# デバッグ情報
DEBUG_INFORMATION = f"""About Echo
Version: {BOT_VERSION}

Max Length: {MAX_MESSAGE_LENGTH}
Cooldown: {COOLDOWN_SECONDS}
Reply Preview Length: {REPLY_PREVIEW_LENGTH}
Config Channel Name Length: {CONFIG_CHANNEL_NAME_LENGTH}

Delete on Cooldown: {DELETE_ON_COOLDOWN}

By {AUTHOR_NAME}
{GITHUB_URL}
"""

# ヘルプ情報
HELP_INFORMATION = f"""Echoについて
バージョン: {BOT_VERSION}

Echoはあなたのアバターと名前を維持したままメッセージを再送信する機能を提供します。

コマンドリスト
/say [text]
Echoでテキストを送信

/enable
Echoを有効化

/disable
Echoを無効化

/channel enable
チャンネルのEcho機能を有効化

/channel disable
チャンネルのEcho機能を無効化

/config
サーバーのEcho設定を管理

ヒント
Echoで送信されたメッセージは、右クリック → アプリのメニューから「編集」や「削除」が可能です。
"""

# ヘルプ情報（英語）
HELP_INFORMATION_EN = f"""About Echo
Version: {BOT_VERSION}

Echo provides a feature to resend messages while maintaining your avatar and name.

Command List
/say [text]
Send text via Echo

/enable
Enable Echo

/disable
Disable Echo

/channel enable
Enable Echo feature for the channel

/channel disable
Disable Echo feature for the channel

/config
Manage Echo settings for the server

Hint
Messages sent via Echo can be edited or deleted from the right-click -> Apps menu.
"""

# ヘルプ情報（フランス語）
HELP_INFORMATION_FR = f"""À propos d'Echo
Version: {BOT_VERSION}

Echo offre une fonctionnalité permettant de renvoyer des messages tout en conservant votre avatar et votre nom.

Liste des commandes
/say [text]
Envoyer du texte via Echo

/enable
Activer Echo

/disable
Désactiver Echo

/channel enable
Activer la fonctionnalité Echo pour le salon

/channel disable
Désactiver la fonctionnalité Echo pour le salon

/config
Gérer les paramètres d'Echo pour le serveur

Astuce
Les messages envoyés via Echo peuvent être modifiés ou supprimés depuis le menu clic droit -> Applications.
"""

# ヘルプ情報（ドイツ語）
HELP_INFORMATION_DE = f"""Über Echo
Version: {BOT_VERSION}

Echo bietet eine Funktion zum erneuten Senden von Nachrichten unter Beibehaltung Ihres Avatars und Namens.

Befehlsliste
/say [text]
Text über Echo senden

/enable
Echo aktivieren

/disable
Echo deaktivieren

/channel enable
Echo-Funktion für den Kanal aktivieren

/channel disable
Echo-Funktion für den Kanal deaktivieren

/config
Echo-Einstellungen für den Server verwalten

Tipp
Über Echo gesendete Nachrichten können über das Rechtsklick-Menü -> Apps bearbeitet oder gelöscht werden.
"""

# ヘルプ情報（韓国語）
HELP_INFORMATION_KO = f"""Echo에 대하여
버전: {BOT_VERSION}

Echo는 아바타와 이름을 유지한 채 메시지를 다시 전송하는 기능을 제공합니다.

명령어 목록
/say [text]
Echo로 텍스트 전송

/enable
Echo 활성화

/disable
Echo 비활성화

/channel enable
채널의 Echo 기능 활성화

/channel disable
채널의 Echo 기능 비활성화

/config
서버의 Echo 설정을 관리

팁
Echo로 전송된 메시지는 우클릭 → 앱 메뉴에서 '편집'이나 '삭제'가 가능합니다.
"""

# ヘルプ情報（中国語）
HELP_INFORMATION_ZH = f"""關於 Echo
版本: {BOT_VERSION}

Echo 提供在保留您的頭像和名稱的情況下重新傳送訊息的功能。

指令列表
/say [text]
透過 Echo 傳送文字

/enable
啟用 Echo

/disable
停用 Echo

/channel enable
啟用頻道的 Echo 功能

/channel disable
停用頻道的 Echo 功能

/config
管理伺服器的 Echo 設定

提示
透過 Echo 傳送的訊息可以從右鍵 → 應用程式選單中進行「編輯」或「刪除」。
"""

# UIローカライゼーション辞書
UI_TRANSLATIONS = {
    "default_user_setting": {
        "ja": "サーバー内のユーザー有効性設定デフォルト値:",
        "en": "Default user enabled setting for the server:",
        "fr": "Paramètre par défaut d'activation utilisateur pour le serveur :",
        "de": "Standard-Benutzeraktivierungseinstellung für den Server:",
        "ko": "서버 내 사용자 활성화 설정 기본값:",
        "zh": "伺服器內使用者啟用設定預設值:"
    },
    "enabled": {
        "ja": "有効", "en": "Enabled", "fr": "Activé", "de": "Aktiviert", "ko": "활성화", "zh": "啟用"
    },
    "disabled": {
        "ja": "無効", "en": "Disabled", "fr": "Désactivé", "de": "Deaktiviert", "ko": "비활성화", "zh": "停用"
    },
    "channel_setting": {
        "ja": "各チャンネルの有効性:",
        "en": "Channel enabled settings:",
        "fr": "Paramètres d'activation par salon :",
        "de": "Kanalaktivierungseinstellungen:",
        "ko": "채널별 활성화 상태:",
        "zh": "各頻道的啟用狀態:"
    },
    "omitted": {
        "ja": "※チャンネル数が多いため省略されました",
        "en": "*Omitted due to too many channels",
        "fr": "*Omis en raison d'un trop grand nombre de salons",
        "de": "*Wegen zu vieler Kanäle weggelassen",
        "ko": "*채널이 너무 많아 생략되었습니다",
        "zh": "*因頻道數量過多已省略"
    },
    "btn_all_ch_enable": {
        "ja": "全チャンネル有効", "en": "Enable All Channels", "fr": "Activer tous les salons", "de": "Alle Kanäle aktivieren", "ko": "모든 채널 활성화", "zh": "啟用所有頻道"
    },
    "btn_all_ch_disable": {
        "ja": "全チャンネル無効", "en": "Disable All Channels", "fr": "Désactiver tous les salons", "de": "Alle Kanäle deaktivieren", "ko": "모든 채널 비활성화", "zh": "停用所有頻道"
    },
    "btn_user_def_enable": {
        "ja": "デフォルト有効", "en": "Enable User Default", "fr": "Activer par défaut", "de": "Benutzerstandard aktivieren", "ko": "사용자 기본값 활성화", "zh": "啟用使用者預設"
    },
    "btn_user_def_disable": {
        "ja": "デフォルト無効", "en": "Disable User Default", "fr": "Désactiver par défaut", "de": "Benutzerstandard deaktivieren", "ko": "사용자 기본값 비활성화", "zh": "停用使用者預設"
    },
    "select_channel_placeholder": {
        "ja": "設定を切り替えるチャンネルを選択",
        "en": "Select a channel to toggle settings",
        "fr": "Sélectionnez un salon pour basculer les paramètres",
        "de": "Wählen Sie einen Kanal, um die Einstellungen umzuschalten",
        "ko": "설정을 전환할 채널을 선택하세요",
        "zh": "選擇要切換設定的頻道"
    }
}

def get_ui_text(key: str, locale: discord.Locale) -> str:
    lang = "en"
    if locale == discord.Locale.japanese: lang = "ja"
    elif locale == discord.Locale.french: lang = "fr"
    elif locale == discord.Locale.german: lang = "de"
    elif locale == discord.Locale.korean: lang = "ko"
    elif locale in [discord.Locale.taiwan_chinese, discord.Locale.chinese]: lang = "zh"
    
    return UI_TRANSLATIONS.get(key, {}).get(lang, UI_TRANSLATIONS.get(key, {}).get("en", key))

# ログとDB設定
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db'), exist_ok=True)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'echo.db')

logger = logging.getLogger('Echo')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = RotatingFileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'echo'), maxBytes=10*1024*1024, backupCount=1, encoding='utf-8')
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 状態管理用変数
db_conn = None

# データベーススキーマ定義
SCHEMA_TABLES = {
    "global_stats": """CREATE TABLE global_stats (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_message_count INTEGER NOT NULL DEFAULT 0
        )""",
    "users": """CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            last_request_time REAL NOT NULL DEFAULT 0
        )""",
    "guilds": """CREATE TABLE guilds (
            guild_id INTEGER PRIMARY KEY,
            guild_name TEXT,
            default_user_enabled INTEGER NOT NULL DEFAULT 0
        )""",
    "user_guild_settings": """CREATE TABLE user_guild_settings (
            user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            guild_id INTEGER NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
            user_enabled INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )""",
    "channels": """CREATE TABLE channels (
            channel_id INTEGER PRIMARY KEY,
            channel_name TEXT,
            guild_id INTEGER REFERENCES guilds(guild_id) ON DELETE CASCADE,
            channel_enabled INTEGER NOT NULL DEFAULT 0
        )""",
    "message_logs": """CREATE TABLE message_logs (
            message_id INTEGER PRIMARY KEY,
            created_at REAL NOT NULL,
            webhook_id INTEGER NOT NULL,
            is_reply INTEGER NOT NULL DEFAULT 0,
            user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
        )""",
}

SCHEMA_INDEXES = {
    "idx_channels_guild": "CREATE INDEX idx_channels_guild ON channels(guild_id)",
    "idx_message_logs_user": "CREATE INDEX idx_message_logs_user ON message_logs(user_id)",
    "idx_message_logs_created": "CREATE INDEX idx_message_logs_created ON message_logs(created_at)",
}

SCHEMA_TRIGGERS = {
    "trg_message_logs_limit": """CREATE TRIGGER trg_message_logs_limit
        AFTER INSERT ON message_logs
        BEGIN
            DELETE FROM message_logs
            WHERE message_id IN (
                SELECT message_id FROM message_logs
                ORDER BY created_at ASC, message_id ASC
                LIMIT MAX((SELECT COUNT(*) FROM message_logs) - 500000, 0)
            );
        END""",
}

# SQL正規化
def normalize_sql(sql):
    if not sql:
        return ""
    sql = re.sub(r'\bIF\s+NOT\s+EXISTS\b', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\s+', ' ', sql).strip()
    return sql

# 現在のスキーマ取得
async def get_current_schema():
    schema = {"table": {}, "index": {}, "trigger": {}}
    async with db_conn.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE type IN ('table','index','trigger')"
    ) as cursor:
        rows = await cursor.fetchall()
    for type_, name, sql in rows:
        if name.startswith('sqlite_'):
            continue
        schema[type_][name] = sql
    return schema

# スキーマ差分判定
async def schema_matches():
    current = await get_current_schema()
    expected = {
        "table": SCHEMA_TABLES,
        "index": SCHEMA_INDEXES,
        "trigger": SCHEMA_TRIGGERS,
    }
    for type_, defs in expected.items():
        cur = current[type_]
        if set(cur.keys()) != set(defs.keys()):
            return False
        for name, ddl in defs.items():
            if normalize_sql(cur.get(name)) != normalize_sql(ddl):
                return False
    return True

# テーブル再構築
async def migrate_schema():
    await db_conn.commit()
    await db_conn.execute("PRAGMA foreign_keys = OFF;")
    try:
        current = await get_current_schema()
        for name in current["trigger"]:
            await db_conn.execute(f'DROP TRIGGER IF EXISTS "{name}"')
        for name in current["index"]:
            await db_conn.execute(f'DROP INDEX IF EXISTS "{name}"')
        for name in current["table"]:
            if name not in SCHEMA_TABLES:
                await db_conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        for name, ddl in SCHEMA_TABLES.items():
            exists = name in current["table"]
            old_cols = []
            if exists:
                async with db_conn.execute(f'PRAGMA table_info("{name}")') as c:
                    old_cols = [r[1] for r in await c.fetchall()]
                await db_conn.execute(f'ALTER TABLE "{name}" RENAME TO "_old_{name}"')
            await db_conn.execute(ddl)
            if exists:
                async with db_conn.execute(f'PRAGMA table_info("{name}")') as c:
                    new_cols = [r[1] for r in await c.fetchall()]
                common = [col for col in new_cols if col in old_cols]
                if common:
                    cols_csv = ", ".join(f'"{col}"' for col in common)
                    await db_conn.execute(
                        f'INSERT OR IGNORE INTO "{name}" ({cols_csv}) '
                        f'SELECT {cols_csv} FROM "_old_{name}"'
                    )
                await db_conn.execute(f'DROP TABLE IF EXISTS "_old_{name}"')
        for ddl in SCHEMA_INDEXES.values():
            await db_conn.execute(ddl)
        for ddl in SCHEMA_TRIGGERS.values():
            await db_conn.execute(ddl)
        await db_conn.commit()
    except Exception:
        await db_conn.rollback()
        raise
    finally:
        await db_conn.execute("PRAGMA foreign_keys = ON;")

# DB初期化
async def init_db():
    global db_conn
    db_conn = await aiosqlite.connect(DB_PATH)
    await db_conn.execute("PRAGMA journal_mode = WAL;")
    await db_conn.execute("PRAGMA busy_timeout = 5000;")
    await db_conn.execute("PRAGMA foreign_keys = ON;")
    await db_conn.execute("PRAGMA synchronous = NORMAL;")
    if await schema_matches():
        logger.info("データベース更新なし")
    else:
        logger.info("データベース更新開始")
        await migrate_schema()
        logger.info("データベース更新完了")
    await db_conn.execute("""
        INSERT OR IGNORE INTO global_stats (id, total_message_count)
        VALUES (1, 0)
    """)
    await db_conn.commit()

# 権限検証
def has_required_permissions(channel):
    guild = getattr(channel, 'guild', None)
    if guild is None:
        return False

    me = guild.me
    if me is None:
        return False

    perms = channel.permissions_for(me)
    can_send = perms.send_messages_in_threads if isinstance(channel, discord.Thread) else perms.send_messages

    return (
        perms.view_channel and            # チャンネル表示
        perms.read_message_history and    # メッセージ履歴を読む
        perms.manage_messages and         # メッセージ管理
        can_send and                      # メッセージを送る
        perms.embed_links and             # リンク埋め込み
        perms.attach_files and            # ファイル添付
        perms.manage_webhooks             # ウェブフック管理
    )

# クールダウン判定
async def check_cooldown(user_id, user_name):
    current_time = time.time()
    async with db_conn.execute("BEGIN IMMEDIATE"):
        try:
            async with db_conn.execute("SELECT last_request_time FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
            last_request_time = row[0] if row else 0
            time_passed = current_time - last_request_time
            if time_passed < COOLDOWN_SECONDS:
                await db_conn.execute("ROLLBACK")
                return "COOLDOWN", int(COOLDOWN_SECONDS - time_passed)
            
            await db_conn.execute("""
                INSERT INTO users (user_id, user_name, last_request_time)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    user_name = excluded.user_name,
                    last_request_time = excluded.last_request_time
            """, (user_id, user_name, current_time))
            await db_conn.execute("COMMIT")
            return "OK", None
        except Exception as e:
            await db_conn.execute("ROLLBACK")
            logger.error(f"データベースクールダウンチェックエラー: {e}")
            return "ERROR", None

# チャンネル有効性チェック
async def check_enabled_channel(channel_id):
    try:
        async with db_conn.execute(
            "SELECT channel_enabled FROM channels WHERE channel_id = ?", 
            (channel_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        return bool(row[0])
    except Exception as e:
        logger.error(f"データベースチャンネル有効性チェックエラー: {e}")
        return False

# ユーザー有効性チェック
async def check_enabled_user(user_id, guild_id):
    try:
        async with db_conn.execute(
            "SELECT COALESCE((SELECT user_enabled FROM user_guild_settings WHERE user_id = ? AND guild_id = ?), "
            "(SELECT default_user_enabled FROM guilds WHERE guild_id = ?), 0)", 
            (user_id, guild_id, guild_id)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return False
        return bool(row[0])
    except Exception as e:
        logger.error(f"データベースユーザー有効性チェックエラー: {e}")
        return False

# ユーザー設定共通処理
async def set_user_guild_enabled(user, guild, enabled):
    await db_conn.execute(
        "INSERT INTO users (user_id, user_name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET user_name = excluded.user_name",
        (user.id, user.display_name)
    )
    await db_conn.execute(
        "INSERT INTO guilds (guild_id, guild_name) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET guild_name = excluded.guild_name",
        (guild.id, guild.name)
    )
    await db_conn.execute(
        "INSERT INTO user_guild_settings (user_id, guild_id, user_enabled) VALUES (?, ?, ?) ON CONFLICT(user_id, guild_id) DO UPDATE SET user_enabled = excluded.user_enabled",
        (user.id, guild.id, int(enabled))
    )
    await db_conn.commit()

# ログ記録
async def log_webhook_message(message_id, created_at, webhook_id, is_reply, user_id):
    try:
        await db_conn.execute("BEGIN IMMEDIATE")
        await db_conn.execute("""
            INSERT INTO message_logs (message_id, created_at, webhook_id, is_reply, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, created_at, webhook_id, is_reply, user_id))
        await db_conn.execute("UPDATE global_stats SET total_message_count = total_message_count + 1 WHERE id = 1")
        await db_conn.commit()
    except Exception as e:
        await db_conn.rollback()
        logger.error(f"データベースウェブフックメッセージログエラー: {e}")

# Webhook取得または作成
async def get_or_create_webhook(channel):
    if isinstance(channel, discord.Thread):
        target_channel = channel.parent
    else:
        target_channel = channel

    webhooks = await target_channel.webhooks()
    for wh in webhooks:
        if wh.name == WEBHOOK_NAME:
            return wh
            
    return await target_channel.create_webhook(name=WEBHOOK_NAME)

# 文字幅換算
def text_width_conversion(text: str, max_full_width: int) -> str:
    max_half_width = max_full_width * 2
    current_width = 0
    result = ""
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in ('F', 'W', 'A') else 1
        if current_width + char_width > max_half_width:
            break
        result += char
        current_width += char_width
    return result

# Discordクライアント設定
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents, max_messages=MAX_MESSAGES)
tree = app_commands.CommandTree(discord_client)

# スラッシュコマンド　ヘルプ情報
@tree.command(name="help", description="Echoのヘルプ情報を表示します")
async def help_command(interaction: discord.Interaction):
    if interaction.locale == discord.Locale.japanese:
        await interaction.response.send_message(HELP_INFORMATION, ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
    elif interaction.locale == discord.Locale.french:
        await interaction.response.send_message(HELP_INFORMATION_FR, ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
    elif interaction.locale == discord.Locale.german:
        await interaction.response.send_message(HELP_INFORMATION_DE, ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
    elif interaction.locale == discord.Locale.korean:
        await interaction.response.send_message(HELP_INFORMATION_KO, ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
    elif interaction.locale in [discord.Locale.taiwan_chinese, discord.Locale.chinese]:
        await interaction.response.send_message(HELP_INFORMATION_ZH, ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
    else:
        await interaction.response.send_message(HELP_INFORMATION_EN, ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

# スラッシュコマンド　Say
@tree.command(name="say", description="Echoでメッセージを送信します")
@app_commands.describe(text="送信するテキスト")
async def say_command(interaction: discord.Interaction, text: app_commands.Range[str, 1, MAX_MESSAGE_LENGTH]):
    if not has_required_permissions(interaction.channel):
        await interaction.response.send_message("必要な権限が不足しています。Echoは以下のすべての権限がある場合のみ作動します：チャンネル表示、メッセージ履歴を読む、メッセージ管理、メッセージを送る、リンク埋め込み、ファイル添付、ウェブフックを管理", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return
        
    # チャンネル有効性チェック
    if not await check_enabled_channel(interaction.channel_id):
        await interaction.response.send_message("このチャンネルではEchoが無効化されています。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return

    status, remaining = await check_cooldown(interaction.user.id, interaction.user.display_name)
    if status == "COOLDOWN":
        await interaction.response.send_message(f"クールダウン中 (残り {remaining} 秒)", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return
        
    # メッセージログ
    logger.info(f"User Message ({interaction.user.name} - {interaction.user.id}): {text}")

    await interaction.response.defer(ephemeral=True)
    try:
        webhook = await get_or_create_webhook(interaction.channel)
        thread = interaction.channel if isinstance(interaction.channel, discord.Thread) else discord.utils.MISSING
        msg = await webhook.send(
            content=text,
            username=interaction.user.display_name,
            avatar_url=interaction.user.display_avatar.url,
            thread=thread,
            wait=True,
            allowed_mentions=MENTION_RESTRICTION
        )
        await log_webhook_message(msg.id, msg.created_at.timestamp(), webhook.id, 0, interaction.user.id)
        await interaction.delete_original_response()
    except Exception as e:
        logger.error(f"Sayコマンドエラー: {e}")
        await interaction.followup.send("送信に失敗しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

# ユーザー設定コマンド
@tree.command(name="enable", description="Echoを有効化します")
async def user_enable(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("このコマンドはサーバー内でのみ使用できます。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return
    await set_user_guild_enabled(interaction.user, interaction.guild, True)
    await interaction.response.send_message("このサーバーでEchoを有効化しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

@tree.command(name="disable", description="Echoを無効化します")
async def user_disable(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("このコマンドはサーバー内でのみ使用できます。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return
    await set_user_guild_enabled(interaction.user, interaction.guild, False)
    await interaction.response.send_message("このサーバーでEchoを無効化しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

# チャンネル設定グループ
channel_group = app_commands.Group(name="channel", description="チャンネル設定", default_permissions=discord.Permissions(manage_guild=True))

@channel_group.command(name="enable", description="チャンネルのEcho機能を有効化します")
async def channel_enable(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return

    guild_id = interaction.guild_id if interaction.guild else 0
    await db_conn.execute("INSERT OR IGNORE INTO guilds (guild_id, guild_name) VALUES (?, ?)", (guild_id, interaction.guild.name if interaction.guild else ""))
    await db_conn.execute("INSERT INTO channels (channel_id, channel_name, guild_id, channel_enabled) VALUES (?, ?, ?, 1) ON CONFLICT(channel_id) DO UPDATE SET channel_enabled = 1", (interaction.channel_id, interaction.channel.name, guild_id))
    await db_conn.commit()
    await interaction.response.send_message("このチャンネルのEcho機能を有効化しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

@channel_group.command(name="disable", description="チャンネルのEcho機能を無効化します")
async def channel_disable(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return

    guild_id = interaction.guild_id if interaction.guild else 0
    await db_conn.execute("INSERT OR IGNORE INTO guilds (guild_id, guild_name) VALUES (?, ?)", (guild_id, interaction.guild.name if interaction.guild else ""))
    await db_conn.execute("INSERT INTO channels (channel_id, channel_name, guild_id, channel_enabled) VALUES (?, ?, ?, 0) ON CONFLICT(channel_id) DO UPDATE SET channel_enabled = 0", (interaction.channel_id, interaction.channel.name, guild_id))
    await db_conn.commit()
    await interaction.response.send_message("このチャンネルのEcho機能を無効化しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

tree.add_command(channel_group)

# コンテキストメニュー　メッセージ編集
class EditModal(discord.ui.Modal, title='メッセージを編集'):
    content = discord.ui.TextInput(label='内容', style=discord.TextStyle.paragraph, max_length=MAX_MESSAGE_LENGTH, required=True)

    def __init__(self, message: discord.Message, webhook: discord.Webhook):
        super().__init__()
        self.message = message
        self.webhook = webhook
        self.content.default = message.content

    async def on_submit(self, interaction: discord.Interaction):
        new_content = self.content.value[:MAX_MESSAGE_LENGTH]
        try:
            thread = interaction.channel if isinstance(interaction.channel, discord.Thread) else discord.utils.MISSING
            await self.webhook.edit_message(self.message.id, content=new_content, thread=thread, allowed_mentions=MENTION_RESTRICTION)
            await interaction.response.defer()
        except Exception as e:
            logger.error(f"ウェブフックメッセージ編集エラー: {e}")
            await interaction.response.send_message("編集に失敗しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

@tree.context_menu(name="メッセージを編集")
async def edit_message_menu(interaction: discord.Interaction, message: discord.Message):
    async with db_conn.execute("SELECT user_id, webhook_id FROM message_logs WHERE message_id = ?", (message.id,)) as cursor:
        row = await cursor.fetchone()
    
    if not row or row[0] != interaction.user.id:
        await interaction.response.send_message("このメッセージを編集する権限がありません。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return
        
    try:
        webhook = await discord_client.fetch_webhook(row[1])
        await interaction.response.send_modal(EditModal(message, webhook))
    except Exception as e:
        logger.error(f"編集用ウェブフック取得エラー: {e}")
        await interaction.response.send_message("メッセージの取得に失敗しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

# コンテキストメニュー　メッセージ削除
@tree.context_menu(name="メッセージを削除")
async def delete_message_menu(interaction: discord.Interaction, message: discord.Message):
    async with db_conn.execute("SELECT user_id, webhook_id FROM message_logs WHERE message_id = ?", (message.id,)) as cursor:
        row = await cursor.fetchone()
        
    if not row or row[0] != interaction.user.id:
        await interaction.response.send_message("このメッセージを削除する権限がありません。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return
        
    await interaction.response.defer(ephemeral=True)
    try:
        webhook = await discord_client.fetch_webhook(row[1])
        thread = interaction.channel if isinstance(interaction.channel, discord.Thread) else discord.utils.MISSING
        await webhook.delete_message(message.id, thread=thread)
        await interaction.delete_original_response()
    except Exception as e:
        logger.error(f"ウェブフックメッセージ削除エラー: {e}")
        await interaction.followup.send("削除に失敗しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

# コンテキストメニュー　ユーザーのEcho有効化
@tree.context_menu(name="Echoを有効化")
async def enable_user_menu(interaction: discord.Interaction, user: discord.User):
    if interaction.guild is None:
        await interaction.response.send_message("このメニューはサーバー内でのみ使用できます。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return

    is_self = interaction.user.id == user.id
    has_perm = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild

    if not (is_self or has_perm):
        await interaction.response.send_message("このユーザーの設定を変更する権限がありません。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return

    await set_user_guild_enabled(user, interaction.guild, True)
    await interaction.response.send_message(f"{user.display_name} のこのサーバーでのEchoを有効化しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)


# コンテキストメニュー　ユーザーのEcho無効化
@tree.context_menu(name="Echoを無効化")
async def disable_user_menu(interaction: discord.Interaction, user: discord.User):
    if interaction.guild is None:
        await interaction.response.send_message("このメニューはサーバー内でのみ使用できます。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return

    is_self = interaction.user.id == user.id
    has_perm = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild

    if not (is_self or has_perm):
        await interaction.response.send_message("このユーザーの設定を変更する権限がありません。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return

    await set_user_guild_enabled(user, interaction.guild, False)
    await interaction.response.send_message(f"{user.display_name} のこのサーバーでのEchoを無効化しました。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

# スラッシュコマンド　コンフィグ
class ConfigView(discord.ui.View):
    def __init__(self, guild: discord.Guild, locale: discord.Locale):
        super().__init__(timeout=None)
        self.guild_id = guild.id
        self.locale = locale
        
        self.btn_channels_enable.label = get_ui_text("btn_all_ch_enable", locale)
        self.btn_channels_disable.label = get_ui_text("btn_all_ch_disable", locale)
        self.btn_user_def_enable.label = get_ui_text("btn_user_def_enable", locale)
        self.btn_user_def_disable.label = get_ui_text("btn_user_def_disable", locale)
        
        self.select_channel.placeholder = get_ui_text("select_channel_placeholder", locale)

        if len(guild.text_channels) > 15:
            self.remove_item(self.select_channel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message("この操作を行う権限がありません。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return False

    async def generate_content(self, interaction: discord.Interaction):
        async with db_conn.execute("SELECT default_user_enabled FROM guilds WHERE guild_id = ?", (self.guild_id,)) as cursor:
            row = await cursor.fetchone()
        default_user_enabled = bool(row[0]) if row else False

        async with db_conn.execute("SELECT channel_id, channel_enabled FROM channels WHERE guild_id = ?", (self.guild_id,)) as cursor:
            channels = await cursor.fetchall()
        
        channel_dict = {c[0]: bool(c[1]) for c in channels}

        txt_def = get_ui_text("default_user_setting", self.locale)
        txt_enabled = get_ui_text("enabled", self.locale)
        txt_disabled = get_ui_text("disabled", self.locale)
        txt_ch = get_ui_text("channel_setting", self.locale)
        txt_omit = get_ui_text("omitted", self.locale)

        content = f"**{txt_def}** {txt_enabled if default_user_enabled else txt_disabled}\n\n"
        content += f"**{txt_ch}**\n"
        
        if interaction.guild:
            for channel in interaction.guild.text_channels:
                is_enabled = channel_dict.get(channel.id, False)
                ch_name = channel.name[:CONFIG_CHANNEL_NAME_LENGTH]
                if len(channel.name) > CONFIG_CHANNEL_NAME_LENGTH:
                    ch_name += "..."
                
                status_text = f"**{txt_enabled}**" if is_enabled else txt_disabled
                line = f"{ch_name}: {status_text}\n"
                
                if len(content) + len(line) > 1900:
                    content += f"{txt_omit}\n"
                    break
                content += line
        
        return content

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="設定を切り替えるチャンネルを選択", min_values=1, max_values=1, row=0)
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        selected_channel = select.values[0]
        
        async with db_conn.execute("SELECT channel_enabled FROM channels WHERE channel_id = ?", (selected_channel.id,)) as cursor:
            row = await cursor.fetchone()
        
        current_status = bool(row[0]) if row else False
        new_status = 0 if current_status else 1
        
        await db_conn.execute(
            "INSERT INTO channels (channel_id, channel_name, guild_id, channel_enabled) VALUES (?, ?, ?, ?) ON CONFLICT(channel_id) DO UPDATE SET channel_enabled = ?",
            (selected_channel.id, selected_channel.name, self.guild_id, new_status, new_status)
        )
        await db_conn.commit()
        
        content = await self.generate_content(interaction)
        await interaction.response.edit_message(content=content, view=self, allowed_mentions=MENTION_RESTRICTION)

    @discord.ui.button(style=discord.ButtonStyle.success, custom_id="config_channels_enable", row=1)
    async def btn_channels_enable(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild:
            for channel in interaction.guild.text_channels:
                await db_conn.execute(
                    "INSERT INTO channels (channel_id, channel_name, guild_id, channel_enabled) VALUES (?, ?, ?, 1) ON CONFLICT(channel_id) DO UPDATE SET channel_enabled = 1",
                    (channel.id, channel.name, self.guild_id)
                )
            await db_conn.commit()
            content = await self.generate_content(interaction)
            await interaction.response.edit_message(content=content, view=self, allowed_mentions=MENTION_RESTRICTION)

    @discord.ui.button(style=discord.ButtonStyle.danger, custom_id="config_channels_disable", row=1)
    async def btn_channels_disable(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild:
            for channel in interaction.guild.text_channels:
                await db_conn.execute(
                    "INSERT INTO channels (channel_id, channel_name, guild_id, channel_enabled) VALUES (?, ?, ?, 0) ON CONFLICT(channel_id) DO UPDATE SET channel_enabled = 0",
                    (channel.id, channel.name, self.guild_id)
                )
            await db_conn.commit()
            content = await self.generate_content(interaction)
            await interaction.response.edit_message(content=content, view=self, allowed_mentions=MENTION_RESTRICTION)

    @discord.ui.button(style=discord.ButtonStyle.success, custom_id="config_user_def_enable", row=2)
    async def btn_user_def_enable(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db_conn.execute(
            "INSERT INTO guilds (guild_id, guild_name, default_user_enabled) VALUES (?, ?, 1) ON CONFLICT(guild_id) DO UPDATE SET default_user_enabled = 1",
            (self.guild_id, interaction.guild.name if interaction.guild else "")
        )
        await db_conn.commit()
        content = await self.generate_content(interaction)
        await interaction.response.edit_message(content=content, view=self, allowed_mentions=MENTION_RESTRICTION)

    @discord.ui.button(style=discord.ButtonStyle.danger, custom_id="config_user_def_disable", row=2)
    async def btn_user_def_disable(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db_conn.execute(
            "INSERT INTO guilds (guild_id, guild_name, default_user_enabled) VALUES (?, ?, 0) ON CONFLICT(guild_id) DO UPDATE SET default_user_enabled = 0",
            (self.guild_id, interaction.guild.name if interaction.guild else "")
        )
        await db_conn.commit()
        content = await self.generate_content(interaction)
        await interaction.response.edit_message(content=content, view=self, allowed_mentions=MENTION_RESTRICTION)

@tree.command(name="config", description="サーバーのEcho設定を管理します")
@app_commands.default_permissions(manage_guild=True)
async def config_command(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("このコマンドはサーバー内でのみ使用できます。", ephemeral=True, allowed_mentions=MENTION_RESTRICTION)
        return
    
    await db_conn.execute("INSERT OR IGNORE INTO guilds (guild_id, guild_name) VALUES (?, ?)", (interaction.guild.id, interaction.guild.name))
    await db_conn.commit()

    view = ConfigView(interaction.guild, interaction.locale)
    content = await view.generate_content(interaction)
    await interaction.response.send_message(content=content, view=view, ephemeral=True, allowed_mentions=MENTION_RESTRICTION)

# イベント　準備完了
@discord_client.event
async def on_ready():
    logger.info(f'{discord_client.user} logged in.')

# イベント　メッセージ受信
@discord_client.event
async def on_message(message):
    if message.author.bot:
        return

    # デバッグコマンド
    if discord_client.user in message.mentions and '..debug' in message.content:
        if message.author.id == MASTER_USER_ID:
            await message.reply(DEBUG_INFORMATION, allowed_mentions=MENTION_RESTRICTION)
        return

    # 無視プレフィックス
    if message.content.strip().startswith(PREFIX_IGNORE):
        return

    # URLチェック
    if re.search(GENERAL_URL_PATTERN, message.content):
        return

    # アタッチメントチェック
    if message.attachments:
        return

    # オンサーバーチェック
    if not message.guild:
        return

    # 権限チェック
    if not has_required_permissions(message.channel):
        return

    # チャンネル有効性チェック
    if not await check_enabled_channel(message.channel.id):
        return

    # ユーザー有効性チェック
    if not await check_enabled_user(message.author.id, message.guild.id):
        return

    # クールダウンチェック
    status, _ = await check_cooldown(message.author.id, message.author.display_name)
    if status != "OK":
        if DELETE_ON_COOLDOWN:
            try:
                await message.delete()
            except Exception as e:
                logger.error(f"クールダウンメッセージ削除エラー: {e}")
        return

    # メッセージログ
    logger.info(f"User Message ({message.author.name} - {message.author.id}): {message.content}")

    # 処理開始
    content = message.content[:MAX_MESSAGE_LENGTH]
    
    # 返信処理
    is_reply = 0
    if message.reference and message.reference.message_id:
        try:
            ref_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
            
            mention = ref_msg.author.mention
            ref_content = ref_msg.content
            
            if ref_msg.webhook_id:
                async with db_conn.execute("SELECT user_id, is_reply FROM message_logs WHERE message_id = ?", (ref_msg.id,)) as cursor:
                    row = await cursor.fetchone()
                if row:
                    mention = f"<@{row[0]}>"
                    if row[1] == 1:
                        if '\n' in ref_content:
                            ref_content = ref_content.split('\n', 1)[1]
                        else:
                            ref_content = ""
            
            clean_ref_content = re.sub(r'<@[^>]+>', '', ref_content)
            clean_ref_content = re.sub(r'\[.*?\]', '', clean_ref_content)
            clean_ref_content = re.sub(r'\s+', ' ', clean_ref_content).strip()
            clean_ref_content = re.sub(r'https?://', '', clean_ref_content, count=1)
            
            clean_ref_content = clean_ref_content.replace('[', '').replace(']', '').replace('<', '').replace('>', '')
            
            if not clean_ref_content:
                display_text = "メッセージ" # 画像のみなどテキストがない場合の代替
            else:
                truncated_text = text_width_conversion(clean_ref_content, REPLY_PREVIEW_LENGTH)
                if len(clean_ref_content) > len(truncated_text):
                    display_text = truncated_text + "..."
                else:
                    display_text = truncated_text
                
            content = f"> {mention} [>{display_text}](<{ref_msg.jump_url}>)\n{content}"
            content = content[:MAX_MESSAGE_LENGTH]
            
            is_reply = 1 
            
        except Exception as e:
            logger.error(f"返信処理エラー: {e}")

    # 空メッセージ防止
    if not content:
        return

    # オリジナルメッセージ削除
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"オリジナルメッセージ削除エラー: {e}")

    # Webhook送信
    webhook = await get_or_create_webhook(message.channel)
    thread = message.channel if isinstance(message.channel, discord.Thread) else discord.utils.MISSING
    
    for attempt in range(2):
        try:
            sent_msg = await webhook.send(
                content=content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                thread=thread,
                wait=True,
                allowed_mentions=MENTION_RESTRICTION
            )
            
            await log_webhook_message(sent_msg.id, sent_msg.created_at.timestamp(), webhook.id, is_reply, message.author.id)
            break
            
        except Exception as e:
            if attempt == 1:
                logger.error(f"ウェブフック送信エラー: {e}")
            else:
                await asyncio.sleep(1)

# ローカライゼーション
class CommandTranslator(app_commands.Translator):
    async def translate(self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext) -> str | None:
        if locale in (discord.Locale.american_english, discord.Locale.british_english):
            translations = {
                "Echoのヘルプ情報を表示します": "Displays help information for Echo",
                "Echoでメッセージを送信します": "Sends a single message via Echo",
                "送信するテキスト": "Text to send",
                "Echoを有効化します": "Enables Echo",
                "Echoを無効化します": "Disables Echo",
                "チャンネル設定": "Channel settings",
                "チャンネルのEcho機能を有効化します": "Enables Echo for this channel",
                "チャンネルのEcho機能を無効化します": "Disables Echo for this channel",
                "メッセージを編集": "Edit Message",
                "メッセージを削除": "Delete Message",
                "Echoを有効化": "Enable Echo",
                "Echoを無効化": "Disable Echo",
                "サーバーのEcho設定を管理します": "Manage Echo settings for the server"
            }
            return translations.get(string.message)
            
        elif locale == discord.Locale.french:
            translations = {
                "Echoのヘルプ情報を表示します": "Affiche les informations d'aide pour Echo",
                "Echoでメッセージを送信します": "Envoie un message unique via Echo",
                "送信するテキスト": "Texte à envoyer",
                "Echoを有効化します": "Active Echo",
                "Echoを無効化します": "Désactive Echo",
                "チャンネル設定": "Paramètres du salon",
                "チャンネルのEcho機能を有効化します": "Active la fonctionnalité Echo pour ce salon",
                "チャンネルのEcho機能を無効化します": "Désactive la fonctionnalité Echo pour ce salon",
                "メッセージを編集": "Éditer le message",
                "メッセージを削除": "Supprimer le message",
                "Echoを有効化": "Activer Echo",
                "Echoを無効化": "Désactiver Echo",
                "サーバーのEcho設定を管理します": "Gérer les paramètres d'Echo pour le serveur"
            }
            return translations.get(string.message)
            
        elif locale == discord.Locale.german:
            translations = {
                "Echoのヘルプ情報を表示します": "Zeigt Hilfeinformationen für Echo an",
                "Echoでメッセージを送信します": "Sendet eine einzelne Nachricht über Echo",
                "送信するテキスト": "Zu sendender Text",
                "Echoを有効化します": "Aktiviert Echo",
                "Echoを無効化します": "Deaktiviert Echo",
                "チャンネル設定": "Kanaleinstellungen",
                "チャンネルのEcho機能を有効化します": "Aktiviert die Echo-Funktion für diesen Kanal",
                "チャンネルのEcho機能を無効化します": "Deaktiviert die Echo-Funktion für diesen Kanal",
                "メッセージを編集": "Nachricht bearbeiten",
                "メッセージを削除": "Nachricht löschen",
                "Echoを有効化": "Echo aktivieren",
                "Echoを無効化": "Echo deaktivieren",
                "サーバーのEcho設定を管理します": "Echo-Einstellungen für den Server verwalten"
            }
            return translations.get(string.message)
            
        elif locale == discord.Locale.korean:
            translations = {
                "Echoのヘルプ情報を表示します": "Echo의 도움말 정보를 표시합니다",
                "Echoでメッセージを送信します": "Echo으로 단일 메시지를 전송합니다",
                "送信するテキスト": "전송할 텍스트",
                "Echoを有効化します": "Echo를 활성화합니다",
                "Echoを無効化します": "Echo를 비활성화합니다",
                "チャンネル設定": "채널 설정",
                "チャンネルのEcho機能を有効化します": "채널의 Echo 기능을 활성화합니다",
                "チャンネルのEcho機能を無効化します": "채널의 Echo 기능을 비활성화합니다",
                "メッセージを編集": "메시지 편집",
                "メッセージを削除": "메시지 삭제",
                "Echoを有効化": "Echo 활성화",
                "Echoを無効化": "Echo 비활성화",
                "サーバーのEcho設定を管理します": "서버의 Echo 설정을 관리합니다"
            }
            return translations.get(string.message)
            
        elif locale in (discord.Locale.taiwan_chinese, discord.Locale.chinese):
            translations = {
                "Echoのヘルプ情報を表示します": "顯示 Echo 的幫助資訊",
                "Echoでメッセージを送信します": "透過 Echo 傳送單則訊息",
                "送信するテキスト": "要傳送的文字",
                "Echoを有効化します": "啟用 Echo",
                "Echoを無効化します": "停用 Echo",
                "チャンネル設定": "頻道設定",
                "チャンネルのEcho機能を有効化します": "啟用此頻道的 Echo 功能",
                "チャンネルのEcho機能を無効化します": "停用此頻道的 Echo 功能",
                "メッセージを編集": "編輯訊息",
                "メッセージを削除": "刪除訊息",
                "Echoを有効化": "啟用 Echo",
                "Echoを無効化": "停用 Echo",
                "サーバーのEcho設定を管理します": "管理伺服器的 Echo 設定"
            }
            return translations.get(string.message)
            
        return None

@discord_client.event
async def setup_hook():
    await init_db()
    await tree.set_translator(CommandTranslator())
    await tree.sync()

original_close = discord_client.close

async def close_client():
    global db_conn
    if db_conn:
        await db_conn.close()
        logger.info("データベース切断完了")
    await original_close()

discord_client.close = close_client

if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
