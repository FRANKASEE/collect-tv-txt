import urllib.request
from urllib.parse import urlparse
import re  # 正则
import os
from datetime import datetime
import asyncio  # 添加 asyncio 导入

# 执行开始时间
timestart = datetime.now()
# 报时
print(f"time: {datetime.now().strftime('%Y%m%d_%H_%M_%S')}")

# 读取文本方法
def read_txt_to_array(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines]
            return lines
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# 读取黑名单
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

# 定义多个对象用于存储不同内容的行文本
ys_lines = []  # CCTV
ws_lines = []  # 卫视频道
ty_lines = []  # 体育频道
dy_lines = []  # 收藏台
gat_lines = []  # 港澳台
other_lines = []  # 其他频道

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
        part_str = part_str.replace("IPV6", "")  # 先剔除IPV6字样
        part_str = part_str.replace("PLUS", "+")  # 替换PLUS
        part_str = part_str.replace("1080", "")  # 替换1080
        filtered_str = ''.join(char for char in part_str if char.isdigit() or char == 'K' or char == '+')
        if not filtered_str.strip():  # 处理特殊情况，如果发现没有找到频道数字返回原名称
            filtered_str = part_str.replace("CCTV", "")

        if len(filtered_str) > 2 and re.search(r'4K|8K', filtered_str):  # 特殊处理CCTV中部分4K和8K名称
            filtered_str = re.sub(r'(4K|8K).*', r'\1', filtered_str)
            if len(filtered_str) > 2:
                filtered_str = re.sub(r'(4K|8K)', r'(\1)', filtered_str)

        return "CCTV" + filtered_str

    elif "卫视" in part_str:
        pattern = r'卫视「.*」'
        result_str = re.sub(pattern, '卫视', part_str)
        return result_str

    return part_str

# 测试延迟并排序
async def measure_streams_live_streams(urls):
    delays = []
    for url in urls:
        try:
            start_time = datetime.now()
            with urllib.request.urlopen(url) as response:
                response.read()  # 读取数据
            delay = (datetime.now() - start_time).total_seconds()
            delays.append(delay)
        except Exception as e:
            print(f"Error measuring delay for {url}: {e}")
            delays.append(float('inf'))  # 如果出错，延迟设为无穷大
    return delays

def is_ipv6(url):
    return ':' in urlparse(url).hostname  # 简单判断是否为IPv6

def get_resolution(url):
    # 假设有一个函数可以获取分辨率，这里返回一个默认值
    return 1080  # 示例返回值

# 处理URL
async def process_url(url):
    try:
        other_lines.append("◆◆◆　" + url)
        with urllib.request.urlopen(url) as response:
            data = response.read()
            text = data.decode('utf-8')

            lines = text.split('\n')
            print(f"行数: {len(lines)}")
            for line in lines:
                if "#genre#" not in line and "," in line and "://" in line:
                    process_channel_line(line)

            other_lines.append('\n')

    except Exception as e:
        print(f"处理URL时发生错误：{e}")

def process_channel_line(line):
    if "#genre#" not in line and "," in line and "://" in line:
        channel_name = line.split(',')[0].strip()
        channel_address = clean_url(line.split(',')[1].strip())
        line = channel_name + "," + channel_address

        if channel_address not in combined_blacklist:
            if "CCTV" in channel_name and check_url_existence(ys_lines, channel_address):
                ys_lines.append(process_name_string(line.strip()))
            elif channel_name in ws_lines and check_url_existence(ws_lines, channel_address):
                ws_lines.append(process_name_string(line.strip()))
            elif channel_name in ty_lines and check_url_existence(ty_lines, channel_address):
                ty_lines.append(process_name_string(line.strip()))
            elif channel_name in dy_lines and check_url_existence(dy_lines, channel_address):
                dy_lines.append(process_name_string(line.strip()))
            elif channel_name in gat_lines and check_url_existence(gat_lines, channel_address):
                gat_lines.append(process_name_string(line.strip()))
            else:
                other_lines.append(line.strip())

def clean_url(url):
    last_dollar_index = url.rfind('$')
    if last_dollar_index != -1:
        return url[:last_dollar_index]
    return url

# 读取文本
ys_dictionary = read_txt_to_array('主频道/CCTV.txt')
ws_dictionary = read_txt_to_array('主频道/卫视频道.txt')
ty_dictionary = read_txt_to_array('主频道/体育频道.txt')
dy_dictionary = read_txt_to_array('主频道/收藏台.txt')
gat_dictionary = read_txt_to_array('主频道/港澳台.txt')

# 读取纠错频道名称方法
def load_corrections_name(filename):
    corrections = {}
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            correct_name = parts[0]
            for name in parts[1:]:
                corrections[name] = correct_name
    return corrections

# 读取纠错文件
corrections_name = load_corrections_name('assets/corrections_name.txt')

# 纠错频道名称
def correct_name_data(corrections, data):
    corrected_data = []
    for line in data:
        name, url = line.split(',', 1)
        if name in corrections and name != corrections[name]:
            name = corrections[name]
        corrected_data.append(f"{name},{url}")
    return corrected_data

def check_url_existence(data_list, url):
    urls = [item.split(',')[1] for item in data_list]
    return url not in urls

# 定义
urls = read_txt_to_array('assets/urls-daily.txt')

# 处理
async def main():
    for url in urls:
        print(f"处理URL: {url}")
        await process_url(url)

    # 测试延迟并排序
    delays = await measure_streams_live_streams(urls)
    url_delay_pairs = list(zip(urls, delays))

    # 过滤掉无效的直播源
    valid_streams = [(url, delay) for url, delay in url_delay_pairs if delay < float('inf')]

    # 获取分辨率并排序
    resolution_delay_pairs = [(url, delay, get_resolution(url)) for url, delay in valid_streams]
    resolution_delay_pairs.sort(key=lambda x: (x[2], x[1]))  # 按分辨率和延迟排序

    # 分别提取前10个IPv6和IPv4的直播源
    ipv6_streams = [pair for pair in resolution_delay_pairs if is_ipv6(pair[0])][:10]
    ipv4_streams = [pair for pair in resolution_delay_pairs if not is_ipv6(pair[0])][:10]

    # 将IPv6放在前面，IPv4放在后面
    combined_streams = ipv6_streams + ipv4_streams

    # 输出结果
    for index, (url, delay, resolution) in enumerate(combined_streams, start=1):
        print(f"线路 {index}: {url}, 延迟: {delay}, 分辨率: {resolution}")

# 运行主程序
asyncio.run(main())

# 执行结束时间
timeend = datetime.now()

# 计算时间差
elapsed_time = timeend - timestart
total_seconds = elapsed_time.total_seconds()

# 转换为分钟和秒
minutes = int(total_seconds // 60)
seconds = int(total_seconds % 60)
# 格式化开始和结束时间
timestart_str = timestart.strftime("%Y%m%d_%H_%M_%S")
timeend_str = timeend.strftime("%Y%m%d_%H_%M_%S")

print(f"开始时间: {timestart_str}")
print(f"结束时间: {timeend_str}")
print(f"执行时间: {minutes} 分 {seconds} 秒")

combined_blacklist_hj = len(combined_blacklist)
all_lines_hj = len(other_lines)  # 这里可以根据需要调整
print(f"blacklist行数: {combined_blacklist_hj} ")
print(f"others_output.txt行数: {all_lines_hj} ")
