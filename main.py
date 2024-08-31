import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime

# 执行开始时间
timestart = datetime.now()
print(f"time: {datetime.now().strftime('%Y%m%d_%H_%M_%S')}")

# 读取demo.txt文件内的频道列表
def read_channels_from_demo(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# 读取文本文件为数组
def read_txt_to_array(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# 黑名单读取
def read_blacklist_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        BlackList = [line.split(',')[1].strip() for line in lines if ',' in line]
        return BlackList
    except Exception as e:
        print(f"An error occurred while reading blacklist: {e}")
        return []

blacklist_auto = read_blacklist_from_txt('blacklist/blacklist_auto.txt')
blacklist_manual = read_blacklist_from_txt('blacklist/blacklist_manual.txt')
combined_blacklist = set(blacklist_auto + blacklist_manual)

# 读取可用频道
valid_channels = set(read_channels_from_demo('demo.txt'))

# 定义多个对象用于存储不同内容的行文本
channel_dict = {}

def process_name_string(input_str):
    parts = input_str.split(',')
    processed_parts = []
    for part in parts:
        processed_part = process_part(part)
        processed_parts.append(processed_part)
    result_str = ','.join(processed_parts)
    return result_str

def process_part(part_str):
    if "CCTV" in part_str and "://" not in part_str:
        part_str = part_str.replace("IPV6", "")
        part_str = part_str.replace("PLUS", "+")
        part_str = part_str.replace("1080", "")
        filtered_str = ''.join(char for char in part_str if char.isdigit() or char == 'K' or char == '+')
        if not filtered_str.strip():
            filtered_str = part_str.replace("CCTV", "")

        if len(filtered_str) > 2 and re.search(r'4K|8K', filtered_str):
            filtered_str = re.sub(r'(4K|8K).*', r'\1', filtered_str)
            if len(filtered_str) > 2:
                filtered_str = re.sub(r'(4K|8K)', r'(\1)', filtered_str)

        return "CCTV" + filtered_str
    elif "卫视" in part_str:
        pattern = r'卫视「.*」'
        result_str = re.sub(pattern, '卫视', part_str)
        return result_str

    return part_str

def get_url_file_extension(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = os.path.splitext(path)[1]
    return extension

def convert_m3u_to_txt(m3u_content):
    lines = m3u_content.split('\n')
    txt_lines = []
    channel_name = ""

    for line in lines:
        if line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            channel_name = line.split(',')[-1].strip()
        elif line.startswith("http") or line.startswith("rtmp") or line.startswith("p3p"):
            txt_lines.append(f"{channel_name},{line.strip()}")

    return '\n'.join(txt_lines)

def check_url_existence(data_list, url):
    urls = [item.split(',')[1] for item in data_list]
    return url not in urls

def clean_url(url):
    last_dollar_index = url.rfind('$')
    if last_dollar_index != -1:
        return url[:last_dollar_index]
    return url

def process_channel_line(line, channel_dict):
    if "#genre#" not in line and "," in line and "://" in line:
        channel_name, channel_address = line.split(',', 1)
        channel_address = clean_url(channel_address.strip())
        line = f"{channel_name},{channel_address}"

        if channel_address not in combined_blacklist and check_url_existence(channel_dict.get(channel_name, []), channel_address):
            channel_dict.setdefault(channel_name, []).append(process_name_string(line.strip()))

def process_url(url, channel_dict):
    try:
        other_lines = channel_dict.setdefault("其他频道", [])
        other_lines.append("◆◆◆　" + url)
        with urllib.request.urlopen(url) as response:
            data = response.read()
            text = data.decode('utf-8')

            if get_url_file_extension(url) == ".m3u" or get_url_file_extension(url) == ".m3u8":
                text = convert_m3u_to_txt(text)

            lines = text.split('\n')
            print(f"行数: {len(lines)}")
            for line in lines:
                if "#genre#" not in line and "," in line and "://" in line:
                    channel_name, channel_address = line.split(',', 1)
                    if "#" not in channel_address:
                        process_channel_line(line, channel_dict)
                    else:
                        url_list = channel_address.split('#')
                        for channel_url in url_list:
                            newline = f'{channel_name},{channel_url}'
                            process_channel_line(newline, channel_dict)

            other_lines.append('\n')

    except Exception as e:
        print(f"处理URL时发生错误：{e}")

# 主执行流程
urls = read_txt_to_array('assets/urls-daily.txt')

# 处理
for url in urls:
    print(f"处理URL: {url}")
    process_url(url, channel_dict)  # 确保在这里传递了 channel_dict

# 合并所有对象中的行文本（去重，排序后拼接）
version = datetime.now().strftime("%Y%m%d-%H-%M-%S") + ",url"
all_lines = ["更新时间,#genre#"] + [version] + ['\n']

# 根据demo.txt列表内的频道构建最终输出
for channel in valid_channels:
    if channel in channel_dict:
        channel_header = [f"{channel},#genre#"]
        sorted_lines = sorted(set(channel_dict[channel]))
        all_lines += channel_header + sorted_lines + ['\n']

# 输出结果到文件
output_file = "merged_output.txt"
others_file = "others_output.txt"
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in all_lines:
            f.write(line + '\n')
    print(f"合并后的文本已保存到文件: {output_file}")

    with open(others_file, 'w', encoding='utf-8') as f:
        for line in channel_dict.get("其他频道", []):
            f.write(line + '\n')
    print(f"Others已保存到文件: {others_file}")

except Exception as e:
    print(f"保存文件时发生错误：{e}")

# 执行结束时间
timeend = datetime.now()

# 计算时间差
elapsed_time = timeend - timestart
total_seconds = elapsed_time.total_seconds()
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)

# 格式化开始和结束时间
timestart_str = timestart.strftime("%Y%m%d_%H_%M_%S")
timeend_str = timeend.strftime("%Y%m%d_%H_%M_%S")

print(f"开始时间: {timestart_str}")
print(f"结束时间: {timeend_str}")
print(f"执行时间: {minutes} 分 {seconds} 秒")

combined_blacklist_hj = len(combined_blacklist)
all_lines_hj = len(all_lines)
other_lines_hj = len(channel_dict.get("其他频道", []))
print(f"blacklist行数: {combined_blacklist_hj} ")
print(f"merged_output.txt行数: {all_lines_hj} ")
print(f"others_output.txt行数: {other_lines_hj} ")
