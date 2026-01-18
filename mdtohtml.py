import argparse
import markdown
from markdown.extensions import def_list, fenced_code, tables, toc
import re
from bs4 import BeautifulSoup
import base64
import os
import yaml

def parse_arguments():
    parser = argparse.ArgumentParser(description='Конвертация Markdown в HTML с поддержкой таблиц, ссылок, идентификаторов заголовков и встроенными изображениями.')
    parser.add_argument('input', help='Путь к входному .md файлу')
    parser.add_argument('output', help='Путь к выходному .html файлу')
    return parser.parse_args()

def extract_metadata(content):
    """Извлекает метаданные из YAML фронтматтера."""
    metadata = {
        'title': 'Untitled',
        'author': '',
        'version': ''
    }
    
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            try:
                front_matter = yaml.safe_load(yaml_content)
                if front_matter:
                    metadata.update(front_matter)
            except yaml.YAMLError as e:
                print(f"Ошибка парсинга YAML: {e}")
    
    return metadata

def encode_image_to_base64(image_path):
    """Преобразует изображение в base64-строку."""
    try:
        with open(image_path, 'rb') as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }.get(ext, 'application/octet-stream')
        return f'data:{mime_type};base64,{encoded_string}'
    except Exception as e:
        print(f"Ошибка при кодировании изображения {image_path}: {e}")
        return None

def encode_font_to_base64(font_path):
    """Преобразует шрифт в base64-строку."""
    try:
        with open(font_path, 'rb') as font_file:
            encoded_string = base64.b64encode(font_file.read()).decode('utf-8')
        ext = os.path.splitext(font_path)[1].lower()
        mime_type = {
            '.ttf': 'font/ttf',
            '.otf': 'font/otf',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2'
        }.get(ext, 'application/octet-stream')
        return f'data:{mime_type};base64,{encoded_string}'
    except Exception as e:
        print(f"Ошибка при кодировании шрифта {font_path}: {e}")
        return None

def convert_markdown_to_html(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as md_file:
        raw_content = md_file.read()
    
    # Извлекаем метаданные из YAML фронтматтера
    metadata = extract_metadata(raw_content)
    title = metadata['title']
    author = metadata.get('author', '')
    version = metadata.get('version', '')
    
    # Удаляем YAML фронтматтер из контента для обработки Markdown
    if raw_content.startswith('---'):
        parts = raw_content.split('---', 2)
        if len(parts) >= 3:
            markdown_content = parts[2].strip()
        else:
            markdown_content = raw_content
    else:
        markdown_content = raw_content
    
    # Заменяем [toc] на [TOC] для корректной обработки
    markdown_content = re.sub(r'\[toc\]', '[TOC]', markdown_content, flags=re.IGNORECASE)
                              
    def custom_slugify(text, sep):
        text = re.sub(r'[^\w\s\-]', '', text)
        text = text.lower().replace(' ', '-').replace('–', '-').replace('—', '-')
        return text
    
    html_content = markdown.markdown(
        markdown_content,
        extensions=[
            'tables',
            'def_list',
            'fenced_code',
            toc.TocExtension(
                toc_depth="2-6",
                permalink=False,
                slugify=custom_slugify,
                toc_class="sidebar-toc"
            )
        ]
    )
    
    soup = BeautifulSoup(html_content, 'html.parser')
    toc_div = soup.find('div', class_='sidebar-toc')
    toc_html = str(toc_div) if toc_div else ''
    
    if toc_div:
        toc_div.decompose()
    
    # Кодирование шрифта Arial
    font_base64 = None
    font_path = os.path.join(os.path.dirname(input_path), 'font', 'Arial.ttf')
    if os.path.exists(font_path):
        font_base64 = encode_font_to_base64(font_path)
    else:
        print(f"Предупреждение: Файл шрифта не найден по пути {font_path}")
        print("Будет использован стандартный Arial из системы")
    
    # Обработка логотипа
    logo_base64 = None
    logo_path = os.path.join(os.path.dirname(input_path), 'image', 'logo.png')
    if os.path.exists(logo_path):
        logo_base64 = encode_image_to_base64(logo_path)
    else:
        print(f"Предупреждение: Логотип не найден по пути {logo_path}")
    
    # Обработка изображений в контенте
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src')
        if src and not src.startswith(('http://', 'https://')):
            image_path = os.path.join(os.path.dirname(input_path), src)
            if os.path.exists(image_path):
                base64_data = encode_image_to_base64(image_path)
                if base64_data:
                    img_tag['src'] = base64_data
                else:
                    print(f"Не удалось встроить изображение: {src}")
            else:
                print(f"Изображение не найдено: {src}")

    # CSS с встроенным шрифтом
    font_css = ""
    if font_base64:
        font_css = f"""
        @font-face {{
            font-family: 'Arial';
            src: url('{font_base64}') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }}
        """
    else:
        font_css = """
        @font-face {
            font-family: 'Arial';
            src: local('Arial'), local('Arial MT');
            font-weight: normal;
            font-style: normal;
        }
        """

    # HTML логотипа с правильным разрешением 254x84
    logo_html = ""
    if logo_base64:
        logo_html = f'<img src="{logo_base64}" alt="Logo" style="width: 254px; height: 84px;">'
    else:
        logo_html = '<div style="width: 254px; height: 84px; background: #8B8B8B; color: white; text-align: center; line-height: 84px;">ЛОГО</div>'

    # HTML для информации о продукте и версии
    product_info_html = ""
    if author or version:
        product_info_html = f"""
        <div style="margin-top: 10px; font-size: 12px; line-height: 1.4;">
            {f'<div><strong>{author}</strong></div>' if author else ''}
            {f'<div>Версия {version}</div>' if version else ''}
        </div>
        """

    html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="generator" content="Markdown Converter">
    <meta name="keywords" content="">
    <meta name="description" content="{title}">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{title}</title>
    <style>
        {font_css}
        
        body {{
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
            color: #000000;
            overflow: hidden;
        }}
        
        #printheader {{
            display: none;
        }}
        
        #idheader {{
            width: 100%;
            height: auto;
            padding: 0;
            margin: 0;
        }}
        
        #idheaderbg {{
            background: #e41d30;
        }}
        
        .header-table {{
            width: 100%;
            border: 0;
            cellspacing: 0;
            cellpadding: 0;
            margin: 0px;
            background: #e41d30;
        }}
        
        .header-logo {{
            vertical-align: middle;
            width: 254px;
            white-space: nowrap;
            padding: 10px 15px;
        }}
        
        .topichead {{
            vertical-align: middle;
            text-align: left;
            color: white;
            padding: 10px 15px;
        }}
        
        .topichead h1 {{
            color: white;
            margin: 0;
            font-size: 18px;
            font-weight: bold;
            line-height: 1.2;
        }}
        
        .product-info {{
            color: white;
            font-size: 12px;
            line-height: 1.4;
            margin-top: 5px;
        }}
        
        .product-info strong {{
            display: block;
        }}
        
        hr {{
            size: 1;
            margin: 0;
            border: none;
            border-top: 1px solid #ddd;
        }}
        
        .container {{
            display: flex;
            height: calc(100vh - 104px);
        }}
        
        .sidebar {{
            width: 280px;
            background-color: #f8f9fa;
            border-right: 1px solid #dee2e6;
            padding: 15px;
            overflow-y: auto;
            font-size: 12px;
        }}
        
        .sidebar h2 {{
            font-size: 14px;
            margin-top: 0;
            margin-bottom: 12px;
            color: #2c3e50;
            border-bottom: 1px solid #3498db;
            padding-bottom: 4px;
        }}
        
        /* Стили для компактного оглавления */
        .sidebar-toc ul {{
            list-style-type: none;
            padding-left: 8px;
            margin: 0;
        }}
        
        .sidebar-toc li {{
            margin: 3px 0;
            line-height: 1.3;
        }}
        
        .sidebar-toc a {{
            color: #2c3e50;
            text-decoration: none;
            font-size: 11px;
            display: block;
            padding: 2px 4px;
            border-radius: 2px;
            transition: all 0.2s ease;
        }}
        
        .sidebar-toc a:hover {{
            color: #e41d30;
            background-color: #e9ecef;
        }}
        
        /* Уровни вложенности */
        .sidebar-toc ul ul {{
            padding-left: 12px;
            margin: 2px 0;
        }}
        
        .sidebar-toc ul ul ul {{
            padding-left: 10px;
        }}
        
        .sidebar-toc ul ul a {{
            font-size: 10px;
            color: #495057;
            padding: 1px 4px 1px 8px;
            border-left: 2px solid #dee2e6;
        }}
        
        .sidebar-toc ul ul ul a {{
            font-size: 9px;
            color: #6c757d;
            padding: 1px 4px 1px 12px;
            border-left: 1px solid #ced4da;
        }}
        
        .sidebar-toc ul ul a:hover {{
            border-left-color: #e41d30;
        }}
        
        #idcontent {{
            flex: 1;
            overflow: auto;
            padding: 20px 40px;
            background-color: #ffffff;
        }}
        
        #innerdiv {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            font-size: 24px;
        }}
        
        h2 {{
            border-bottom: 1px solid #3498db;
            padding-bottom: 8px;
            font-size: 20px;
        }}
        
        h3 {{
            font-size: 18px;
            color: #34495e;
        }}
        
        p {{
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 15px;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            border: 1px solid #000;
            margin: 15px 0;
            font-size: 13px;
        }}
        
        th, td {{
            border: 1px solid #000;
            padding: 6px 8px;
            text-align: left;
        }}
        
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        
        pre {{
            background-color: #f4f4f4;
            padding: 12px;
            overflow-x: auto;
            border-radius: 4px;
            border: 1px solid #ddd;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.4;
        }}
        
        .p_Название1_аястранeoeа {{
            border-top: none;
            border-right: none;
            border-left: none;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 10px;
        }}
        
        .p_Названиепродукта {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .p_Версияпродукта {{
            color: #666;
            margin-bottom: 20px;
        }}
        
        .p_Normal {{
            margin: 15px 0;
        }}
        
        @media screen and (max-width: 1024px) {{
            .sidebar {{
                width: 240px;
                padding: 12px;
            }}
            
            #idcontent {{
                padding: 15px 20px;
            }}
            
            .header-logo {{
                width: 200px;
                padding: 5px 10px;
            }}
            
            .header-logo img {{
                width: 200px;
                height: auto;
                max-height: 66px;
            }}
        }}
        
        @media screen and (max-width: 768px) {{
            .container {{
                flex-direction: column;
                height: auto;
            }}
            
            .sidebar {{
                width: 100%;
                height: 200px;
                border-right: none;
                border-bottom: 1px solid #dee2e6;
            }}
            
            #idcontent {{
                padding: 15px;
            }}
            
            .header-logo {{
                width: 150px;
                padding: 5px;
            }}
            
            .header-logo img {{
                width: 150px;
                height: auto;
                max-height: 50px;
            }}
            
            .topichead h1 {{
                font-size: 16px;
            }}
            
            .product-info {{
                font-size: 11px;
            }}
        }}
        
        @media print {{
            span.f_Heading1 {{ color: black; }}
            #idheader, #printheader img {{ display: none; }}
            #printheader {{ display: block; margin-top: 20px; }}
            #idcontent {{ margin-top: 10px; }}
            .sidebar {{ display: none; }}
        }}
    </style>
</head>
<body>

<div id="printheader"><h1 class="p_Heading1"><span class="f_Heading1">{title}</span></h1></div>

<div id="idheader">
<div id="idheaderbg">
<table class="header-table">
  <tr valign="middle">
    <td class="header-logo">
        {logo_html}
    </td>
    <td class="topichead">
        <h1 class="p_Heading1"><span class="f_Heading1">{title}</span></h1>
        {product_info_html}
    </td>
  </tr>
</table>
</div>

<hr/>

</div>

<div class="container">
    <div class="sidebar">
        <h2>Содержание</h2>
        {toc_html}
    </div>
    
    <div id="idcontent">
        <div id="innerdiv">
            {soup.prettify()}
        </div>
    </div>
</div>

</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as html_file:
        html_file.write(html_template)

if __name__ == '__main__':
    args = parse_arguments()
    convert_markdown_to_html(args.input, args.output)