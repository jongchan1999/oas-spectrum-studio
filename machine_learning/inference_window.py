import os
import numpy as np
import matplotlib.pyplot as plt
import torch
from RegressionModel_linux import CNNModel
import argparse
import pandas as pd
from PIL import Image
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# === 설정 ===
wavelength_min, wavelength_max = 203, 670
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # ✅ CPU fallback

# === 파서 ===
parser = argparse.ArgumentParser()
parser.add_argument("--measured", type=str, required=True)
parser.add_argument("--reference", type=str, required=True)
parser.add_argument("--noise_measured", type=str, required=True)
parser.add_argument("--noise_reference", type=str, required=True)
parser.add_argument("--model_path", type=str, required=True)
parser.add_argument("--output_dir", type=str, default="inference_overlay_outputs")
parser.add_argument("--exp_id", type=int, default=1)
parser.add_argument("--cross_section", type=str, default="Cross_sections_out/interpolated_cross_section.txt")  # ✅ 경로 외부에서도 가능하게
args = parser.parse_args()

os.makedirs(args.output_dir, exist_ok=True)

# === 상수 ===
max_vals = torch.tensor([543.0, 476.0, 13100.0, 520.0, 535.0, 196.0, 900.0, 1500.0], device=device)
factors = torch.tensor([1e14, 1e14, 1e12, 1e12, 1e12, 1e11, 1e13, 1e13], device=device)
ref = pd.read_csv(args.cross_section, delimiter="\t", header=None).values  # ✅ 상대 경로 허용
wavelength_ref = ref[:, 0]
cross_sections = torch.tensor(ref[:, 1:], dtype=torch.float32).T.to(device)  # [8, 1038]

# === Optical Depth 계산 함수 ===
def parse_txt(filepath):
    data = []
    with open(filepath, "r") as f:
        for line in f:
            try:
                values = list(map(float, line.strip().split()))
                if len(values) == 2:
                    data.append(values)
            except ValueError:
                continue
    arr = np.array(data)
    mask = (arr[:, 0] >= wavelength_min) & (arr[:, 0] <= wavelength_max)
    return arr[mask]

def compute_OD(I0, I):
    eps = 1e-8
    return np.log(np.clip(I0[:, 1], eps, None) / np.clip(I[:, 1], eps, None))

# === 데이터 불러오기 ===
I0 = parse_txt(args.reference)
I = parse_txt(args.measured)
I0_noise = parse_txt(args.noise_reference)
I_noise = parse_txt(args.noise_measured)

od_measured = compute_OD(I0, I)
od_noise = compute_OD(I0_noise, I_noise)
od_threshold = np.percentile(od_noise, 95)

# === 이미지 생성용 텐서 변환 (train과 해상도 맞춤) ===
def prepare_image(od_values):
    R = (np.random.rand(len(od_values)) - 0.5) * 6E-3  # 동일한 방식의 노이즈 추가
    od_noisy = od_values + R

    # 마스킹 및 클리핑 (학습과 동일)
    od_masked = np.ma.masked_where((od_noisy < 1E-4) | (od_noisy > 1.75), od_noisy)
    norm = np.clip(od_masked, 0, 2) / 2
    norm = norm.filled(0.0)  # 마스크 영역은 0

    # 이미지 생성
    img_array = np.tile(norm, (500, 1)) * 255
    img_array = img_array.astype(np.uint8)
    img = Image.fromarray(img_array).convert("RGB").resize((640, 500))
    img_tensor = torch.FloatTensor(np.array(img).transpose(2, 0, 1)) / 255.0
    return img_tensor.unsqueeze(0).to(device)  # [1, 3, 500, 640]

img_tensor = prepare_image(od_measured)

# === 모델 로드 및 예측 ===
model = CNNModel(num_classes=8, exp_id=args.exp_id).to(device)
model.load_state_dict(torch.load(args.model_path, map_location=device))
model.eval()

with torch.no_grad():
    pred = model(img_tensor)[0]  # [8]

# === 추론 복원 ===
if args.exp_id in [1, 5]:
    pred_real = (pred / max_vals) * max_vals
elif args.exp_id in [2, 6]:
    pred_real = pred * max_vals
elif args.exp_id in [3, 7]:
    pred_real = (pred / 100.0) * max_vals
elif args.exp_id in [4, 8]:
    pred_real = (pred / 1000.0) * max_vals
else:
    pred_real = pred * max_vals

# threshold 이하 제거
threshold_tensor = torch.tensor(od_threshold, device=device)
pred_real[pred_real < threshold_tensor] = 0.0

# === 재구성 OD 생성 ===
pred_od = (pred_real * factors).unsqueeze(1) * cross_sections * 15  # [8, 1038]
reconstructed_OD = pred_od.sum(dim=0).cpu().numpy()

# === Uniform noise 추가 (학습과 동일 방식)
noise = (np.random.rand(len(reconstructed_OD)) - 0.5) * 6E-3
reconstructed_OD += noise

# === Plot ===
plt.figure(figsize=(6.4, 5.0))
plt.semilogy(I[:, 0], od_measured, '-k', linewidth=2, label="Measured OD")
plt.semilogy(wavelength_ref, reconstructed_OD, '-r', linewidth=2, label="Predicted OD")
plt.xlim([203, 670])
plt.ylim([1e-4, 1e+1])
plt.axis("off")
plt.tight_layout()

# 예측값을 파일 이름에 삽입
chem_names = ['a','b','c','d','e','f','g','h']
chem_values = [f"{k:.3f}" for k in pred_real.cpu().numpy()]
pred_str = "_".join([f"{k}_{v}" for k, v in zip(chem_names, chem_values)])
save_path = os.path.join(args.output_dir, f"compare_overlay_{pred_str}.png")

plt.savefig(save_path, dpi=300)
plt.close()

print(f"[✓] Saved overlay image to: {save_path}")