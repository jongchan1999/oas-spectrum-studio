# ✅ RegressionModel_linux.py (ClippedReLU 제거, ReLU 분기만 유지)
import torch
import torch.nn as nn
import torchvision.models as models

class CNNModel(nn.Module):
    def __init__(self, num_classes=8, exp_id=1):
        super(CNNModel, self).__init__()
        self.backbone = models.resnet101(weights='DEFAULT')
        for param in self.backbone.parameters():
            param.requires_grad = True
        in_features = self.backbone.fc.in_features

        if exp_id in [1, 2, 3, 4]:
            self.backbone.fc = nn.Sequential(
                #nn.Dropout(0.2),
                nn.Linear(in_features, num_classes),
                nn.ReLU()
            )
        else:
            self.backbone.fc = nn.Linear(in_features, num_classes)

    def forward(self, x):
        return self.backbone(x)
