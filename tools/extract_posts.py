#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import html
from datetime import datetime

def extract_wp_posts(sql_file_path):
    """从WordPress SQL文件提取文章"""
    
    print(f"读取文件: {sql_file_path}")
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找wp_posts表的INSERT语句
    posts_pattern = r"INSERT INTO `wp_posts` VALUES (.*?);"
    matches = re.findall(posts_pattern, content, re.DOTALL)
    
    if not matches:
        print("未找到wp_posts表的INSERT语句")
        return []
    
    print(f"找到 {len(matches)} 个INSERT语句")
    
    all_posts = []
    
    for match in matches:
        # 提取每条记录
        records = re.findall(r'\((.*?)\)', match)
        print(f"处理 {len(records)} 条记录")
        
        for record in records:
            # 分割字段，处理转义和引号
            fields = parse_sql_record(record)
            
            if len(fields) < 15:
                continue
                
            post_data = {
                'ID': fields[0],
                'post_date': fields[1].strip("'"),
                'post_content': fields[3].strip("'"),
                'post_title': fields[4].strip("'"),
                'post_status': fields[5].strip("'"),
                'post_type': fields[9].strip("'")
            }
            
            # 只处理已发布的文章和页面
            if post_data['post_status'] == 'publish' and post_data['post_type'] in ('post', 'page'):
                all_posts.append(post_data)
    
    print(f"提取到 {len(all_posts)} 篇已发布文章")
    return all_posts

def parse_sql_record(record):
    """解析SQL记录中的字段"""
    fields = []
    current_field = ""
    in_quotes = False
    escaped = False
    
    for char in record:
        if escaped:
            current_field += char
            escaped = False
        elif char == '\\':
            current_field += char
            escaped = True
        elif char == "'":
            in_quotes = not in_quotes
            current_field += char
        elif char == ',' and not in_quotes:
            fields.append(current_field.strip())
            current_field = ""
        else:
            current_field += char
    
    if current_field:
        fields.append(current_field.strip())
    
    return fields

def create_markdown_from_posts(posts, output_dir="content"):
    """将文章转换为Markdown文件"""
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/诗词", exist_ok=True)
    os.makedirs(f"{output_dir}/散文", exist_ok=True) 
    os.makedirs(f"{output_dir}/学术", exist_ok=True)
    
    created_count = 0
    
    for post in posts:
        # 清理标题作为文件名
        title = post['post_title']
        if not title or title == 'Auto Draft':
            continue
            
        # 确定分类
        category = determine_category(title, post['post_content'])
        
        # 创建安全的文件名
        safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '-', title)
        safe_title = safe_title[:50]
        
        if not safe_title:
            safe_title = f"post-{post['ID']}"
        
        filepath = f"{output_dir}/{category}/{safe_title}.md"
        
        # 准备内容
        content = clean_content(post['post_content'])
        date_str = format_date(post['post_date'])
        
        # 创建Markdown
        md_content = f"""---
title: "{title}"
date: {date_str}
draft: false
categories: ["{category}"]
---

{content}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        created_count += 1
        print(f"创建: {filepath}")
    
    return created_count

def determine_category(title, content):
    """根据标题和内容确定分类"""
    text = (title + " " + content).lower()
    
    poetry_keywords = ['诗', '词', '七律', '五律', '绝句', '古诗', '韵', '赋']
    academic_keywords = ['汉字', '部首', '文字', '语言', '研究', '论文', '学术', '教学']
    
    if any(keyword in text for keyword in poetry_keywords):
        return "诗词"
    elif any(keyword in text for keyword in academic_keywords):
        return "学术"
    else:
        return "散文"

def clean_content(content):
    """清理HTML和WordPress短代码"""
    # 移除HTML标签
    content = re.sub(r'<[^>]+>', '', content)
    
    # 移除WordPress短代码
    content = re.sub(r'\[[^\]]+\]', '', content)
    
    # 处理转义字符
    content = content.replace('\\r\\n', '\n').replace('\\n', '\n')
    content = content.replace("\\'", "'")
    content = content.replace('\\"', '"')
    
    # 解码HTML实体
    content = html.unescape(content)
    
    # 清理多余空行
    content = re.sub(r'\n\s*\n', '\n\n', content)
    
    return content.strip()

def format_date(date_str):
    """格式化日期"""
    try:
        # 尝试解析MySQL日期格式
        dt = datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    except:
        return '2024-01-01T00:00:00+08:00'

if __name__ == "__main__":
    sql_file = "/Users/shu/Sites/fyl Wordpress/sql data backup/localhost(3).sql"
    
    print("开始提取WordPress文章...")
    posts = extract_wp_posts(sql_file)
    
    if posts:
        count = create_markdown_from_posts(posts)
        print(f"\n成功创建 {count} 篇Markdown文件")
        
        # 显示一些统计信息
        categories = {}
        for post in posts:
            cat = determine_category(post['post_title'], post['post_content'])
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n分类统计:")
        for cat, num in categories.items():
            print(f"  {cat}: {num} 篇")
    else:
        print("未找到可提取的文章")
