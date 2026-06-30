import os
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score
from fusion_model import AuthenticEyeFusionMLP

def train_fusion_model(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    if not os.path.exists(args.features_file):
        raise FileNotFoundError(
            f"{args.features_file} not found. Run scripts/extract_features.py first; "
            "training a production fusion model on dummy data is disabled."
        )

    data = torch.load(args.features_file)
    X = data['features']
    y = data['labels']

    if X.ndim != 2 or X.shape[1] != 16:
        raise ValueError(f"Expected features with shape [N, 16], got {tuple(X.shape)}")
    if y.ndim == 1:
        y = y.unsqueeze(1)
    if len(X) != len(y):
        raise ValueError(f"Feature/label length mismatch: {len(X)} features vs {len(y)} labels")
        
    y_np = y.numpy()
    X_train, X_val, y_train, y_val = train_test_split(
        X.numpy(), y_np, test_size=0.2, random_state=42, stratify=y_np.reshape(-1)
    )
    
    train_ds = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
    val_ds = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
    
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)
    
    model = AuthenticEyeFusionMLP(input_dim=16).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    best_val_auc = 0.0
    
    for epoch in range(args.epochs):
        model.train()
        train_loss = 0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        scheduler.step()
        
        model.eval()
        val_loss = 0
        all_preds = []
        all_targets = []
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
                
                probs = torch.sigmoid(outputs)
                all_preds.extend(probs.cpu().numpy())
                all_targets.extend(batch_y.cpu().numpy())
                
        auc = roc_auc_score(all_targets, all_preds)
        print(f"Epoch {epoch+1}/{args.epochs} | "
              f"Train Loss: {train_loss/len(train_loader):.4f} | "
              f"Val Loss: {val_loss/len(val_loader):.4f} | AUC: {auc:.4f}")
              
        if auc > best_val_auc:
            best_val_auc = auc
            torch.save(model.state_dict(), args.save_path)
            
    print(f"Finished. Best AUC: {best_val_auc:.4f}")

def main(args_list=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--features_file", type=str, default="extracted_features.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--save_path", type=str, default="fusion_mlp.pth")
    args = parser.parse_args(args_list)
    train_fusion_model(args)

if __name__ == "__main__":
    main()
