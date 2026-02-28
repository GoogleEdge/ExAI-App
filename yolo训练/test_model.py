from ultralytics import YOLO
import cv2
from pathlib import Path

model_path = r'yolo_model.pt'
model = YOLO(model_path)

test_image = r'D:\代码\2026srsc\yolo部分\待处理数据集\0093.jpg'

results = model(test_image, conf=0.3, iou=0.5)

print(f"置信度阈值: 0.3")
print(f"测试图片: {test_image}")

for i, result in enumerate(results):
    img = result.orig_img.copy()
    
    print(f"检测框数量: {len(result.boxes) if result.boxes else 0}")
    print(f"掩码数量: {len(result.masks) if result.masks else 0}")
    
    if result.boxes is not None and len(result.boxes) > 0:
        for j, box in enumerate(result.boxes):
            conf = box.conf[0].item()
            print(f"  检测 {j+1}: 置信度 {conf:.3f}")
    
    if result.masks is not None:
        for j, mask in enumerate(result.masks):
            mask_array = mask.data.cpu().numpy()[0]
            mask_resized = cv2.resize(mask_array.astype('uint8') * 255, 
                                       (img.shape[1], img.shape[0]))
            
            contours, _ = cv2.findContours(mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(img, contours, -1, (0, 255, 0), 2)
            
            if len(contours) > 0:
                x, y, w, h = cv2.boundingRect(contours[0])
                cv2.putText(img, f'Q{j+1}', (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    output_path = r'D:\代码\2026srsc\yolo部分\待处理数据集\0093_result1.jpg'
    cv2.imwrite(str(output_path), img)
    print(f"\n结果已保存: {output_path}")

print("\n测试完成！")
