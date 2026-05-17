#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import html
from datetime import datetime

def extract_posts(sql_file_path):
    """从WordPress SQL文件提取文章"""
    
    print(f"读取文件: {sql_file_path}")
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}")
        return []
    
    # 查找所有wp_posts的INSERT语句
    posts_pattern = r"INSERT INTO `wp_posts`[^;]*;"
    matches = re.findall(posts_pattern, content, re.DOTALL | re.IGNORECASE)
    
    print(f"找到 {len(matches)} 个INSERT语句")
    
    if not matches:
        return []
    
    all_posts = []
    
    for i, match in enumerate(matches):
        print(f"处理第 {i+1} 个INSERT语句")
        
        # 提取VALUES后面的内容
        values_match = re.search(r"VALUES\s*(.*)", match, re.DOTALL | re.IGNORECASE)
        if not values_match:
            continue
            
        values_content = values_match.group(1)
        
        # 提取每条记录
        records = re.findall(r'\(((?:[^()]|\([^()]*\))*)\)', values_content)
        
        print(f"  找到 {len(records)} 条记录")
        
        for record in records:
            fields = parse_sql_fields(record)
            
            if len(fields) < 15:
                continue
                
            # 提取关键字段
            post_data = {
                'ID': clean_field(fields[0]),
                'post_date': clean_field(fields[2]),
                'post_content': clean_field(fields[4]),
                'post_title': clean_field(fields[5]),
                'post_status': clean_field(fields[7]),
                'post_type': clean_field(fields[20]) if len(fields) > 20 else 'post'
            }
            
            # 只处理已发布的文章
            if (post_data['post_status'] == 'publish' and 
                post_data['post_type'] in ('post', 'page') and
                post_data['post_title'] and 
                post_data['post_title'] != 'Auto Draft'):
                all_posts.append(post_data)
                print(f"    提取: {post_data['post_title'][:30]}...")
    
    print(f"总共提取到 {len(all_posts)} 篇已发布文章")
    return all_posts

def parse_sql_fields(record):
    """解析SQL字段"""
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
    
    if current_field.strip():
        fields.append(current_field.strip())
    
    return fields

def clean_field(field):
    """清理字段值"""
    if not field:
        return ""
    
    if field.startswith("'") and field.endswith("'"):
        field = field[1:-1]
    
    field = field.replace("\\'", "'")
    field = field.replace('\\"', '"')
    field = field.replace('\\\\', '\\')
    
    return field

def create_markdown_files(posts):
    """创建Markdown文件"""
    
    for category in ['诗词', '散文', '学术']:
        os.makedirs(f"content/{category}", exist_ok=True)
    
    created_count = 0
    
    for post in posts:
        category = classify_post(post)
        filename = create_filename(post['post_title'])
        
        if not filename:
            continue
        
        content = clean_content(post['post_content'])
        date_str = format_date(post['post_date'])
        
        md_content = f"""---
title: "{post['post_title']}"
date: {date_str}
draft: false
categories: ["{category}"]
---

{content}
"""
        
        filepath = f"content/{category}/{filename}.md"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            created_count += 1
            print(f"创建: {filepath}")
        except Exception as e:
            print(f"创建文件失败 {filepath}: {e}")
    
    return created_count

def classify_post(post):
    """分类文章"""
    title = (post['post_title'] or '').lower()
    content = (post['post_content'] or '').lower()
    
    poetry_words = ['诗', '词', '七律', '五律', '绝句', '古诗', '吟', '赋', '韵']
    academic_words = ['汉字', '部首', '文字', '语言', '研究', '论文', '学术', '教学', '教育']
    
    text = title + " " + content
    
    if any(word in text for word in poetry_words):
        return "诗词"
    elif any(word in text for word in academic_words):
        return "学术"
    else:
        return "散文"

def create_filename(title):
    """创建安全的文件名"""
    if not title:
        return ""
    
    import re
    filename = re.sub(r'[^\w\u4e00-\u9fff-]', '-', title)
    filename = re.sub(r'-+', '-', filename)
    filename = filename.strip('-')
    return filename[:50]

def clean_content(content):
    """清理HTML内容"""
    if not content:
        return ""
    
    content = re.sub(r'<[^>]+>', '', content)
    content = html.unescape(content)
    content = content.replace('\\r\\n', '\n').replace('\\n', '\n')
    content = re.sub(r'\n\s*\n', '\n\n', content)
    return content.strip()

def format_date(date_str):
    """格式化日期"""
    if not date_str:
        return '2024-01-01T00:00:00+08:00'
    
    try:
        dt = datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    except:
        return '2024-01-01T00:00:00+08:00'

if __name__ == "__main__":
    sql_file = "/Users/shu/Sites/fyl Wordpress/sql data backup/localhost(3).sql"
    
    print("开始提取WordPress文章...")
    posts = extract_posts(sql_file)
    
    if posts:
        created_count = create_markdown_files(posts)
        print(f"\n✅ 成功创建 {created_count} 篇Markdown文件")
        
        from collections import Counter
        categories = Counter()
        for post in posts:
            cat = classify_post(post)
            categories[cat] += 1
        
        print("\n📊 分类统计:")
        for cat, count in categories.most_common():
            print(f"  {cat}: {count} 篇")
    else:
        print("❌ 未找到可提取的文章")
