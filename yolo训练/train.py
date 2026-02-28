from ultralytics import YOLO

model = YOLO('yolo26n-seg.pt')

results = model.train(
    data='exam_dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name='exam_segment',
    device='cpu',
    patience=20,
    save=True,
    plots=True,
)

print("训练完成！")
print(f"最佳模型保存在: runs/segment/exam_segment/weights/best.pt")
