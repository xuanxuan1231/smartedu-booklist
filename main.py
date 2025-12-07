"""
纯手搓 从smartedu提取课本数据
"""

import requests, json
from datetime import datetime
from loguru import logger

FILE_SERVER = "1"

data = requests.get(f"https://s-file-{FILE_SERVER}.ykt.cbern.com.cn/zxx/ndrs/tags/tch_material_tag.json").json()
logger.success("获取分类数据")

tag_data = []
for part in range(100, 102):
    tag_data += requests.get(
        f"https://s-file-{FILE_SERVER}.ykt.cbern.com.cn/zxx/ndrs/resources/tch_material/part_{part}.json"
    ).json()
    logger.debug(f"获取课本数据分片 {part%100}")
tag_data = tag_data[:-10] # 把教师用书的视频扔了
logger.success("获取课本数据")

periods = data["hierarchies"][0]["children"][0]["hierarchies"][0]["children"]

for period in periods[:-2]: # 不处理高中和特殊教育的数据
    name = period["tag_name"]
    period_id = period["tag_id"]
    logger.debug(f"正在遍历学段 {name}。ID: {period_id}")
    subjects = []
    for subject in period["hierarchies"][0]["children"]:
        subject_data = {
            "name": subject["tag_name"],
            "versions": []
        }
        subject_id = subject["tag_id"]
        logger.debug(f"正在遍历学科 {subject_data['name']}。ID: {subject_id}")
        if subject_data['name'] == "信息科技": 
            # 信息科技没有“版本” 后面再写
            logger.info("跳过 信息科技 学科")
            continue
        for version in subject["hierarchies"][0]["children"]:
            version_data = {
                "name": version["tag_name"],
                "grades": []
            }
            version_id = version["tag_id"]
            logger.debug(f"正在遍历版本 {version_data['name']}。ID: {version_id}")
            for grade in version["hierarchies"][0]["children"]:
                grade_data = {
                    "name": grade["tag_name"],
                    "books": []
                }
                grade_id = grade["tag_id"]
                logger.debug(f"正在遍历年级 {grade_data['name']}。ID: {grade_id}")
                books = []
                for book in tag_data:
                    if f"{subject_id}/{version_id}/{grade_id}" in book["tag_paths"][0]:
                        book_data = {
                            "name": book["title"],
                            "content_id": book["id"]
                        }
                        books.append(book_data)
                        logger.success(f"匹配到课本 {book_data['name']}，ID: {book["id"]}")
                    #logger.warning(f"课本 ID 是 {book["id"]}。当前正在遍历的课本 ID 是 {book['tag_paths'][0]}")
                grade_data["books"] = books
                version_data["grades"].append(grade_data)
            subject_data["versions"].append(version_data)
        subjects.append(subject_data)
    final_data = {
        "version": datetime.now().strftime("%Y%m%d%H%M"),
        "subjects": subjects
    }
    #print(final_data)
    #break
    if name == "小学":
        filename = "primary.json"
    elif name == "初中":
        filename = "junior.json"
    elif name == "小学（五·四制）":
        filename = "primary_54.json"
    elif name == "初中（五·四制）":
        filename = "junior_54.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    logger.success(f"已写入文件 {filename}")

