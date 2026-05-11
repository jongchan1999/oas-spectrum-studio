# ✅ generate_linux.py (원본 구조 유지 + 경로만 리눅스 기준으로 수정)

import os
import numpy as np
import pandas as pd
import time
from glob import glob
import matplotlib.pyplot as plt
import random

ref = pd.read_csv("/home/ubuntu/final_optimized_code_for_paper/Cross_sections_out/interpolated_cross_section.txt", delimiter='\t', header=None)
ref = ref.values
Wavelength = ref[:, 0]
O3, NO, NO2, NO3, HONO, N2O4, N2O5, HONO2 = ref[:, 1:].T

img_dir = "/home/ubuntu/final_optimized_code_for_paper/simulated"
num_images = 1000

def generate():
    idx_img = 1
    while True:
        eps = 0.0001
        step_size = 0.001
        try:
            if idx_img % 6 == 1:
                a = np.random.choice(np.arange(102.0, 543.0+eps, step_size)); b = 0.0
                c = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                d = np.random.choice(np.arange(42.40, 520.0+eps, step_size))
                e = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                f = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                g = np.random.choice(np.arange(0.0, 400.0+eps, step_size))
                h = np.random.choice([0.0, np.random.choice(np.arange(0.0, 100+eps, step_size))])
            elif idx_img % 6 == 2:
                a = np.random.choice(np.arange(10.2, 543.0+eps, step_size)); b = 0.0
                c = np.random.choice(np.arange(50.0, 600.0+eps, step_size))
                d = np.random.choice(np.arange(42.4, 520.0+eps, step_size))
                e = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                f = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                g = np.random.choice(np.arange(300.0, 900.0+eps, step_size))
                h = np.random.choice([0.0, np.random.choice(np.arange(0.0, 100+eps, step_size))])
            elif idx_img % 6 == 3:
                a = np.random.choice(np.arange(10.1, 200.0+eps, step_size)); b = 0.0
                c = np.random.choice(np.arange(466.0, 8640.0+eps, step_size))
                d = np.random.choice(np.arange(30.0, 100.04+eps, step_size))
                e = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                f = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                g = np.random.choice(np.arange(155.0, 900.0+eps, step_size))
                h = np.random.choice([0.0, np.random.choice(np.arange(10.0, 1000.0+eps, step_size))])
            elif idx_img % 6 == 4:
                a = b = 0.0
                c = np.random.choice(np.arange(9190.0, 12100.0+eps, step_size))
                d = np.random.choice([0.0, np.random.choice(np.arange(0.0, 30+eps, step_size))])
                e = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
                f = np.random.choice(np.arange(107.0, 185.0+eps, step_size))
                g = np.random.choice(np.arange(10.5, 155.0+eps, step_size))
                h = np.random.choice(np.arange(500.0, 1500.0+eps, step_size))
            elif idx_img % 6 == 5:
                a = 0.0
                b = np.random.choice(np.arange(21.2, 360.0+eps, step_size))
                c = np.random.choice(np.arange(9290.0, 11100.0+eps, step_size))
                d = np.random.choice([0.0, np.random.choice(np.arange(0.0, 30+eps, step_size))])
                e = np.random.choice([0.0, np.random.choice(np.arange(0.0, 535.0+eps, step_size))])
                f = np.random.choice(np.arange(27.4, 196.0+eps, step_size))
                g = np.random.choice([0.0, np.random.choice(np.arange(0.0, 50.0+eps, step_size))])
                h = np.random.choice(np.arange(10.0, 1000.0+eps, step_size))
            elif idx_img % 6 == 0:
                a = 0.0
                b = np.random.choice(np.arange(329.0, 476.0+eps, step_size))
                c = np.random.choice(np.arange(6000.0, 13100.0+eps, step_size))
                d = np.random.choice([0.0, np.random.choice(np.arange(0.0, 30+eps, step_size))])
                e = np.random.choice(np.arange(10.9, 535.0+eps, step_size))
                f = np.random.choice([0.0, np.random.choice(np.arange(0, 27.4+eps, step_size))])
                g = np.random.choice([0.0, np.random.choice(np.arange(0.0, 50.0+eps, step_size))])
                h = np.random.choice([0.0, np.random.choice(np.arange(0.0, 10.0+eps, step_size))])
            
            if idx_img % 13 == 0:
                if idx_img % 2 == 0:
                    a = 0.0
                    b = 0.0
                    c = 0.0
                    d = 0.0
                    e = 0.0
                    f = 0.0
                    g = 0.0
                    h = 0.0
                else:
                    a = np.random.choice([0.0, np.random.choice(np.arange(0.0, 543.0+eps, step_size))])
                    b = np.random.choice([0.0, np.random.choice(np.arange(0.0, 476.0+eps, step_size))])
                    c = np.random.choice([0.0, np.random.choice(np.arange(0.0, 13100.0+eps, step_size))])
                    d = np.random.choice([0.0, np.random.choice(np.arange(0.0, 520.0+eps, step_size))])
                    e = np.random.choice([0.0, np.random.choice(np.arange(0.0, 535.0+eps, step_size))])
                    f = np.random.choice([0.0, np.random.choice(np.arange(0.0, 196.0+eps, step_size))])
                    g = np.random.choice([0.0, np.random.choice(np.arange(0.0, 900.0+eps, step_size))])
                    h = np.random.choice([0.0, np.random.choice(np.arange(0.0, 1500.0+eps, step_size))])

            plot = a * 1E14 * O3 + b * 1E14 * NO + c * 1E12 * NO2 + d * 1E12 * NO3 + \
                   e * 1E12 * HONO + f * 1E11 * N2O4 + g * 1E13 * N2O5 + h * 1E13 * HONO2
            plot = plot * 15 + (np.random.rand(len(plot)) - 0.5) * 6E-3

            filename = f'idx_{idx_img}_a_{a:.3f}_b_{b:.3f}_c_{c:.3f}_d_{d:.3f}_e_{e:.3f}_f_{f:.3f}_g_{g:.3f}_h_{h:.3f}.png'
            final_path = os.path.join(img_dir, filename)
            
            fig = plt.figure(figsize=(6.4, 5.0), dpi=100)
            ax = plt.gca()
            ax.set_position([0.05, 0.05, 0.9, 0.9])  # axes를 figure 전체에 꽉 차게 확장
            plt.semilogy(Wavelength, np.ma.masked_where(((plot < 1E-4) | (plot > 1.75)), plot), '-k', linewidth=2)
            plt.axis('off'); plt.xlim([203, 670]); plt.ylim([1E-4, 1E+1])
            ax.set_xticklabels([]); ax.set_yticklabels([])
            plt.savefig(final_path, dpi=100)

            try:
                plt.savefig(final_path, bbox_inches=None, pad_inches=0)
                plt.close()

                if os.path.exists(final_path) and os.path.getsize(final_path) > 1024:
                    pass
                else:
                    print(f"[WARNING] Invalid image file skipped: {final_path}")
                    continue
            except Exception as e:
                print(f"[ERROR] Saving image failed: {e}")
                plt.close()
                continue

            try:
                img_files_rm = glob(os.path.join(img_dir, f'idx_{idx_img}_*'))
                for img_file in img_files_rm:
                    if final_path not in img_file:
                        try:
                            os.remove(img_file)
                        except PermissionError as e:
                            print(f"[WARNING] PermissionError removing image {img_file}: {e}")
            except Exception as e:
                print(f"[WARNING] Error scanning/deleting old images: {e}")

        except Exception as e:
            print(f"[ERROR] Unexpected error during generation at idx {idx_img}: {e}")

        idx_img = 1 if idx_img == num_images else idx_img + 1
        time.sleep(0.05)

if __name__ == '__main__':
    generate()
