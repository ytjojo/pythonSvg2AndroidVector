# 转换单个文件
python3 converter.py -i input.svg -o output_dir

# 批量转换目录
python3 converter.py -i svg_dir -o avd_output

# 递归处理子目录
python3 converter.py -i svg_dir -o avd_output -r