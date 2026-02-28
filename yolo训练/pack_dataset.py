import shutil
from pathlib import Path

base_dir = Path(r'c:\Users\10732\Documents\代码\2026srsc\yolo部分')
output_zip = base_dir / 'exam_dataset_colab.zip'

exam_dataset = base_dir / 'exam_dataset'

shutil.make_archive(
    str(output_zip.with_suffix('')),
    'zip',
    exam_dataset
)

print(f"数据集已打包: {output_zip}")
print(f"文件大小: {output_zip.stat().st_size / 1024 / 1024:.2f} MB")
