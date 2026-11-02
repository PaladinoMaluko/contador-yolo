import cv2
from pathlib import Path
from ultralytics import YOLO

VIDEO_ENTRADA = "videos/transito.mp4"
VIDEO_SAIDA = "saidas/detectado.mp4"
EXTENSAO = Path(VIDEO_ENTRADA).suffix.lower()
VERMELHO = (0, 0, 255)
AZUL = (255, 0, 0)
VERDE = (0, 255, 0)
BRANCO = (255, 255, 255)


modelo = YOLO("yolo11n.pt")


capt = cv2.VideoCapture(VIDEO_ENTRADA)
if not capt.isOpened():
    raise SystemExit(f"Não foi possivel abrir o video:{VIDEO_ENTRADA}")

largura = int(capt.get(cv2.CAP_PROP_FRAME_WIDTH))
altura = int(capt.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = capt.get(cv2.CAP_PROP_FPS)
total_frame = int(capt.get(cv2.CAP_PROP_FRAME_COUNT))

tipo_gravador = {
    ".mp4":"mp4v",
    ".avi":"MJPG"
}

if EXTENSAO not in tipo_gravador:
    raise SystemExit(f"Extensão não suportada: {EXTENSAO}")

fourcc = cv2.VideoWriter_fourcc(*tipo_gravador[EXTENSAO])
gravador = cv2.VideoWriter(VIDEO_SAIDA, fourcc, fps, (largura, altura))

if not gravador.isOpened():
    raise SystemExit(f"Não foi possivel criar o video:{VIDEO_SAIDA}")

cores = {
    "car":VERDE,
    "truck":VERMELHO,
    "bus":AZUL
}

contador_frame = 0
while True:
    ok, frame = capt.read()

    if not ok:
        break

    contador_frame += 1
    print(f"frames:{contador_frame} de {total_frame}", end="\r")

    results = modelo(frame, imgsz=480, verbose=False)
    result = results[0]
    for caixa in result.boxes:
        x1, y1, x2, y2 = map(int, caixa.xyxy[0])
        class_id = int(caixa.cls[0])
        confianca = float(caixa.conf[0])
        nome = modelo.names[class_id]
        cor = cores.get(nome, BRANCO)

        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)

        y_texto = max(y1 - 8, 15)

        texto = f"{nome} - {confianca:.2f}"
        cv2.putText(frame, texto, (x1, y_texto), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)
        
    gravador.write(frame)

capt.release()
gravador.release()
print(f"Finalizado - video salvo em {VIDEO_SAIDA}")