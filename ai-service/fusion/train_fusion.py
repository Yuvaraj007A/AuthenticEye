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
    
    # In a real scenario, you run your dataset through the base extractors 
    # and save the 16-dim vectors into an .npy file to rapidly train the MLP.
    if os.path.exists(args.features_file):
        data = torch.load(args.features_file)
        X = data['features']
        y = data['labels']
    else:
        print(f"File {args.features_file} not found. Generating dummy features for tests.")
        X = torch.randn(1000, 16)
        y = torch.randint(0, 2, (1000, 1)).float()
        
    X_train, X_val, y_train, y_val = train_test_split(
        X.numpy(), y.numpy(), test_size=0.2, random_state=42, stratify=y.numpy()
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--features_file", type=str, default="extracted_features.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--save_path", type=str, default="fusion_mlp.pth")
    args = parser.parse_args()
    train_fusion_model(args)
