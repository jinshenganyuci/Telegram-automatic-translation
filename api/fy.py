﻿from telethon.sync import TelegramClient
from telethon import events
from openai import OpenAI
import emoji

# 设置API key 和 base URL
api_key = "sk-GTOUkESeByYkwBg634Db5fCa04Fc41BaBb712c82F09aE438"
base_url = "http://127.0.0.1:3000/v1"
openai = OpenAI(api_key=api_key, base_url=base_url)

# Telegram 登录信息
api_id = 11098080
api_hash = "943bb3e8dbc814b3c0eff350db4d6418"

# 创建Telegram客户端
client = TelegramClient('session_name', api_id, api_hash)

# 登录Telegram
client.start()

# 定义特定的人的用户名或ID列表
target_users = [818882954,-1001989872538]  # 将需要监听的用户的Chat ID添加到列表中

# 翻译函数
async def translate_message(message, to_language, role):
    chat_completion = openai.chat.completions.create(
        messages=[
            {
                "role": role,
                "content": f"Translate the text to {{{to_language}}} Language:\n{message}",
            }
        ],
        model="gpt-3.5-turbo-0613",
    )
    return chat_completion.choices[0].message.content.strip()

# 监听消息事件
@client.on(events.NewMessage)
async def handle_message(event):
    # 获取消息内容
    message = event.message

    # 判断消息是否为空或只包含 Emoji 表情
    if not message.text or (not any(char.isalnum() for char in message.text) and emoji.emoji_count(message.text) == len(message.text)):
        # 如果消息为空，只包含 Emoji 表情，直接返回，不进行翻译
        return
	# 判断消息是否为中文并由别人发送的
    if any('\u4e00' <= char <= '\u9fff' for char in message.text) and not message.out:
        # 如果消息包含中文并且是别人发送的，直接返回，不进行翻译
        return

    # 判断消息是否为特定用户发送的
    if message.sender_id in target_users:
        # 调用 OpenAI 进行翻译
        translated_text = await translate_message(message.text, "zh_CN", "user")

        # 修改原始消息为翻译后的内容格式为 "引用回复译文"
        modified_message = f"**{translated_text}**"

        # 发送修改后的消息
        await client.send_message(entity=message.chat_id, message=modified_message, reply_to=message.id)

    # 判断消息是否为空或只包含 Emoji 表情或没有中文字符
    if not message.text or (not any(char.isalnum() for char in message.text) and emoji.emoji_count(message.text) == len(message.text)) or not any('\u4e00' <= char <= '\u9fff' for char in message.text):
        # 如果消息为空，只包含 Emoji 表情，或没有中文字符，直接返回，不进行翻译
        return

    # 判断消息是否为别人发送的
    if message.out:
        # 调用 OpenAI 进行翻译
        translated_text = await translate_message(message.text, "en", "user")

        # 修改原始消息为翻译后的内容格式为 "原文\n译文"
        modified_message = f"{message.text}\n{translated_text}"

        # 发送修改后的消息
        await message.edit(modified_message)

# 开始监听消息
client.run_until_disconnected()
