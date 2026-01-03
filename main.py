"""
纯手搓 从smartedu提取课本数据
"""

import requests, json
from datetime import datetime
from loguru import logger
import dns.resolver

logger.add("logs/{time}.log")

resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers = ["1.1.1.1", "1.0.0.1", "223.5.5.5"]

FILE_SERVER = "1"
DOMAIN = f"s-file-{FILE_SERVER}.ykt.cbern.com.cn"
IP = resolver.resolve(DOMAIN, "A", lifetime=15.0)[0]
logger.success(f"DNS 解析完成。IP：{IP}")

data = requests.get(
    f"https://{IP}/zxx/ndrs/tags/tch_material_tag.json",
    headers={"Host": DOMAIN},
    verify=False
    ).json()
logger.success("获取分类数据")

tag_data = []
for part in range(100, 104):
    tag_data += requests.get(
        f"https://{IP}/zxx/ndrs/resources/tch_material/part_{part}.json",
        headers={"Host": DOMAIN},
        verify=False
    ).json()
    logger.debug(f"获取课本数据分片 {part%100}")
# tag_data = tag_data[:-10] # 把教师用书的视频扔了 当我他妈没说 什么狗屎排序
logger.success("获取课本数据")

periods = data["hierarchies"][0]["children"][0]["hierarchies"][0]["children"]

for period in periods[:-1]: # 不处理特殊教育的数据
    name = period["tag_name"]
    period_id = period["tag_id"]
    logger.debug(f"正在遍历学段 {name}。ID: {period_id}")
    subjects = []

    origindata_subjects = period["hierarchies"][0]["children"]
    for subject in origindata_subjects:
        subject_data = {
            "name": subject["tag_name"],
            "versions": []
        }
        subject_id = subject["tag_id"]
        logger.debug(f"正在遍历学科 {subject_data['name']}。ID: {subject_id}")
        
        origindata_versions = subject["hierarchies"][0]["children"]
        # 没有版本 造个版本嘛
        if subject["hierarchies"][0]["hierarchy_name"] == "年级":
            # 创建形式版本 全部
            origindata_versions = [{"tag_id": "", "tag_name": "全部", "hierarchies": subject["hierarchies"]}]
        for version in origindata_versions:
            version_data = {
                "name": version["tag_name"],
                "grades": []
            }
            version_id = version["tag_id"]
            if version_id == "":
                logger.debug(f"正在遍历形式版本 全部。没有 ID。")
            else:
                logger.debug(f"正在遍历版本 {version_data['name']}。ID: {version_id}")
            
            origindata_grades = version["hierarchies"][0]["children"]
            # 没有年级？那就造个年级！
            if version["hierarchies"][0]["children"] == []:
                # 创建形式年级 全部
                origindata_grades = [{"tag_id": "", "tag_name": "全部"}]
            for grade in origindata_grades:
                grade_data = {
                    "name": grade["tag_name"],
                    "books": []
                }
                grade_id = grade["tag_id"]
                if grade_id == "":
                    logger.debug(f"正在遍历形式年级 全部。没有 ID。")
                else:
                    logger.debug(f"正在遍历年级 {grade_data['name']}。ID: {grade_id}")
                books = []
                for book in tag_data:
                    if "tag_paths" not in book.keys():
                        continue
                    if book["tag_paths"] == []:
                        continue
                    # 更傻福的判断
                    if f"{period_id}/{subject_id}{("/" + version_id) if version_id != "" else ""}{("/" + grade_id) if grade_id != "" else ""}" in book["tag_paths"][0]:
                        try:
                            ti_response = requests.get(
                                f"https://{IP}/zxx/ndrv2/resources/tch_material/details/{book["id"]}.json",
                                headers={"Host": DOMAIN},
                                verify=False
                            ).json()
                            for ti in ti_response["ti_items"]:
                                if ti["ti_storage"].endswith(".pdf"):
                                    path = ti["ti_storage"].replace("cs_path:${ref-path}", "")
                                    break
                            book_data = {
                                "name": book["title"],
                                "content_id": book["id"],
                                "path": path
                            }
                        except:
                            book_data = {
                                "name": book["title"],
                                "content_id": book["id"],
                                "path": f"{book["id"]}: Failed to fetch path"
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
    if name == "小学（五•四学制）":
        filename = "primary54.json"
    elif name == "初中（五•四学制）":
        filename = "junior54.json"
    elif name == "小学":
        filename = "primary.json"
    elif name == "初中":
        filename = "junior.json"
    elif name == "高中":
        filename = "senior.json"
    else:
        continue
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, separators=(',', ':'))
    logger.success(f"已写入文件 {filename}")

categories = []
for category in periods[-1]["hierarchies"][0]["children"]: # 处理特殊教育的数据
    category_data = {
        "name": category["tag_name"],
        "periods": []
    }
    category_id = category["tag_id"]
    logger.debug(f"正在遍历特殊教育类别 {name}。ID: {category_id}")

    origindata_periods = category["hierarchies"][0]["children"]
    if category["hierarchies"][0]["hierarchy_name"] == "学科":
        # 创建形式学段 特殊教育
        origindata_periods = [{"tag_id": "", "tag_name": "全部", "hierarchies": category["hierarchies"]}]
    for period in origindata_periods:
        period_data = {
            "name": period["tag_name"],
            "subjects": []
        }
        period_id = period["tag_id"]
        if period_id == "":
            logger.debug(f"正在遍历特殊教育形式学段 全部。没有 ID。")
        else:
            logger.debug(f"正在遍历特殊教育学段 {period_data['name']}。ID: {period_id}")

        origindata_subjects = period["hierarchies"][0]["children"]
        for subject in origindata_subjects:
            subject_data = {
                "name": subject["tag_name"],
                "grades": []
            }
            subject_id = subject["tag_id"]
            logger.debug(f"正在遍历学科 {subject_data['name']}。ID: {subject_id}")

            origindata_grades = subject["hierarchies"][0]["children"]
            if subject["hierarchies"][0]["hierarchy_name"] == "册次":
                # 创建形式年级 全部
                origindata_grades = [{"tag_id": "", "tag_name": "全部", "hierarchies": subject["hierarchies"]}]
            for grade in origindata_grades:
                grade_data = {
                    "name": grade["tag_name"],
                    "volumes": []
                }
                grade_id = grade["tag_id"]
                if grade_id == "":
                    logger.debug(f"正在遍历形式年级 全部。没有 ID。")
                else:
                    logger.debug(f"正在遍历年级 {grade_data['name']}。ID: {grade_id}")
                
                origindata_volumes = grade["hierarchies"][0]["children"]
                if origindata_volumes == []:
                    # 创建形式册次 全部
                    origindata_volumes = [{"tag_id": "", "tag_name": "全部"}]
                for volume in origindata_volumes:
                    volume_data = {
                        "name": volume["tag_name"],
                        "books": []
                    }
                    volume_id = volume["tag_id"]
                    if volume_id == "":
                        logger.debug(f"正在遍历形式册次 全部。没有 ID。")
                    else:
                        logger.debug(f"正在遍历册次 {volume_data['name']}。ID: {volume_id}")
                    books = []
                    for book in tag_data:
                        if "tag_paths" not in book.keys():
                            continue
                        if book["tag_paths"] == []:
                            continue
                        # 更傻福的判断
                        if f"{category_id}{("/" + period_id) if period_id != "" else ""}/{subject_id}{("/" + grade_id) if grade_id != "" else ""}{("/" + volume_id) if volume_id != "" else ""}" in book["tag_paths"][0]:
                            try:
                                ti_response = requests.get(
                                    f"https://{IP}/zxx/ndrv2/resources/tch_material/details/{book["id"]}.json",
                                    headers={"Host": DOMAIN},
                                    verify=False
                                ).json()
                                for ti in ti_response["ti_items"]:
                                    if ti["ti_storage"].endswith(".pdf"):
                                        path = ti["ti_storage"].replace("cs_path:${ref-path}", "")
                                        break
                                book_data = {
                                    "name": book["title"],
                                    "content_id": book["id"],
                                    "path": path
                                }
                            except:
                                book_data = {
                                    "name": book["title"],
                                    "content_id": book["id"],
                                    "path": f"{book["id"]}: Failed to fetch path"
                                }
                            books.append(book_data)
                            logger.success(f"匹配到课本 {book_data['name']}，ID: {book["id"]}")
                    volume_data["books"] = books
                    grade_data["volumes"].append(volume_data)
                subject_data["grades"].append(grade_data)
            period_data["subjects"].append(subject_data)
        category_data["periods"].append(period_data)
    categories.append(category_data)
final_data = {
    "version": datetime.now().strftime("%Y%m%d%H%M"),
    "categories": categories
}
filename = "special.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, separators=(',', ':'))
logger.success(f"已写入文件 {filename}")
            