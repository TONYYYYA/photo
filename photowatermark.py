#!/usr/bin/env python3
import os
import sys
import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ExifTags


def get_capture_date(image_path):
    """从图片EXIF信息中获取拍摄日期，返回YYYY-MM-DD格式"""
    try:
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            if not exif_data:
                return None

            # 查找EXIF中的拍摄时间标签
            date_tags = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]
            for tag_id in exif_data:
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag in date_tags:
                    date_str = exif_data[tag_id]
                    try:
                        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").strftime("%Y-%m-%d")
                    except ValueError:
                        continue
            return None
    except Exception as e:
        print(f"警告: 无法读取 {os.path.basename(image_path)} 的拍摄时间 - {str(e)}")
        return None


def add_watermark(input_path, output_path, text, font_size=30, color=(255, 255, 255), position='bottom_right'):
    """给图片添加水印并保存"""
    try:
        with Image.open(input_path) as img:
            # 处理图片模式以支持水印绘制
            if img.mode in ('RGBA', 'LA'):
                background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
                background.paste(img, img.split()[-1])
                img = background.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            draw = ImageDraw.Draw(img)

            # 尝试加载系统字体
            font = None
            system_fonts = [
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf"  # Windows
            ]

            for font_path in system_fonts:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except:
                        continue

            if not font:
                font = ImageFont.load_default()
                print("提示: 使用默认字体")

            # 计算文本尺寸
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            img_width, img_height = img.size
            padding = 10

            # 确定水印位置
            positions = {
                'top_left': (padding, padding),
                'top_right': (img_width - text_width - padding, padding),
                'bottom_left': (padding, img_height - text_height - padding),
                'bottom_right': (img_width - text_width - padding, img_height - text_height - padding),
                'center': ((img_width - text_width) // 2, (img_height - text_height) // 2)
            }

            x, y = positions.get(position, positions['bottom_right'])

            # 绘制半透明背景和水印文本
            draw.rectangle(
                [(x - 2, y - 2), (x + text_width + 2, y + text_height + 2)],
                fill=(0, 0, 0, 128)  # 半透明黑色背景
            )
            draw.text((x, y), text, font=font, fill=color)

            # 保存图片
            img.save(output_path)
            return True
    except Exception as e:
        print(f"错误: 处理 {os.path.basename(input_path)} 失败 - {str(e)}")
        return False


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='给图片添加拍摄时间水印')
    parser.add_argument('image_path', help='图片文件路径或包含图片的目录')
    parser.add_argument('--font-size', type=int, default=30, help='水印字体大小，默认30')
    parser.add_argument('--color', default='255,255,255', help='水印颜色(RGB)，默认白色(255,255,255)')
    parser.add_argument('--position',
                        choices=['top_left', 'top_right', 'bottom_left', 'bottom_right', 'center'],
                        default='bottom_right',
                        help='水印位置，默认右下角')

    args = parser.parse_args()

    # 解析颜色参数
    try:
        color = tuple(map(int, args.color.split(',')))
        if len(color) != 3 or any(c < 0 or c > 255 for c in color):
            raise ValueError
    except ValueError:
        print("警告: 无效的颜色值，使用默认白色")
        color = (255, 255, 255)

    # 收集所有图片文件
    image_files = []
    if os.path.isdir(args.image_path):
        # 处理目录中的所有图片
        for filename in os.listdir(args.image_path):
            file_path = os.path.join(args.image_path, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                image_files.append(file_path)
    elif os.path.isfile(args.image_path) and args.image_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
        # 处理单个图片文件
        image_files.append(args.image_path)
    else:
        print("错误: 无效的图片路径或文件格式")
        sys.exit(1)

    if not image_files:
        print("错误: 没有找到图片文件")
        sys.exit(1)

    # 创建输出目录
    base_dir = os.path.dirname(image_files[0]) if len(image_files) == 1 else args.image_path
    output_dir = os.path.join(base_dir, f"{os.path.basename(base_dir)}_watermark")
    os.makedirs(output_dir, exist_ok=True)
    print(f"信息: 处理后的图片将保存到 {output_dir}")

    # 处理图片
    success_count = 0
    for file_path in image_files:
        filename = os.path.basename(file_path)
        print(f"\n处理: {filename}")

        # 获取水印文本
        watermark_text = get_capture_date(file_path)
        if not watermark_text:
            watermark_text = datetime.now().strftime("%Y-%m-%d")
            print(f"提示: 无法获取拍摄时间，使用当前日期 {watermark_text}")

        # 构建输出路径
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(output_dir, f"{name}_watermark{ext}")

        # 添加水印
        if add_watermark(file_path, output_path, watermark_text, args.font_size, color, args.position):
            print(f"成功: 已保存到 {os.path.basename(output_path)}")
            success_count += 1

    # 显示处理结果
    print(f"\n处理完成: {success_count}/{len(image_files)} 个文件处理成功")
    print("version 1.0")


if __name__ == "__main__":
    main()
