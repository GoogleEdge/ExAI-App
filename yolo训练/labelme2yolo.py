import json
import os
from pathlib import Path
from collections import defaultdict

base_dir = Path(r'c:\Users\10732\Documents\代码\2026srsc\yolo部分')

images_train = base_dir / 'exam_dataset/images/train'
images_val = base_dir / 'exam_dataset/images/val'
labels_train = base_dir / 'exam_dataset/labels/train'
labels_val = base_dir / 'exam_dataset/labels/val'

def convert_labelme_to_yolo(json_path, output_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    img_width = data['imageWidth']
    img_height = data['imageHeight']
    
    yolo_lines = []
    
    for shape in data.get('shapes', []):
        label = shape['label']
        points = shape['points']
        group_id = shape.get('group_id')
        shape_type = shape['shape_type']
        
        if shape_type == 'polygon':
            normalized_points = []
            for x, y in points:
                nx = x / img_width
                ny = y / img_height
                normalized_points.extend([nx, ny])
            
            class_id = 0
            line = f"{class_id} " + " ".join(f"{p:.6f}" for p in normalized_points)
            yolo_lines.append((group_id, line))
            
        elif shape_type == 'rectangle':
            x1, y1 = points[0]
            x2, y2 = points[1]
            
            rect_points = [
                (x1, y1),
                (x2, y1),
                (x2, y2),
                (x1, y2)
            ]
            
            normalized_points = []
            for x, y in rect_points:
                nx = x / img_width
                ny = y / img_height
                normalized_points.extend([nx, ny])
            
            class_id = 0
            line = f"{class_id} " + " ".join(f"{p:.6f}" for p in normalized_points)
            yolo_lines.append((group_id, line))
    
    output_file = output_dir / (json_path.stem + '.txt')
    with open(output_file, 'w') as f:
        for _, line in yolo_lines:
            f.write(line + '\n')
    
    return len(yolo_lines), [g for g, _ in yolo_lines if g is not None]

def process_directory(image_dir, label_dir):
    json_files = list(image_dir.glob('*.json'))
    total = 0
    all_group_ids = []
    
    for json_file in json_files:
        count, group_ids = convert_labelme_to_yolo(json_file, label_dir)
        total += count
        all_group_ids.extend(group_ids)
        print(f"转换: {json_file.name} -> {count} 个标注" + (f" (Group IDs: {group_ids})" if group_ids else ""))
    
    return len(json_files), total, all_group_ids

print("转换训练集...")
train_files, train_labels, train_groups = process_directory(images_train, labels_train)
print(f"训练集: {train_files} 个文件, {train_labels} 个标注\n")

print("转换验证集...")
val_files, val_labels, val_groups = process_directory(images_val, labels_val)
print(f"验证集: {val_files} 个文件, {val_labels} 个标注\n")

if train_groups or val_groups:
    print(f"检测到跨页标注 (Group ID): {set(train_groups + val_groups)}")
    print("提示: 跨页题目需要在后处理中根据 Group ID 合并")

print("转换完成！")
