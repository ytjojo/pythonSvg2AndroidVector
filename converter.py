import os
import argparse
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import math

# 常量定义
KAPPA = 0.5522847498307935  # 圆/椭圆贝塞尔曲线控制点系数

def s(number: float) -> str:
    """格式化浮点数，保留12位精度"""
    return str(round(number, 12))

def normalize_color(color: str) -> str:
    """规范化颜色格式，添加透明度通道"""
    if not color or color.lower() == "none":
        return "#00000000"  # 完全透明
    
    # 处理短格式颜色 (#RGB → #RRGGBB)
    if re.match(r"^#([0-9a-f]{3})$", color, re.IGNORECASE):
        color = f"#{color[1]*2}{color[2]*2}{color[3]*2}"
    
    # 添加透明度通道 (#RRGGBB → #AARRGGBB)
    if re.match(r"^#([0-9a-f]{6})$", color, re.IGNORECASE):
        color += "FF"  # 添加完全不透明通道
    
    # 修正：使用正确的字符串方法 startswith() 和 len()
    if color.startswith("#00") and len(color) == 9:
        return "#00000000"  # 已规范化为标准透明色格式
    
    return color

def convert_units(value: str) -> str:
    """将像素单位转换为dp，处理无单位情况"""
    if value.endswith("px"):
        return value.replace("px", "dp")
    elif value.replace(".", "", 1).isdigit():  # 检查是否为纯数字
        return f"{value}dp"
    return value

def convert_line(line: ET.Element) -> str:
    """转换直线为路径数据"""
    x1 = line.get("x1", "0")
    y1 = line.get("y1", "0")
    x2 = line.get("x2", "0")
    y2 = line.get("y2", "0")
    return f"M {x1} {y1} L {x2} {y2}"

def convert_rect(rect: ET.Element) -> str:
    """转换矩形为路径数据"""
    x = float(rect.get("x", "0"))
    y = float(rect.get("y", "0"))
    w = float(rect.get("width", "0"))
    h = float(rect.get("height", "0"))
    rx = float(rect.get("rx", "0"))
    ry = float(rect.get("ry", "0") or rx)  # 如果ry未设置则使用rx
    
    # 无圆角矩形
    if rx == 0 and ry == 0:
        return f"M {x} {y} H {s(x+w)} V {s(y+h)} H {x} V {y} Z"
    
    # 圆角矩形
    r = s(x + w)
    b = s(y + h)
    return (
        f"M {s(x + rx)} {y} "
        f"L {s(x + w - rx)} {y} "
        f"Q {x+w} {y} {x+w} {s(y + ry)} "
        f"L {x+w} {s(y + h - ry)} "
        f"Q {x+w} {y+h} {s(x + w - rx)} {y+h} "
        f"L {s(x + rx)} {y+h} "
        f"Q {x} {y+h} {x} {s(y + h - ry)} "
        f"L {x} {s(y + ry)} "
        f"Q {x} {y} {s(x + rx)} {y} Z"
    )

def convert_circle(circle: ET.Element) -> str:
    """转换圆形为路径数据"""
    cx = float(circle.get("cx", "0"))
    cy = float(circle.get("cy", "0"))
    r_val = float(circle.get("r", "0"))
    ctrl_dist = r_val * KAPPA
    
    return (
        f"M {cx} {s(cy - r_val)} "
        f"C {s(cx + ctrl_dist)} {s(cy - r_val)} {s(cx + r_val)} {s(cy - ctrl_dist)} {s(cx + r_val)} {cy} "
        f"C {s(cx + r_val)} {s(cy + ctrl_dist)} {s(cx + ctrl_dist)} {s(cy + r_val)} {cx} {s(cy + r_val)} "
        f"C {s(cx - ctrl_dist)} {s(cy + r_val)} {s(cx - r_val)} {s(cy + ctrl_dist)} {s(cx - r_val)} {cy} "
        f"C {s(cx - r_val)} {s(cy - ctrl_dist)} {s(cx - ctrl_dist)} {s(cy - r_val)} {cx} {s(cy - r_val)} Z"
    )

def convert_ellipse(ellipse: ET.Element) -> str:
    """转换椭圆为路径数据"""
    cx = float(ellipse.get("cx", "0"))
    cy = float(ellipse.get("cy", "0"))
    rx = float(ellipse.get("rx", "0"))
    ry = float(ellipse.get("ry", "0"))
    ctrl_dist_x = rx * KAPPA
    ctrl_dist_y = ry * KAPPA
    
    return (
        f"M {cx} {s(cy - ry)} "
        f"C {s(cx + ctrl_dist_x)} {s(cy - ry)} {s(cx + rx)} {s(cy - ctrl_dist_y)} {s(cx + rx)} {cy} "
        f"C {s(cx + rx)} {s(cy + ctrl_dist_y)} {s(cx + ctrl_dist_x)} {s(cy + ry)} {cx} {s(cy + ry)} "
        f"C {s(cx - ctrl_dist_x)} {s(cy + ry)} {s(cx - rx)} {s(cy + ctrl_dist_y)} {s(cx - rx)} {cy} "
        f"C {s(cx - rx)} {s(cy - ctrl_dist_y)} {s(cx - ctrl_dist_x)} {s(cy - ry)} {cx} {s(cy - ry)} Z"
    )

def convert_polygon(poly: ET.Element, is_polyline=False) -> str:
    """转换多边形/折线为路径数据"""
    points = poly.get("points", "")
    points_list = [p.strip() for p in re.split(r'[\s,]', points) if p.strip()]
    
    if len(points_list) % 2 != 0:
        return ""  # 无效的点数据
    
    path_data = []
    for i in range(0, len(points_list), 2):
        cmd = "M" if i == 0 else "L"
        path_data.append(f"{cmd} {points_list[i]} {points_list[i+1]}")
    
    if not is_polyline:
        path_data.append("Z")
    
    return " ".join(path_data)

def convert_element_to_path(elem: ET.Element) -> ET.Element:
    """将SVG元素转换为等效的路径元素"""
    path_data = ""
    elem_type = elem.tag.split('}')[-1]  # 移除命名空间
    
    # 根据元素类型转换路径数据
    if elem_type == "line":
        path_data = convert_line(elem)
    elif elem_type == "rect":
        path_data = convert_rect(elem)
    elif elem_type == "circle":
        path_data = convert_circle(elem)
    elif elem_type == "ellipse":
        path_data = convert_ellipse(elem)
    elif elem_type == "polygon":
        path_data = convert_polygon(elem)
    elif elem_type == "polyline":
        path_data = convert_polygon(elem, is_polyline=True)
    
    # 创建新的路径元素
    if path_data:
        ns = "http://www.w3.org/2000/svg"
        # 创建属性字典，包含fill-rule和stroke-linecap
        attribs = {
            "d": path_data,
            "fill": elem.get("fill", ""),
            "stroke": elem.get("stroke", ""),
            "stroke-width": elem.get("stroke-width", "0")
        }
        # 复制fill-rule属性（如果存在）
        if "fill-rule" in elem.attrib:
            attribs["fill-rule"] = elem.attrib["fill-rule"]
        # 复制stroke-linecap属性（如果存在）
        if "stroke-linecap" in elem.attrib:
            attribs["stroke-linecap"] = elem.attrib["stroke-linecap"]
        
        path_elem = ET.Element(f"{{{ns}}}path", attrib=attribs)
        return path_elem
    return None

def convert_svg_to_avd(svg_content: str) -> str:
    """转换单个 SVG 内容为 AVD XML"""
    # 解析 SVG
    svg_root = ET.fromstring(svg_content)
    ns = "http://www.w3.org/2000/svg"
    
    # 处理 viewBox 属性
    viewbox = svg_root.get("viewBox", "0 0 24 24").split()
    viewport_width = viewbox[2] if len(viewbox) >= 4 else "24"
    viewport_height = viewbox[3] if len(viewbox) >= 4 else "24"
    
    # 创建 VectorDrawable 根元素
    vector_attrib = {
        "xmlns:android": "http://schemas.android.com/apk/res/android",
        "android:width": convert_units(svg_root.get("width", "24dp")),
        "android:height": convert_units(svg_root.get("height", "24dp")),
        "android:viewportWidth": viewport_width,
        "android:viewportHeight": viewport_height
    }
    vector = ET.Element("vector", attrib=vector_attrib)
    
    # 转换所有图形元素
    for elem in svg_root.findall(".//"):
        elem_type = elem.tag.split('}')[-1]
        
        # 处理基本形状（转换为路径）
        if elem_type in ["line", "rect", "circle", "ellipse", "polygon", "polyline"]:
            path_elem = convert_element_to_path(elem)
            if path_elem:
                # 创建新的路径元素并添加到vector
                fill_color = normalize_color(path_elem.get("fill", "#000000"))
                stroke_color = normalize_color(path_elem.get("stroke", "#000000"))
                
                avd_attribs = {
                    "android:pathData": path_elem.get("d", ""),
                    "android:fillColor": fill_color,
                    "android:strokeWidth": path_elem.get("stroke-width", "0"),
                    "android:strokeColor": stroke_color
                }
                # 添加fillType属性（如果存在）
                fill_rule = path_elem.get("fill-rule")
                if fill_rule == "evenodd":
                    avd_attribs["android:fillType"] = "evenOdd"
                # 添加strokeLineCap属性（如果存在）
                stroke_linecap = path_elem.get("stroke-linecap")
                if stroke_linecap in ["round", "square", "butt"]:
                    avd_attribs["android:strokeLineCap"] = stroke_linecap
                
                avd_path = ET.SubElement(vector, "path", avd_attribs)
        
        # 处理路径元素
        elif elem.tag.endswith("path"):
            fill_color = normalize_color(elem.get("fill", "#000000"))
            stroke_color = normalize_color(elem.get("stroke", "#000000"))
            
            avd_attribs = {
                "android:pathData": elem.get("d", ""),
                "android:fillColor": fill_color,
                "android:strokeWidth": elem.get("stroke-width", "0"),
                "android:strokeColor": stroke_color
            }
            # 添加fillType属性（如果存在）
            fill_rule = elem.get("fill-rule")
            if fill_rule == "evenodd":
                avd_attribs["android:fillType"] = "evenOdd"
            # 添加strokeLineCap属性（如果存在）
            stroke_linecap = elem.get("stroke-linecap")
            if stroke_linecap in ["round", "square", "butt"]:
                avd_attribs["android:strokeLineCap"] = stroke_linecap
            
            avd_path = ET.SubElement(vector, "path", avd_attribs)
    
    # 生成格式化 XML
    rough_xml = ET.tostring(vector, "utf-8")
    parsed_xml = minidom.parseString(rough_xml)
    pretty_xml = parsed_xml.toprettyxml(indent="    ")
    
    # 后处理：使每个属性单独一行
    # 匹配开始标签（包括自闭合标签）和XML声明
    pattern = r'(\s*)(<\??[a-zA-Z:_][^>]*?)(\s+)([^>]*?)(/?>)'
    def _format_attributes(match):
        leading_indent = match.group(1)  # 标签前的缩进空白
        tag_start = match.group(2)       # 标签开始部分（含声明）
        whitespace = match.group(3)      # 标签与属性间的空白
        attrs = match.group(4)           # 属性字符串
        tag_end = match.group(5)         # 标签结束部分（> 或 />）
        
        # 跳过XML声明行（保持单行格式）
        if tag_start.startswith("<?xml"):
            return f"{leading_indent}{tag_start}{attrs}{tag_end}"
        
        # 提取所有属性键值对
        attrs_list = re.findall(r'(\S+?=".*?")', attrs)
        if not attrs_list:
            return f"{leading_indent}{tag_start}{tag_end}"
        
        # 每行一个属性，保持缩进
        attr_indent = leading_indent + '    '
        formatted_attrs = "\n" + attr_indent + ("\n" + attr_indent).join(attrs_list)
        
        return f"{leading_indent}{tag_start}{formatted_attrs}{tag_end}"
    
    # 应用属性格式化
    return re.sub(pattern, _format_attributes, pretty_xml)

def batch_convert(input_dir: str, output_dir: str):
    """批量转换目录中的 SVG 文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    converted_count = 0
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".svg"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.xml")
            
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    svg_content = f.read()
                
                avd_xml = convert_svg_to_avd(svg_content)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(avd_xml)
                print(f"✅ Converted: {filename}")
                converted_count += 1
            except Exception as e:
                print(f"❌ Failed to convert {filename}: {str(e)}")
    
    print(f"\nConversion complete! {converted_count} files converted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SVG to Android VectorDrawable Converter")
    parser.add_argument("-i", "--input", required=True, help="Input SVG file or directory")
    parser.add_argument("-o", "--output", required=True, help="Output directory for AVD files")
    parser.add_argument("-r", "--recursive", action="store_true", help="Process directories recursively")
    args = parser.parse_args()
    
    if os.path.isdir(args.input):
        batch_convert(args.input, args.output)
    else:
        # 单个文件转换
        with open(args.input, "r", encoding="utf-8") as f:
            avd_xml = convert_svg_to_avd(f.read())
        
        if not os.path.exists(args.output):
            os.makedirs(args.output)
            
        output_filename = f"{os.path.splitext(os.path.basename(args.input))[0]}.xml"
        output_path = os.path.join(args.output, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(avd_xml)
        print(f"✅ Converted single file: {os.path.basename(args.input)} → {output_filename}")