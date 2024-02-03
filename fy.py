import yaml
import logging
import time
import re
from telethon.sync import TelegramClient
from telethon import events
from openai import OpenAI

# 设置日志记录。
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 尝试读取配置文件。
try:
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
except Exception as e:
    logging.error(f"Failed to load config file: {e}")
    exit(1)

# 提取配置信息。
api_id = config['telegram']['api_id']
api_hash = config['telegram']['api_hash']
session_name = config['telegram']['session_name']
api_key = config['openai']['api_key']
base_url = config['openai']['base_url']
target_users = config['target_users']
target_groups = config['target_groups']

# 初始化客户端。
client = TelegramClient(session_name, api_id, api_hash)
openai_client = OpenAI(api_key=api_key, base_url=base_url)

# 默认使用的模型。
current_model = "coze"

# 辅助函数。
def contains_chinese(text):
    return any('\u4e00' <= character <= '\u9fff' for character in text)

def is_pure_url(text):
    url_pattern = r'^\s*http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+\s*$'
    return re.match(url_pattern, text) is not None

# 翻译函数，使用当前模型。
def translate_text(text, target_language):
    response = openai_client.chat.completions.create(
        model=current_model,
        messages=[
            {"role": "system", "content": "You are a translation engine, only returning translated answers."},
            {"role": "user", "content": f"Translate the text to {target_language} please do not explain my original text, do not explain the translation results, Do not explain the context.:\n{text}"}
        ]
    )
    translated_text = response.choices[0].message.content
    return translated_text

# 处理命令以切换模型。
@client.on(events.NewMessage(pattern='/fymodel'))
async def change_model(event):
    global current_model
    # 分割命令文本以提取模型名称。
    parts = event.raw_text.split(maxsplit=1)
    if len(parts) > 1:
        model_name = parts[1]
        current_model = model_name
        await event.reply(f"翻译模型已切换至: {current_model}")
    else:
        await event.reply("请指定要切换的模型名称。")


# 监听新消息事件，进行消息处理。
@client.on(events.NewMessage)
async def handle_message(event):
    if event.chat_id not in target_groups and event.sender_id not in target_users:
        return  # 如果消息不是来自目标用户或群组，则忽略
    start_time = time.time()  # 记录开始时间
    try:
        message = event.message

        # 跳过空文本或非文本消息。
        if not message.text or message.text.strip() == "":
            return

        # 跳过仅包含链接的消息。
        if is_pure_url(message.text):
            return

        # 记录来自target_users的消息和你自己发出去的消息为log。
        if (message.chat_id in target_users or (message.sender_id in target_users and event.is_group)) or message.out:
            logging.info(f"原文: {message.text}")

        # 对特定用户/群聊的消息进行翻译。
        if (message.chat_id in target_users or (message.sender_id in target_users and event.is_group)) and not message.out:
            if contains_non_chinese(message.text):
                # 如果消息只包含链接，跳过翻译。
                if is_pure_url(message.text):
                    pass
                # 如果消息不只包含链接，进行翻译。
                else:
                    translated_text = translate_text(message.text, "zh_CN")  
                    if translated_text and contains_chinese(translated_text):
                        modified_message = f"**{translated_text}**"
                        await client.send_message(entity=message.chat_id, message=modified_message, reply_to=message.id)
                end_time = time.time()  # 记录结束时间
                logging.info(f"翻译总耗时：{end_time - start_time}秒")  # 记录并打印翻译耗时
                logging.info(f"引用并翻译成功，已回复：\n{modified_message}")

        # 对自己在特定群聊发送的中文消息进行英文翻译。
        elif message.out and message.chat_id in target_groups:
            if contains_chinese(message.text):
                translated_text = translate_text(message.text, "English")  
                if translated_text:
                    # 修改原消息，添加英文翻译。
                    modified_message = f"{message.text}\n{translated_text}"
                    await message.edit(modified_message)
                    end_time = time.time()  # 记录结束时间
                    logging.info(f"翻译总耗时：{end_time - start_time}秒")  # 记录并打印翻译耗时
                    logging.info(f"消息编辑成功，新消息：\n{modified_message}")

    except Exception as e:
        # 记录处理消息时发生的异常。
        logging.error(f"Error handling message: {e}")

# 启动客户端。
try:
    client.start()
    client.run_until_disconnected()
finally:
    client.disconnect()
