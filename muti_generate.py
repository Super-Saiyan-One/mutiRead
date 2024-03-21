import concurrent.futures
import json
import threading

import openai
import os

openai.api_key = ''
lock = threading.Lock()


def create_result_file(result_file_name):
    data = []
    with open(result_file_name, 'w') as file:
        json.dump(data, file)


def askChatGPT(messages):
    MODEL = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=messages,
        temperature=0.7)
    return response['choices'][0]['message']['content']


def build_template(text):
    prompt_template = (
        f"请你基于以下材料回答下面三个问题：该段材料的法律关键词、法律主体、主体之间的关系分别是什么？"
        f"回答格式请用json，请你严格确保分三行回答三个不同的问题。每一行的key字段分别为：法律关键词、法律主体、主体之间的关系。答案字段为字符串，不要有其余符号。"
        f"以下是材料：{text}"
        f"请你每个问题的答案尽可能详细、完整。并且请你严格确保返回答案为一个json对象，这个非常重要。"
    )
    return prompt_template


def generate_answer(prompt_text, line_number):
    messages = [{"role": "user", "content": ""}]
    tmp = {"role": "user", "content": build_template(prompt_text)}
    messages.append(tmp)
    json_data = askChatGPT(messages)
    print(json_data)
    data = json.loads(json_data)
    data['line'] = line_number
    return data


def process_line(filename, line_number):
    with open(filename, 'r') as file:
        for current_line_number, line in enumerate(file):
            if current_line_number == line_number:
                return f"Line {line_number}: {line.strip()}"


def read_file_in_chunks(filename, num_threads, result_filename):
    create_result_file(result_filename)
    with open(filename, 'r') as file:
        total_lines = sum(1 for _ in file)

    # Create a thread pool and assign a line to each thread
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # 将每一个future和每行的line进行映射
        future_to_line = {executor.submit(process_line, filename, i): i for i in range(total_lines)}

        # 当线程执行完毕时处理结果
        for future in concurrent.futures.as_completed(future_to_line):
            line_number = future_to_line[future]
            try:
                with lock:
                    data = future.result()
                    json_result = generate_answer(data, line_number)
                    with open(result_filename, 'r+', encoding='utf-8') as file:
                        results = json.load(file)
                        results.append(json_result)
                        file.seek(0)
                        json.dump(results, file, ensure_ascii=False, indent=4)
                        file.truncate()
            except Exception as exc:
                print(f'Line {line_number} generated an exception: {exc}')
            else:
                if data:
                    print(data)


num_threads = 5

filename = 'information.txt'

result_filename = 'result.json'

read_file_in_chunks(filename, num_threads, result_filename)
