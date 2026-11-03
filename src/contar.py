import cv2
from pathlib import Path
from ultralytics import YOLO

VIDEO_ENTRADA = "videos/transito.mp4"
VIDEO_SAIDA = "saidas/contagem.mp4"
EXTENSAO = Path(VIDEO_SAIDA).suffix.lower()
VERMELHO = (0, 0, 255)
AZUL = (255, 0, 0)
VERDE = (0, 255, 0)
BRANCO = (255, 255, 255)
LINHA_Y_PROPORCAO = 0.6
CLASSES_CONTADAS = {"car", "truck", "bus", "motorcycle"}

Path(VIDEO_SAIDA).parent.mkdir(parents=True, exist_ok=True)

modelo = YOLO("yolo11n.pt")

capt = cv2.VideoCapture(VIDEO_ENTRADA)
if not capt.isOpened():
    raise SystemExit(f"Não foi possivel abrir o video:{VIDEO_ENTRADA}")

largura = int(capt.get(cv2.CAP_PROP_FRAME_WIDTH))
altura = int(capt.get(cv2.CAP_PROP_FRAME_HEIGHT))

linha_y = int(altura * LINHA_Y_PROPORCAO)

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

escala = largura / 1280
tam_fonte = 1.6 * escala
espessura = max(1, round(2 * escala))

contador_frame = 0
ultima_posicao = {}
ids_contados = set()
contagem = {}
subindo_descendo = {"subindo":0, "descendo":0}
while True:
    ok, frame = capt.read()

    if not ok:
        break

    contador_frame += 1
    print(f"frames:{contador_frame} de {total_frame}", end="\r")

    results = modelo.track(frame, persist=True, tracker="bytetrack.yaml", 
                           imgsz=480, verbose=False)
    result = results[0]
    for caixa in result.boxes:
        x1, y1, x2, y2 = map(int, caixa.xyxy[0])
        class_id = int(caixa.cls[0])
        confianca = float(caixa.conf[0])
        nome = modelo.names[class_id]
        cor = cores.get(nome, BRANCO)

        if nome not in CLASSES_CONTADAS:
            continue

        if caixa.id is None:
            continue

        track_id = int(caixa.id[0])

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        y_anterior = ultima_posicao.get(track_id)

        if y_anterior is not None and track_id not in ids_contados:
            cruzou = None
            if y_anterior < linha_y <= cy:
                cruzou = "descendo"
            elif y_anterior > linha_y >= cy:
                cruzou = "subindo"
            
            if cruzou:
                ids_contados.add(track_id)
                contagem[nome] = contagem.get(nome, 0) + 1
                subindo_descendo[cruzou] += 1
        
        ultima_posicao[track_id] = cy

        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, espessura)

        texto = f"#{track_id} {nome} - {confianca:.2f}"
        (larg_txt, alt_txt), base = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX,
                                                    tam_fonte, espessura)

        y_texto = max(y1 - int(8 * escala), alt_txt + base)

        cv2.rectangle(frame, (x1, y_texto - alt_txt - base), 
                      (x1 + larg_txt, y_texto + base), cor, -1)
        cv2.putText(frame, texto, (x1, y_texto), 
                    cv2.FONT_HERSHEY_SIMPLEX, tam_fonte, BRANCO, espessura)

        cv2.circle(frame, (cx, cy), 4 * espessura, cor, -1)

    altura_linha = int(50 * escala)
    for i, (nome, qtd) in enumerate(contagem.items()):
        y = altura_linha * (i + 2)
        cv2.putText(frame, f"{nome} - {qtd}", (20, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5 * escala, BRANCO, espessura + 1)

    cv2.line(frame, (0, linha_y), (largura, linha_y), (0, 255, 255), espessura)
    total = sum(contagem.values())
    cv2.putText(frame, f"Total: {total}", (20, altura_linha), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5 * escala, BRANCO, espessura + 1)

    

    gravador.write(frame)

capt.release()
gravador.release()

print(f"Finalizado - video salvo em {VIDEO_SAIDA}")
print("Resumo da contagem:")
for nome, qtd in contagem.items():
    print(f"{nome}: {qtd}")
print(f"Total: {sum(contagem.values())}")
print(f"subiram: {subindo_descendo['subindo']} desceram: {subindo_descendo['descendo']}")