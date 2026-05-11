
# ✅ train_linux.py (정규화별 loss/recon 분기 + 안정성 보완 + ClippedReLU 제거)
import os
#os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
#os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
import re
import csv
import shutil
import argparse
import torch
import time
import numpy as np
from glob import glob
from tqdm import tqdm
from PIL import Image, UnidentifiedImageError
from torch.utils.data import Dataset, DataLoader, random_split
import torch.nn as nn
from RegressionModel_linux import CNNModel

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
torch.cuda.empty_cache()

parser = argparse.ArgumentParser()
parser.add_argument('--exp_id', type=int, required=True)
args = parser.parse_args()
exp_id = args.exp_id

base_path = "/home/ubuntu/final_optimized_code_for_paper"
snapshot_dir = os.path.join(base_path, "snapshot", f"exp_{exp_id}")
simulated_dir = os.path.join(base_path, "simulated")
log_dir = os.path.join(base_path, "logs", f"exp_{exp_id}")
model_dir = os.path.join(base_path, "model", f"exp_{exp_id}")
os.makedirs(snapshot_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)
os.makedirs(model_dir, exist_ok=True)

max_vals = torch.tensor([543.0, 476.0, 13100.0, 520.0, 535.0, 196.0, 900.0, 1500.0])
factors = torch.tensor([1e14, 1e14, 1e12, 1e12, 1e12, 1e11, 1e13, 1e13])
label_weights = torch.tensor([3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0])
ref = torch.tensor(np.loadtxt(os.path.join(base_path, "Cross_sections_out", "interpolated_cross_section.txt")), dtype=torch.float32)
wavelength_ref = ref[:, 0]
ref_data = ref[:, 1:]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
max_vals, factors, label_weights = max_vals.to(device), factors.to(device), label_weights.to(device)
ref_data = ref_data.to(device)

def generate_snapshot(n=1000):
    os.makedirs(snapshot_dir, exist_ok=True)
    for f in os.listdir(snapshot_dir):
        try:
            os.remove(os.path.join(snapshot_dir, f))
        except Exception as e:
            print(f"[WARNING] Failed to remove {f}: {e}")

    all_files = glob(os.path.join(simulated_dir, "idx_*.png"))
    valid_files = []
    for f in all_files:
        if os.path.isfile(f):
            valid_files.append(f)

    def safe_getmtime(path):
        try:
            return os.path.getmtime(path)
        except FileNotFoundError:
            return 0  # 존재하지 않는 파일은 오래된 파일 취급

    files = sorted(valid_files, key=safe_getmtime, reverse=True)[:n]

    for f in files:
        try:
            shutil.copy(f, snapshot_dir)
        except FileNotFoundError:
            print(f"[WARNING] Skipped missing file: {f}")
        except Exception as e:
            print(f"[ERROR] Failed to copy {f}: {e}")

    print(f"[INFO] Copied {len(files)} images to snapshot.")

class RegressionDataset(Dataset):
    def __init__(self, dir_path):
        self.paths = sorted(glob(os.path.join(dir_path, "idx_*.png")))

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img_path = self.paths[idx]
        try:
            with Image.open(img_path) as img:
                img.load()
                img = img.convert('RGB').resize((640, 500))
                image = torch.FloatTensor(np.array(img).transpose(2, 0, 1) / 255.0)
            label = re.findall(r"\d+\.\d+", img_path)
            if len(label) != 8:
                raise ValueError(f"Label parsing failed for {img_path}")
            label = torch.FloatTensor([float(x) for x in label])
            return image, label
        except Exception as e:
            print(f"[ERROR] Failed to load {img_path}: {e}")
            return None

def collate_fn(batch):
    batch = [b for b in batch if b is not None]
    if not batch:
        return None
    images, labels = zip(*batch)
    return torch.stack(images), torch.stack(labels)

def main():
    epochs = 5000
    batch_size = 16
    learning_rate = 0.0005
    lambda_reg = 1.0
    lambda_rec = 1.0
    best_val_loss = float('inf')

    model = CNNModel(num_classes=8, exp_id=exp_id).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion_reg = nn.MSELoss(reduction='none')
    criterion_rec = nn.MSELoss()

    log_file = open(os.path.join(log_dir, "train_log.csv"), "w", newline="")
    logger = csv.writer(log_file)
    logger.writerow(["epoch", "train_loss", "reg_loss", "rec_loss", "val_total", "val_reg", "val_rec"])

    for epoch in range(1, epochs + 1):
        print(f"\n=== Epoch {epoch} ===")
        generate_snapshot()

        dataset = RegressionDataset(snapshot_dir)
        train_len = int(0.7 * len(dataset))
        val_len = len(dataset) - train_len
        train_set, val_set = random_split(dataset, [train_len, val_len])

        train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=0, collate_fn=collate_fn)
        val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=0, collate_fn=collate_fn)

        model.train()
        total, reg_sum, rec_sum, count = 0, 0, 0, 0
        eps = 1e-6

        def norm_out(out):
            if exp_id == 1 or exp_id == 5:
                return out / max_vals
            elif exp_id == 2 or exp_id == 6:
                return out
            elif exp_id == 3 or exp_id == 7:
                return out / 100.0
            elif exp_id == 4 or exp_id == 8:
                return out / 1000.0

        for batch in tqdm(train_loader, ncols=100):
            R = (torch.rand(wavelength_ref.shape[0]) - 0.5) * 6E-3
            R = R.to(device)
            if batch is None:
                continue
            images, labels = batch[0].to(device), batch[1].to(device)
            optimizer.zero_grad()

            out = model(images)
            label_norm = labels / max_vals
            out_norm = norm_out(out)
            loss_reg = (criterion_reg(out_norm, label_norm) * label_weights).mean()

            recon_input = out_norm * max_vals * factors
            spectra = labels * factors
            recon = torch.matmul(recon_input, ref_data.T) * 15 + R
            spectra = torch.matmul(spectra, ref_data.T) * 15 + R
            loss_rec = criterion_rec(torch.log10(torch.clamp(recon, min=eps)), torch.log10(torch.clamp(spectra, min=eps)))

            loss = lambda_reg * loss_reg + lambda_rec * loss_rec
            loss.backward()
            optimizer.step()

            bs = images.size(0)
            total += loss.item() * bs
            reg_sum += loss_reg.item() * bs
            rec_sum += loss_rec.item() * bs
            count += bs

        train_total = total / count if count > 0 else 0.0
        train_reg = reg_sum / count if count > 0 else 0.0
        train_rec = rec_sum / count if count > 0 else 0.0

        # Validation
        model.eval()
        v_total = v_reg = v_rec = v_count = 0
        with torch.no_grad():
            for batch in val_loader:
                R = (torch.rand(wavelength_ref.shape[0]) - 0.5) * 6E-3
                R = R.to(device)
                if batch is None:
                    continue
                images, labels = batch[0].to(device), batch[1].to(device)
                out = model(images)

                label_norm = labels / max_vals
                out_norm = norm_out(out)
                loss_reg = (criterion_reg(out_norm, label_norm) * label_weights).mean()

                recon_input = out_norm * max_vals * factors
                spectra = labels * factors
                recon = torch.matmul(recon_input, ref_data.T) * 15 + R
                spectra = torch.matmul(spectra, ref_data.T) * 15 + R
                loss_rec = criterion_rec(torch.log10(torch.clamp(recon, min=eps)), torch.log10(torch.clamp(spectra, min=eps)))
                loss = lambda_reg * loss_reg + lambda_rec * loss_rec

                bs = images.size(0)
                v_total += loss.item() * bs
                v_reg += loss_reg.item() * bs
                v_rec += loss_rec.item() * bs
                v_count += bs

        val_total = v_total / v_count if v_count > 0 else 0.0
        val_reg = v_reg / v_count if v_count > 0 else 0.0
        val_rec = v_rec / v_count if v_count > 0 else 0.0

        print(f"Train  : Total={train_total:.4f}, Reg={train_reg:.4f}, Rec={train_rec:.4f}")
        print(f"Val    : Total={val_total:.4f}, Reg={val_reg:.4f}, Rec={val_rec:.4f}")

        logger.writerow([epoch, train_total, train_reg, train_rec, val_total, val_reg, val_rec])
        log_file.flush()

        if epoch % 500 == 0:
            torch.save(model.state_dict(), os.path.join(model_dir, f"epoch_{epoch}.pth"))

        if epoch == 1 or val_total < best_val_loss:
            best_val_loss = val_total
            torch.save(model.state_dict(), os.path.join(model_dir, f"best_model_epoch_{epoch}_.pth"))

        time.sleep(5)

    log_file.close()

if __name__ == '__main__':
    main()
